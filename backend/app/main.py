"""FastAPI application: routes, request pipeline, and error handling.

Run from the backend directory:

    uvicorn app.main:app --reload --reload-dir app
"""

import logging
import re
import threading
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import CORS_ORIGINS
from app.db import create_ticket, init_db, list_tickets
from app.embeddings import get_embedding_model
from app.escalation_rules import is_affirmative, is_negative
from app.llm import (
    NO_INFO_RESPONSE,
    LLMUnavailableError,
    classify_escalation,
    generate_response,
    is_no_info_answer,
)
from app.models import ChatRequest, ChatResponse, ErrorResponse, HealthResponse, Source, Ticket
from app.rag import KnowledgeBaseNotReadyError, RetrievalResult, is_knowledge_base_ready, retrieve

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)  # silence per-request HTTP logs
logger = logging.getLogger("taskflow")

SNIPPET_LENGTH = 180
MAX_STORED_MESSAGES = 20
FOLLOW_UP_MAX_WORDS = 12

ESCALATION_CONFIRMED_RESPONSE = (
    "Done! I've passed your question to our support team, and a human agent will follow up with you shortly."
)
ESCALATION_DECLINED_RESPONSE = "No problem! Is there anything else I can help you with?"
ESCALATED_WITHOUT_ANSWER_RESPONSE = (
    "I don't have information on that in our help articles, so I've passed your message to our "
    "support team. A human agent will follow up with you shortly."
)


@dataclass
class PendingOffer:
    """An out-of-scope question waiting for the customer to accept a human handoff."""

    message: str
    ai_response: str
    reason: str


class ConversationStore:
    """Thread-safe, in-memory chat history keyed by conversation ID.

    Good enough for a single-process demo; a production system would use
    Redis or a database so history survives restarts and scales horizontally.
    """

    def __init__(self) -> None:
        self._conversations: dict[str, list[dict]] = {}
        self._pending_offers: dict[str, PendingOffer] = {}
        self._lock = threading.Lock()

    def get_history(self, conversation_id: str) -> list[dict]:
        """Return a copy of the messages in a conversation (empty if unknown)."""
        with self._lock:
            return list(self._conversations.get(conversation_id, []))

    def append_turn(self, conversation_id: str, user_message: str, assistant_message: str) -> None:
        """Record one user/assistant exchange, keeping only the most recent messages."""
        with self._lock:
            history = self._conversations.setdefault(conversation_id, [])
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": assistant_message})
            del history[:-MAX_STORED_MESSAGES]

    def set_offer(self, conversation_id: str, offer: PendingOffer) -> None:
        """Remember that we asked the customer whether they want a human agent."""
        with self._lock:
            self._pending_offers[conversation_id] = offer

    def pop_offer(self, conversation_id: str) -> PendingOffer | None:
        """Remove and return the pending offer, if any (an offer is answered once)."""
        with self._lock:
            return self._pending_offers.pop(conversation_id, None)


conversations = ConversationStore()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialise the DB and warm up the embedding model before serving requests."""
    init_db()
    get_embedding_model()
    if not is_knowledge_base_ready():
        logger.warning("Knowledge base is not ingested yet. Run `python -m app.ingest` from /backend.")
    yield


app = FastAPI(title="TaskFlow Support Agent", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    """Return a clean JSON 500 instead of a stack trace for unexpected errors."""
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "An unexpected server error occurred."})


# --- Helpers -------------------------------------------------------------------


def make_snippet(text: str, length: int = SNIPPET_LENGTH) -> str:
    """Flatten markdown to plain text and cut it at a word boundary."""
    plain = re.sub(r"[#*`|>]+", "", text)
    plain = re.sub(r"\s+", " ", plain).strip()
    if len(plain) <= length:
        return plain
    return plain[:length].rsplit(" ", 1)[0] + "…"


def build_sources(retrieval: RetrievalResult) -> list[Source]:
    """One source per article (best-scoring chunk), limited to relevant hits."""
    best_by_title: dict[str, Source] = {}
    for chunk in retrieval.relevant_chunks():
        if chunk.article_title not in best_by_title:  # chunks arrive best-first
            best_by_title[chunk.article_title] = Source(
                title=chunk.article_title, snippet=make_snippet(chunk.text), score=chunk.score
            )
    return list(best_by_title.values())


def build_retrieval_query(message: str, history: list[dict]) -> str:
    """Give short follow-up questions the context of the previous question.

    "What about on Business?" retrieves poorly on its own. Prepending the
    previous customer message is a cheap alternative to an extra LLM call
    that rewrites the question.
    """
    previous = previous_user_messages(history)
    if previous and len(message.split()) <= FOLLOW_UP_MAX_WORDS:
        return f"{previous[-1]} {message}"
    return message


def previous_user_messages(history: list[dict]) -> list[str]:
    """Extract just the customer's messages from a conversation history."""
    return [m["content"] for m in history if m["role"] == "user"]


