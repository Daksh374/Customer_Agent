"""API tests with retrieval and the LLM mocked out: no network, no vector DB."""

import pytest
from fastapi.testclient import TestClient

import app.db as db
import app.main as main
from app.llm import LLMUnavailableError, classify_escalation
from app.models import EscalationDecision
from app.rag import KnowledgeBaseNotReadyError, RetrievalResult, RetrievedChunk

CHUNK = RetrievedChunk(
    text="Monthly subscriptions are not eligible for refunds.",
    source_file="06-refund-policy.md",
    article_title="Refund Policy",
    chunk_index=0,
    score=0.62,
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "TICKETS_DB_PATH", tmp_path / "tickets.db")
    db.init_db()
    monkeypatch.setattr(main, "retrieve", lambda q: RetrievalResult([CHUNK], 0.62, False))
    monkeypatch.setattr(main, "generate_response", lambda q, chunks, history: "No refunds on monthly plans.")
    monkeypatch.setattr(
        main, "classify_escalation", lambda *a, **k: EscalationDecision(escalate=False, reason=None)
    )
    return TestClient(main.app)  # not used as a context manager, so lifespan doesn't load the model


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_chat_returns_answer_and_sources(client):
    body = client.post("/chat", json={"message": "Refund on monthly?"}).json()
    assert body["response"] == "No refunds on monthly plans."
    assert body["retrieved_sources"][0]["title"] == "Refund Policy"
    assert body["escalate"] is False and body["ticket_id"] is None
    assert body["conversation_id"]


def test_escalation_creates_ticket(client, monkeypatch):
    monkeypatch.setattr(
        main, "classify_escalation", lambda *a, **k: EscalationDecision(escalate=True, reason="Legal threat")
    )
    body = client.post("/chat", json={"message": "My lawyer will call you"}).json()
    assert body["escalate"] is True and body["ticket_id"].startswith("#")

    tickets = client.get("/tickets").json()
    assert tickets[0]["ticket_id"] == body["ticket_id"]
    assert tickets[0]["reason"] == "Legal threat"


def test_missing_knowledge_base_returns_503(client, monkeypatch):
    def not_ready(_):
        raise KnowledgeBaseNotReadyError("Run ingest first")

    monkeypatch.setattr(main, "retrieve", not_ready)
    response = client.post("/chat", json={"message": "hi"})
    assert response.status_code == 503
    assert "ingest" in response.json()["detail"]


def test_llm_failure_returns_503(client, monkeypatch):
    def down(*_):
        raise LLMUnavailableError("AI is down")

    monkeypatch.setattr(main, "generate_response", down)
    response = client.post("/chat", json={"message": "hi"})
    assert response.status_code == 503
    assert response.json()["detail"] == "AI is down"


def test_empty_message_is_rejected(client):
    assert client.post("/chat", json={"message": ""}).status_code == 422


def test_classifier_falls_back_when_llm_fails(monkeypatch):
    import app.llm as llm

    def down(*_, **__):
        raise LLMUnavailableError("rate limited")

    monkeypatch.setattr(llm, "_chat_completion", down)
    decision = classify_escalation("How do I export data?", "Go to Admin → Data.", retrieval_confidence=0.6)
    assert decision.escalate is False


OUT_OF_SCOPE = EscalationDecision(escalate=True, reason="Low retrieval confidence", requires_confirmation=True)


def test_out_of_scope_question_asks_before_creating_ticket(client, monkeypatch):
    monkeypatch.setattr(main, "classify_escalation", lambda *a, **k: OUT_OF_SCOPE)
    body = client.post("/chat", json={"message": "Weather in Mumbai?"}).json()
    assert body["offer_escalation"] is True
    assert body["escalate"] is False and body["ticket_id"] is None
    assert body["retrieved_sources"] == []
    assert client.get("/tickets").json() == []


def test_accepting_offer_creates_ticket_for_original_question(client, monkeypatch):
    monkeypatch.setattr(main, "classify_escalation", lambda *a, **k: OUT_OF_SCOPE)
    first = client.post("/chat", json={"message": "Weather in Mumbai?"}).json()
    reply = client.post("/chat", json={"message": "yes", "conversation_id": first["conversation_id"]}).json()
    assert reply["escalate"] is True and reply["ticket_id"].startswith("#")
    assert client.get("/tickets").json()[0]["message"] == "Weather in Mumbai?"


def test_declining_offer_creates_no_ticket(client, monkeypatch):
    monkeypatch.setattr(main, "classify_escalation", lambda *a, **k: OUT_OF_SCOPE)
    first = client.post("/chat", json={"message": "Weather in Mumbai?"}).json()
    reply = client.post("/chat", json={"message": "no thanks", "conversation_id": first["conversation_id"]}).json()
    assert reply["escalate"] is False and reply["ticket_id"] is None
    assert client.get("/tickets").json() == []


def test_new_question_drops_pending_offer(client, monkeypatch):
    monkeypatch.setattr(main, "classify_escalation", lambda *a, **k: OUT_OF_SCOPE)
    cid = client.post("/chat", json={"message": "Weather in Mumbai?"}).json()["conversation_id"]
    monkeypatch.setattr(main, "classify_escalation", lambda *a, **k: EscalationDecision(escalate=False))
    client.post("/chat", json={"message": "Refund on monthly?", "conversation_id": cid})
    # The offer was dropped, so a later "yes" is just a normal message, not a handoff.
    later = client.post("/chat", json={"message": "yes", "conversation_id": cid}).json()
    assert later["ticket_id"] is None
    assert client.get("/tickets").json() == []


def test_immediate_escalation_does_not_ask_to_connect(client, monkeypatch):
    monkeypatch.setattr(main, "generate_response", lambda *a: "I don't have information on that. Want an agent?")
    monkeypatch.setattr(
        main, "classify_escalation", lambda *a, **k: EscalationDecision(escalate=True, reason="Legal threat")
    )
    body = client.post("/chat", json={"message": "My lawyer will be in touch"}).json()
    assert body["ticket_id"] and body["offer_escalation"] is False
    assert "will follow up" in body["response"] and "?" not in body["response"]


def test_low_confidence_escalates_without_calling_llm(monkeypatch):
    import app.llm as llm

    monkeypatch.setattr(llm, "_chat_completion", lambda *a, **k: pytest.fail("LLM should not be called"))
    decision = classify_escalation("What's the weather?", "I don't have information on that.", 0.05)
    assert decision.escalate is True and decision.requires_confirmation is True


def test_sensitive_topic_escalates_without_confirmation():
    decision = classify_escalation("My lawyer will contact you", "I don't have information on that.", 0.05)
    assert decision.escalate is True and decision.requires_confirmation is False
