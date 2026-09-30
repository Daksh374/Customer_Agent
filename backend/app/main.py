"""FastAPI application: routes, startup, and HTTP error handling.

The conversation logic lives in `chat_service.py`; this module only turns
HTTP requests into service calls and service errors into HTTP responses.

Run from the backend directory:

    uvicorn app.main:app --reload --reload-dir app
"""

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.chat_service import handle_message
from app.config import CORS_ORIGINS
from app.db import init_db, list_tickets
from app.embeddings import get_embedding_model
from app.llm import LLMUnavailableError
from app.models import ChatRequest, ChatResponse, ErrorResponse, HealthResponse, Ticket
from app.rag import KnowledgeBaseNotReadyError, is_knowledge_base_ready

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)  # silence per-request HTTP logs
logger = logging.getLogger("support")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialise the DB and warm up the embedding model before serving requests."""
    init_db()
    get_embedding_model()
    if not is_knowledge_base_ready():
        logger.warning("Knowledge base is not ingested yet. Run `python -m app.ingest` from /backend.")
    yield


app = FastAPI(title="E-commerce Support Agent", version="1.0.0", lifespan=lifespan)
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
    """Reply to a customer message, continuing the conversation if an ID is given.

    Declared as a sync function so FastAPI runs it in a worker thread; the
    embedding model, ChromaDB, Groq SDK, and sqlite3 are all blocking calls.
    """
    conversation_id = request.conversation_id or str(uuid.uuid4())
    try:
        return handle_message(conversation_id, request.message.strip())
    except KnowledgeBaseNotReadyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMUnavailableError as exc:
        raise HTTPException(status_code=503, detail=exc.user_message) from exc


@app.get("/tickets", response_model=list[Ticket])
def tickets() -> list[Ticket]:
    """List all escalation tickets, newest first (a mock admin view)."""
    return list_tickets()
