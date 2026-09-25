"""LLM calls via Groq: grounded answer generation and escalation classification."""

import json
import logging
from functools import lru_cache

import groq
from pydantic import ValidationError

from app.config import (
    GROQ_API_KEY,
    GROQ_CLASSIFIER_MODEL,
    GROQ_MODEL,
    LLM_MAX_RETRIES,
    LLM_TIMEOUT_SECONDS,
    MAX_HISTORY_MESSAGES,
    RELEVANCE_THRESHOLD,
)
from app.escalation_rules import apply_rules
from app.models import EscalationDecision
from app.rag import RetrievedChunk

logger = logging.getLogger(__name__)

NO_INFO_PHRASE = "I don't have information on that"
NO_INFO_RESPONSE = f"{NO_INFO_PHRASE} in our help articles. Would you like me to connect you with a human agent?"

ANSWER_SYSTEM_PROMPT = f"""You are the customer support assistant for TaskFlow, a project management SaaS product.

Rules:
- Answer ONLY using the information inside <context>. Do not use outside knowledge.
- If the context does not contain enough information to answer, reply with exactly:
  "{NO_INFO_PHRASE}." followed by one short sentence offering to connect them with a human agent.
- Never invent features, prices, policies, limits, URLs, or steps that are not in the context.
- Never invent contact methods (emails, links, phone numbers, forms). If the customer needs a
  person, say a TaskFlow support agent will follow up.
- Be concise and friendly. Use short numbered steps or bullet points for procedures.
- Refer to the context as "our help articles" if needed; never mention "context" or "chunks".
- Use earlier conversation turns only to understand follow-up questions, not as a source of facts."""

CLASSIFIER_SYSTEM_PROMPT = """You decide whether a customer support conversation must be escalated to a human agent.

Escalate (escalate=true) ONLY if the customer's latest message itself shows one of these:
- A billing dispute: the customer says they were charged incorrectly, twice, or without consent
- Disagreement with a refund decision that was already made (not a question about eligibility)
- A request to delete their account, workspace, or personal data
- Legal threats or mentions of lawyers, courts, or regulators
- Clear frustration or anger (insults, sarcasm, repeated complaints, threats to leave)

Do NOT escalate:
- Questions about policies, prices, or eligibility, even if the answer is "no"
  ("Can I get a refund on my monthly plan?" is a question, not a dispute)
- How-to questions about billing, refunds, exports, or deletion
- Polite follow-ups or clarifications

Judge the customer's words, not the assistant's answer.
Respond with JSON only: {"escalate": true|false, "reason": "<one short sentence>"}"""


class LLMUnavailableError(RuntimeError):
    """Raised when the LLM can't be reached; `user_message` is safe to show customers."""

    def __init__(self, user_message: str):
        super().__init__(user_message)
        self.user_message = user_message


# --- Groq client & error handling ---------------------------------------------


@lru_cache(maxsize=1)
def _get_client() -> groq.Groq:
    """Create (once) the Groq client with a timeout and limited retries."""
    if not GROQ_API_KEY:
        raise LLMUnavailableError("The AI service is not configured (GROQ_API_KEY is missing).")
    return groq.Groq(api_key=GROQ_API_KEY, timeout=LLM_TIMEOUT_SECONDS, max_retries=LLM_MAX_RETRIES)


def _friendly_error(exc: groq.GroqError) -> str:
    """Map a Groq SDK exception to a message that is safe to show a customer."""
    # Order matters: APITimeoutError is a subclass of APIConnectionError.
    if isinstance(exc, groq.RateLimitError):
        return "Our AI assistant is receiving too many requests right now. Please try again in a moment."
    if isinstance(exc, groq.APITimeoutError):
        return "Our AI assistant took too long to respond. Please try again."
    if isinstance(exc, groq.APIConnectionError):
        return "We couldn't reach our AI assistant. Please try again shortly."
    if isinstance(exc, groq.AuthenticationError):
        return "The AI service is misconfigured (invalid API key). Please contact the site administrator."
    if isinstance(exc, groq.NotFoundError):
        return "The configured AI model is unavailable (check GROQ_MODEL). Please contact the site administrator."
    return "Our AI assistant is temporarily unavailable. Please try again later."


def _model_params(model: str) -> dict:
    """Extra parameters for a given model.

    gpt-oss models "think" before answering; low effort keeps latency down
    for simple support questions. Other models reject this parameter.
    """
    return {"reasoning_effort": "low"} if model.startswith("openai/gpt-oss") else {}


def _chat_completion(model: str, messages: list[dict], **kwargs) -> str:
    """Call Groq and return the reply text, raising `LLMUnavailableError` on failure."""
    try:
        completion = _get_client().chat.completions.create(
            model=model, messages=messages, **_model_params(model), **kwargs
        )
    except groq.GroqError as exc:
        logger.warning("Groq call failed: %s: %s", type(exc).__name__, exc)
        raise LLMUnavailableError(_friendly_error(exc)) from exc
    return (completion.choices[0].message.content or "").strip()


