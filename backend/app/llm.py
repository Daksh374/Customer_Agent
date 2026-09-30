"""LLM calls via Groq: query rewriting, grounded answers, and escalation classification."""

import json
import logging
from functools import lru_cache

import groq
from pydantic import ValidationError

from app.config import (
    GROQ_API_KEY,
    GROQ_CLASSIFIER_MODEL,
    GROQ_MODEL,
    HISTORY_MESSAGE_MAX_CHARS,
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

ANSWER_SYSTEM_PROMPT = f"""You are the customer support assistant for an online shopping (e-commerce) store in India.

Rules:
- Answer ONLY using the information inside <context>. Do not use outside knowledge.
- If the context does not contain enough information to answer, reply with exactly
  "{NO_INFO_PHRASE}." and nothing else.
- If the customer asks several things and the context covers only some of them, answer those and
  say briefly which part our help articles don't cover. Otherwise don't add disclaimers about what
  the articles don't say.
- Never invent features, prices, policies, limits, URLs, or steps that are not in the context.
- Never invent contact methods (emails, links, phone numbers, forms).
- Do not offer to connect the customer with a human agent and do not ask whether they want one.
  The support system handles handoffs to human agents automatically.
- You cannot see customer accounts, orders, payments, refunds, or tracking data. Never claim to
  have checked an order; explain how the customer can check it (e.g. Account > My Orders).
- Use the conversation to understand what the customer is referring to, but take facts only
  from <context>. Prefer giving the relevant steps or policy straight away; ask a short
  clarifying question only if no useful answer is possible without it.
- Be concise, warm, and professional. Use short numbered steps or bullet points for procedures.
  Never use tables (the chat is often read on a phone). Write amounts as "Rs." and the number.
- Refer to the context as "our help articles" if needed; never mention "context" or "chunks".
- Always reply in English, even if the customer writes in Hindi or Hinglish."""

REWRITE_SYSTEM_PROMPT = """You rewrite a customer's latest message in an online-shopping support chat into a
standalone question that can be understood without the rest of the conversation.

- Resolve references ("it", "that", "the second one", "what about electronics?") using the conversation.
- If the message answers a question the assistant asked (e.g. "yes" after "Would you like the steps
  to return it?"), write the question the customer now wants answered.
- If the message is already standalone, return it unchanged. Do not answer it or add details.
- Translate Hindi or Hinglish into English.
- If the message asks anything at all, even something off-topic, return it as a question.
- If the message states a need or a problem, turn it into the question the customer wants answered
  ("I need a GST invoice for my company" -> "How can I get a GST invoice for my company?";
  "the phone I ordered is not turning on" -> "What should I do if the phone I received does not turn on?").
- Keep what the customer is talking about from earlier turns (e.g. money deducted for a failed
  payment is not the same as a refund for a returned item).
- Return an empty string only if the message cannot be turned into a question: a bare "yes"/"ok"
  when the assistant did not ask anything, or background with no request (e.g. "I ordered a phone").

Respond with JSON only: {"question": "<standalone question in English, or empty string>"}"""

CLASSIFIER_SYSTEM_PROMPT = """You decide whether a customer support conversation must be escalated to a human agent.

Escalate (escalate=true) ONLY if the customer's latest message itself shows one of these:
- A payment dispute: the customer says they were charged incorrectly, twice, or without consent
- Disagreement with a refund, return, or replacement decision that was already made
- A request to delete their account or personal data
- A report of a counterfeit/fake product or of fraud on their account
- Legal threats or mentions of lawyers, consumer courts, police, or regulators
- Clear frustration or anger (insults, sarcasm, repeated complaints, threats to stop shopping here)

Do NOT escalate:
- Questions about policies, prices, delivery times, or eligibility, even if the answer is "no"
  ("Can I return shoes after 15 days?" is a question, not a dispute)
- How-to questions about orders, tracking, returns, refunds, payments, or coupons
- A failed payment where money was deducted: this is routine and auto-reversed by the bank
  ("Money was deducted but my order was not placed" is routine). Escalate only if the customer
  says the reversal has not arrived after the stated time (e.g. "it's been 10 days, still no refund").
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
        f"[Source {i}: {chunk.article_title}{f' > {chunk.section}' if chunk.section else ''}]\n{chunk.text}"
        for i, chunk in enumerate(chunks, 1)
    )


def trim_history(history: list[dict] | None) -> list[dict]:
    """Keep the most recent messages, shortening long assistant replies.

    The gist of an earlier answer is enough to resolve a follow-up, and
    full-length answers would multiply the tokens sent on every turn.
    """
    trimmed = []
    for message in (history or [])[-MAX_HISTORY_MESSAGES:]:
        content = message["content"]
        if message["role"] == "assistant" and len(content) > HISTORY_MESSAGE_MAX_CHARS:
            content = content[:HISTORY_MESSAGE_MAX_CHARS].rsplit(" ", 1)[0] + " …"
        trimmed.append({"role": message["role"], "content": content})
    return trimmed


def build_answer_messages(
    query: str,
    chunks: list[RetrievedChunk],
    history: list[dict] | None = None,
    standalone_query: str | None = None,
) -> list[dict]:
    """Assemble the system prompt, recent history, and context-grounded question."""
    user_turn = f"<context>\n{format_context(chunks)}\n</context>\n\nCustomer message: {query}"
    if standalone_query and standalone_query.strip().lower() != query.strip().lower():
        user_turn += f"\n(In this conversation, the customer is asking: {standalone_query})"
    return [
        {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
        *trim_history(history),
        {"role": "user", "content": user_turn},
    ]


def generate_response(
    query: str,
    retrieved_chunks: list[RetrievedChunk],
    history: list[dict] | None = None,
    standalone_query: str | None = None,
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
    messages = build_answer_messages(query, retrieved_chunks, history, standalone_query)
    answer = _chat_completion(GROQ_MODEL, messages, temperature=0.2, max_tokens=1024)
    return answer or NO_INFO_RESPONSE


def is_no_info_answer(answer: str) -> bool:
    """True if the reply is a "no information" answer.

    Only a reply that *starts* with the phrase counts: a partial answer that
    mentions one uncovered detail still contains useful information.
    """
    normalised = answer.replace("\u2019", "'").strip().lower()
    return normalised.startswith(NO_INFO_PHRASE.lower())


# --- Query rewriting -----------------------------------------------------------


def format_transcript(history: list[dict]) -> str:
    """Render messages as "Customer: ..." / "Assistant: ..." lines."""
    speaker = {"user": "Customer", "assistant": "Assistant"}
    return "\n".join(f"{speaker[m['role']]}: {m['content']}" for m in history)


def rewrite_query(message: str, history: list[dict]) -> str:
    """Turn the latest message into a standalone English question using the conversation.

    Returns "" when the message isn't a question at all (e.g. a bare "yes"
    with nothing to agree to). Raises `LLMUnavailableError` on failure, so
    the caller can fall back to a simpler heuristic.
    """
    user_turn = (
        f"Conversation so far:\n{format_transcript(trim_history(history)) or '(none)'}\n\n"
        f"Latest customer message: {message}"
    )
    raw = _chat_completion(
        GROQ_CLASSIFIER_MODEL,
        [{"role": "system", "content": REWRITE_SYSTEM_PROMPT}, {"role": "user", "content": user_turn}],
        temperature=0,
        max_tokens=300,
        response_format={"type": "json_object"},
    )
    try:
        question = json.loads(raw).get("question", "")
    except (json.JSONDecodeError, AttributeError) as exc:
        raise LLMUnavailableError("Query rewriting returned invalid JSON") from exc
    return question.strip() if isinstance(question, str) else ""


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
