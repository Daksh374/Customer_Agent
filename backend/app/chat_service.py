"""The conversation pipeline behind POST /chat.

Every customer message is routed through these steps, in order:

  1. Pending offer    - if we just asked "connect you with a human agent?",
                        a yes opens a ticket and a no closes the offer.
  2. Human request    - "talk to an agent" opens a ticket straight away.
  3. Small talk       - greetings, thanks, "ok", "no thanks" get a canned
                        reply without retrieval or an LLM call.
  4. Question         - rewrite into a standalone question using the chat
                        history, retrieve, answer, classify escalation.

Every turn is saved to conversation memory, so later messages can refer
back to earlier ones ("what about electronics?", "yes", "the second one").
"""

import logging
import re

from app import memory
from app.config import TICKET_TRANSCRIPT_MESSAGES
from app.db import create_ticket
from app.escalation_rules import check_human_request
from app.intents import is_affirmative, is_negative, small_talk_reply
from app.llm import (
    NO_INFO_RESPONSE,
    LLMUnavailableError,
    classify_escalation,
    format_transcript,
    generate_response,
    is_no_info_answer,
    rewrite_query,
)
from app.memory import PendingOffer
from app.models import ChatResponse, Source
from app.rag import RetrievalResult, retrieve

logger = logging.getLogger("support")

SNIPPET_LENGTH = 180
MAX_SOURCES = 3
# Articles scoring well below the best match are background noise, not citations.
SOURCE_SCORE_MARGIN = 0.1
FOLLOW_UP_MAX_WORDS = 12
TRANSCRIPT_ASSISTANT_MAX_CHARS = 300

HUMAN_HANDOFF_REASON = "Customer asked to speak with a human agent."
# Handoff replies say what was done; the ticket card in the UI says what happens next.
HUMAN_HANDOFF_RESPONSE = "Sure! I've created a support ticket and shared this conversation with our team."
OFFER_ACCEPTED_RESPONSE = "Done! I've passed your question to our support team."
OFFER_DECLINED_RESPONSE = "No problem! Is there anything else I can help you with?"
ESCALATED_WITHOUT_ANSWER_RESPONSE = (
    "I don't have information on that in our help articles, so I've passed your message to our support team."
)
CLARIFY_RESPONSE = (
    "Sure! What would you like help with? For example, I can help with an order, delivery, "
    "a return or refund, a payment, or your account."
)


def handle_message(conversation_id: str, message: str) -> ChatResponse:
    """Route one customer message and return the reply.

    Raises `KnowledgeBaseNotReadyError` or `LLMUnavailableError` when an
    answer can't be produced; the API layer turns both into HTTP 503.
    """
    history = memory.get_history(conversation_id)

    offer = memory.pop_offer(conversation_id)
    if offer is not None:
        reply = resolve_offer(conversation_id, message, offer, history)
        if reply is not None:
            return reply

    if check_human_request(message):
        return hand_off_to_human(conversation_id, message, history)

    canned = small_talk_reply(message, assistant_asked_question(history))
    if canned is not None:
        return respond(conversation_id, message, canned)

    return answer_question(conversation_id, message, history)


# --- Routing steps -------------------------------------------------------------


def resolve_offer(
    conversation_id: str, message: str, offer: PendingOffer, history: list[dict]
) -> ChatResponse | None:
    """Handle a yes/no reply to a "connect you with a human?" offer.

    Returns None for anything else: the offer has already been dropped, and
    the message is handled as a new question.
    """
    if is_affirmative(message):
        transcript = build_transcript(history, message, OFFER_ACCEPTED_RESPONSE)
        ticket_id = create_ticket(offer.message, offer.ai_response, offer.reason, conversation_id, transcript)
        logger.info("Customer accepted handoff; conversation %s → ticket %s", conversation_id, ticket_id)
        return respond(
            conversation_id, message, OFFER_ACCEPTED_RESPONSE,
            escalate=True, escalation_reason=offer.reason, ticket_id=ticket_id,
        )
    if is_negative(message):
        return respond(conversation_id, message, OFFER_DECLINED_RESPONSE)
    return None


def hand_off_to_human(conversation_id: str, message: str, history: list[dict]) -> ChatResponse:
    """Open a ticket immediately when the customer asks for a person.

    The ticket records the customer's actual issue (their latest real
    question), not just "talk to an agent", plus the recent transcript.
    """
    issue = latest_customer_issue(history) or message
    transcript = build_transcript(history, message, HUMAN_HANDOFF_RESPONSE)
    ticket_id = create_ticket(issue, HUMAN_HANDOFF_RESPONSE, HUMAN_HANDOFF_REASON, conversation_id, transcript)
    logger.info("Customer requested a human; conversation %s → ticket %s", conversation_id, ticket_id)
    return respond(
        conversation_id, message, HUMAN_HANDOFF_RESPONSE,
        escalate=True, escalation_reason=HUMAN_HANDOFF_REASON, ticket_id=ticket_id,
    )