# --- Answer generation ---------------------------------------------------------


def format_context(chunks: list[RetrievedChunk]) -> str:
    """Render retrieved chunks as numbered, titled sources for the prompt."""
    if not chunks:
        return "(no relevant articles found)"
    return "\n\n".join(
        f"[Source {i}: {chunk.article_title}]\n{chunk.text}" for i, chunk in enumerate(chunks, 1)
    )


def build_answer_messages(
    query: str, chunks: list[RetrievedChunk], history: list[dict] | None = None
) -> list[dict]:
    """Assemble the system prompt, recent history, and context-grounded question."""
    recent_history = (history or [])[-MAX_HISTORY_MESSAGES:]
    user_turn = f"<context>\n{format_context(chunks)}\n</context>\n\nCustomer question: {query}"
    return [
        {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
        *recent_history,
        {"role": "user", "content": user_turn},
    ]


def generate_response(
    query: str, retrieved_chunks: list[RetrievedChunk], history: list[dict] | None = None
) -> str:
    """Generate an answer grounded only in `retrieved_chunks`.

    Callers should pass only chunks that cleared the relevance threshold. With
    no relevant chunks the LLM is skipped entirely and a fixed "no info" reply
    is returned: given only loosely related text, models tend to improvise
    plausible-sounding details, which is exactly what grounding should prevent.

    Raises `LLMUnavailableError` (with a customer-safe message) if Groq fails;
    the API layer turns that into an HTTP 503.
    """
    if not retrieved_chunks:
        return NO_INFO_RESPONSE
    messages = build_answer_messages(query, retrieved_chunks, history)
    answer = _chat_completion(GROQ_MODEL, messages, temperature=0.2, max_tokens=1024)
    return answer or NO_INFO_RESPONSE


def is_no_info_answer(answer: str) -> bool:
    """True if the model said it couldn't answer from the knowledge base."""
    normalised = answer.replace("’", "'").lower()
    return NO_INFO_PHRASE.lower() in normalised


# --- Escalation classification -------------------------------------------------


def classify_escalation(
    query: str,
    ai_response: str,
    retrieval_confidence: float,
    previous_user_messages: list[str] | None = None,
) -> EscalationDecision:
    """Decide whether the conversation should go to a human agent.

    Checks run cheapest-first and stop at the first hit, ordered so that the
    most specific reason wins (e.g. "Legal threat" beats "low confidence"):
      1. Deterministic rules (sensitive topics, human requests, frustration)
      2. Low retrieval confidence (knowledge base doesn't cover the question)
      3. The model itself said it had no information
      4. LLM classifier for nuanced cases the rules can't catch

    Checks 2 and 3 mean the question is out of scope rather than sensitive,
    so they set `requires_confirmation`: the customer is asked before a
    ticket is opened.

    Never raises: if the LLM classifier fails, falls back to "no escalation"
    because steps 1–3 already caught the high-risk cases.
    """
    previous_user_messages = previous_user_messages or []

    rule_reason = apply_rules(query, previous_user_messages)
    if rule_reason:
        return EscalationDecision(escalate=True, reason=rule_reason)

    if retrieval_confidence < RELEVANCE_THRESHOLD:
        return EscalationDecision(
            escalate=True,
            reason=f"Low retrieval confidence ({retrieval_confidence:.2f}); question may not be covered by the knowledge base.",
            requires_confirmation=True,
        )
    if is_no_info_answer(ai_response):
        return EscalationDecision(
            escalate=True,
            reason="The assistant could not find an answer in the knowledge base.",
            requires_confirmation=True,
        )

    return _classify_with_llm(query, ai_response, previous_user_messages)


def _classify_with_llm(query: str, ai_response: str, previous_user_messages: list[str]) -> EscalationDecision:
    """Ask the LLM for an escalation decision; fall back to no escalation on any failure."""
    recent = "\n".join(f"- {m}" for m in previous_user_messages[-3:]) or "(none)"
    user_turn = (
        f"Earlier customer messages:\n{recent}\n\n"
        f"Latest customer message:\n{query}\n\n"
        f"Assistant reply:\n{ai_response}"
    )
    messages = [
        {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
        {"role": "user", "content": user_turn},
    ]
    try:
        raw = _chat_completion(
            GROQ_CLASSIFIER_MODEL, messages, temperature=0, max_tokens=300, response_format={"type": "json_object"}
        )
        decision = EscalationDecision.model_validate(json.loads(raw))
    except (LLMUnavailableError, json.JSONDecodeError, ValidationError) as exc:
        logger.warning("Escalation classifier failed, defaulting to no escalation: %s", exc)
        return EscalationDecision(escalate=False, reason=None)

    return decision if decision.escalate else EscalationDecision(escalate=False, reason=None)
