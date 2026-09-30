"""Pydantic schemas for API requests/responses and internal decisions."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Body of POST /chat."""

    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: str | None = Field(
        default=None, description="Omit to start a new conversation."
    )


class Source(BaseModel):
    """A knowledge-base article cited in an answer."""

    title: str
    snippet: str
    score: float


class ChatResponse(BaseModel):
    """Response of POST /chat."""

    response: str
    retrieved_sources: list[Source]
    escalate: bool
    escalation_reason: str | None = None
    ticket_id: str | None = None
    offer_escalation: bool = Field(
        default=False,
        description="True when the bot asks whether to connect a human agent; reply yes/no to answer.",
    )
    conversation_id: str


class EscalationDecision(BaseModel):
    """Output of the escalation classifier.

    `requires_confirmation` marks out-of-scope questions: instead of opening a
    ticket straight away, the customer is first asked if they want a human.
    """

    escalate: bool
    reason: str | None = None
    requires_confirmation: bool = False


class Ticket(BaseModel):
    """An escalation ticket as stored in SQLite."""

    ticket_id: str
    conversation_id: str | None
    message: str
    ai_response: str
    reason: str
    created_at: str
    transcript: str | None = None


class HealthResponse(BaseModel):
    """Response of GET /health."""

    status: str


class ErrorResponse(BaseModel):
    """Shape of every error body returned by the API."""

    detail: str