def answer_question(conversation_id: str, message: str, history: list[dict]) -> ChatResponse:
    """Run the RAG pipeline for a question and apply the escalation decision."""
    question = resolve_question(message, history)
    if not question:
        return respond(conversation_id, message, CLARIFY_RESPONSE)

    retrieval = retrieve(question)
    answer = generate_response(message, retrieval.relevant_chunks(), history, question)
    decision = classify_escalation(message, answer, retrieval.top_score, previous_user_messages(history))

    # Out-of-scope question: ask before opening a ticket, and cite nothing.
    if decision.escalate and decision.requires_confirmation:
        memory.set_offer(conversation_id, PendingOffer(question, NO_INFO_RESPONSE, decision.reason or "Escalated"))
        return respond(conversation_id, message, NO_INFO_RESPONSE, offer_escalation=True)

    ticket_id = None
    if decision.escalate:
        if is_no_info_answer(answer):
            # Already escalated, so don't ask "would you like me to connect you?"
            answer = ESCALATED_WITHOUT_ANSWER_RESPONSE
        transcript = build_transcript(history, message, answer)
        ticket_id = create_ticket(message, answer, decision.reason or "Escalated", conversation_id, transcript)
        logger.info("Escalated conversation %s as ticket %s: %s", conversation_id, ticket_id, decision.reason)

    # Citing articles alongside "I don't have information on that" would be contradictory.
    sources = [] if is_no_info_answer(answer) else build_sources(retrieval)
    return respond(
        conversation_id, message, answer,
        sources=sources, escalate=decision.escalate,
        escalation_reason=decision.reason, ticket_id=ticket_id,
    )


def resolve_question(message: str, history: list[dict]) -> str:
    """Rewrite the message into a standalone question using the conversation.

    Falls back to a heuristic (prefix short follow-ups with the previous
    question) if the rewriting LLM call fails, so a rewrite outage degrades
    answer quality slightly instead of failing the request.
    """
    try:
        return rewrite_query(message, history)
    except LLMUnavailableError as exc:
        logger.warning("Query rewriting failed, using heuristic: %s", exc)
        previous = previous_user_messages(history)
        if previous and len(message.split()) <= FOLLOW_UP_MAX_WORDS:
            return f"{previous[-1]} {message}"
        return message


# --- Helpers -------------------------------------------------------------------


def respond(
    conversation_id: str,
    message: str,
    response: str,
    sources: list[Source] | None = None,
    **fields,
) -> ChatResponse:
    """Save the turn to conversation memory and build the API response."""
    memory.append_turn(conversation_id, message, response)
    return ChatResponse(
        response=response,
        retrieved_sources=sources or [],
        escalate=fields.pop("escalate", False),
        conversation_id=conversation_id,
        **fields,
    )


def assistant_asked_question(history: list[dict]) -> bool:
    """True if the assistant's last message ended with a question."""
    last_assistant = next((m["content"] for m in reversed(history) if m["role"] == "assistant"), "")
    return last_assistant.rstrip().endswith("?")


def previous_user_messages(history: list[dict]) -> list[str]:
    """Extract just the customer's messages from a conversation history."""
    return [m["content"] for m in history if m["role"] == "user"]


def latest_customer_issue(history: list[dict]) -> str | None:
    """The customer's most recent real question (not small talk or a handoff request)."""
    for message in reversed(previous_user_messages(history)):
        if not check_human_request(message) and small_talk_reply(message, False) is None:
            return message
    return None


def build_transcript(history: list[dict], message: str, response: str) -> str:
    """Recent conversation, including this turn, for the human agent picking up a ticket."""
    turns = history + [{"role": "user", "content": message}, {"role": "assistant", "content": response}]
    shortened = [
        {**m, "content": m["content"][:TRANSCRIPT_ASSISTANT_MAX_CHARS]} if m["role"] == "assistant" else m
        for m in turns[-TICKET_TRANSCRIPT_MESSAGES:]
    ]
    return format_transcript(shortened)


def make_snippet(text: str, length: int = SNIPPET_LENGTH) -> str:
    """Flatten markdown to plain text and cut it at a word boundary."""
    plain = re.sub(r"[#*`|>]+", "", text)
    plain = re.sub(r"\s+", " ", plain).strip()
    if len(plain) <= length:
        return plain
    return plain[:length].rsplit(" ", 1)[0] + "…"


def build_sources(retrieval: RetrievalResult) -> list[Source]:
    """Cite up to 3 articles whose best chunk scores close to the top match."""
    best_by_title: dict[str, Source] = {}
    cutoff = retrieval.top_score - SOURCE_SCORE_MARGIN
    for chunk in retrieval.relevant_chunks():
        if chunk.score < cutoff or len(best_by_title) == MAX_SOURCES:
            break  # chunks arrive best-first
        if chunk.article_title not in best_by_title:
            best_by_title[chunk.article_title] = Source(
                title=chunk.article_title, snippet=make_snippet(chunk.text), score=chunk.score
            )
    return list(best_by_title.values())