# --- Routes --------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness check."""
    return HealthResponse(status="ok")


@app.post(
    "/chat",
    response_model=ChatResponse,
    responses={503: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def chat(request: ChatRequest) -> ChatResponse:
    """Answer a customer message: retrieve → generate → classify → (maybe) ticket.

    If the previous reply offered a human handoff, a yes/no answer is handled
    first. Retrieval or LLM failures become HTTP 503 with a message safe to
    show the customer; escalation classification never fails the request.

    Declared as a sync function so FastAPI runs it in a worker thread; the
    embedding model, ChromaDB, Groq SDK, and sqlite3 are all blocking calls.
    """
    conversation_id = request.conversation_id or str(uuid.uuid4())
    message = request.message.strip()

    offer_reply = handle_offer_reply(conversation_id, message)
    if offer_reply:
        return offer_reply

    return answer_question(conversation_id, message)


def handle_offer_reply(conversation_id: str, message: str) -> ChatResponse | None:
    """Resolve a pending "connect you with a human?" offer.

    Returns a response for a clear yes or no. Anything else is treated as a
    new question: the offer is dropped and None is returned.
    """
    offer = conversations.pop_offer(conversation_id)
    if offer is None:
        return None

    if is_affirmative(message):
        ticket_id = create_ticket(offer.message, offer.ai_response, offer.reason, conversation_id)
        logger.info("Customer accepted handoff; conversation %s → ticket %s", conversation_id, ticket_id)
        conversations.append_turn(conversation_id, message, ESCALATION_CONFIRMED_RESPONSE)
        return ChatResponse(
            response=ESCALATION_CONFIRMED_RESPONSE,
            retrieved_sources=[],
            escalate=True,
            escalation_reason=offer.reason,
            ticket_id=ticket_id,
            conversation_id=conversation_id,
        )

    if is_negative(message):
        conversations.append_turn(conversation_id, message, ESCALATION_DECLINED_RESPONSE)
        return ChatResponse(
            response=ESCALATION_DECLINED_RESPONSE,
            retrieved_sources=[],
            escalate=False,
            conversation_id=conversation_id,
        )

    return None


def answer_question(conversation_id: str, message: str) -> ChatResponse:
    """Run the RAG pipeline for a customer question and apply the escalation decision."""
    history = conversations.get_history(conversation_id)

    try:
        retrieval = retrieve(build_retrieval_query(message, history))
    except KnowledgeBaseNotReadyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        answer = generate_response(message, retrieval.relevant_chunks(), history)
    except LLMUnavailableError as exc:
        raise HTTPException(status_code=503, detail=exc.user_message) from exc

    decision = classify_escalation(
        message, answer, retrieval.top_score, previous_user_messages(history)
    )

    # Out-of-scope question: ask before opening a ticket, and cite nothing.
    if decision.escalate and decision.requires_confirmation:
        conversations.set_offer(conversation_id, PendingOffer(message, NO_INFO_RESPONSE, decision.reason or "Escalated"))
        conversations.append_turn(conversation_id, message, NO_INFO_RESPONSE)
        return ChatResponse(
            response=NO_INFO_RESPONSE,
            retrieved_sources=[],
            escalate=False,
            offer_escalation=True,
            conversation_id=conversation_id,
        )

    ticket_id = None
    if decision.escalate:
        if is_no_info_answer(answer):
            # Already escalated, so don't ask "would you like me to connect you?"
            answer = ESCALATED_WITHOUT_ANSWER_RESPONSE
        ticket_id = create_ticket(message, answer, decision.reason or "Escalated", conversation_id)
        logger.info("Escalated conversation %s as ticket %s: %s", conversation_id, ticket_id, decision.reason)

    conversations.append_turn(conversation_id, message, answer)

    # Citing articles alongside "I don't have information on that" would be contradictory.
    sources = [] if is_no_info_answer(answer) else build_sources(retrieval)

    return ChatResponse(
        response=answer,
        retrieved_sources=sources,
        escalate=decision.escalate,
        escalation_reason=decision.reason,
        ticket_id=ticket_id,
        conversation_id=conversation_id,
    )


@app.get("/tickets", response_model=list[Ticket])
def tickets() -> list[Ticket]:
    """List all escalation tickets, newest first (a mock admin view)."""
    return list_tickets()
