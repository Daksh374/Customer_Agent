"""API and pipeline tests with retrieval and the LLM mocked out: no network, no vector DB."""

import pytest
from fastapi.testclient import TestClient

import app.chat_service as service
import app.db as db
import app.main as main
from app.intents import GREETING_REPLY
from app.llm import LLMUnavailableError, classify_escalation
from app.models import EscalationDecision
from app.rag import KnowledgeBaseNotReadyError, RetrievalResult, RetrievedChunk

CHUNK = RetrievedChunk(
    text="Electronics are replacement-only within 7 days of delivery.",
    source_file="04-returns-and-refunds.pdf",
    article_title="Returns & Refunds",
    chunk_index=0,
    score=0.62,
)
NO_ESCALATION = EscalationDecision(escalate=False)
OUT_OF_SCOPE = EscalationDecision(escalate=True, reason="Low retrieval confidence", requires_confirmation=True)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "support.db")
    db.init_db()
    monkeypatch.setattr(service, "rewrite_query", lambda message, history: message)
    monkeypatch.setattr(service, "retrieve", lambda q: RetrievalResult([CHUNK], 0.62, False))
    monkeypatch.setattr(service, "generate_response", lambda *a: "Phones can only be replaced if defective.")
    monkeypatch.setattr(service, "classify_escalation", lambda *a, **k: NO_ESCALATION)
    return TestClient(main.app)  # not used as a context manager, so lifespan doesn't load the model


def chat(client, message, conversation_id=None):
    return client.post("/chat", json={"message": message, "conversation_id": conversation_id}).json()


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_chat_returns_answer_and_sources(client):
    body = chat(client, "Can I return a phone?")
    assert body["response"] == "Phones can only be replaced if defective."
    assert body["retrieved_sources"][0]["title"] == "Returns & Refunds"
    assert body["escalate"] is False and body["ticket_id"] is None
    assert body["conversation_id"]


def test_conversation_memory_is_passed_to_the_next_turn(client, monkeypatch):
    histories = []
    monkeypatch.setattr(service, "rewrite_query", lambda message, history: histories.append(history) or message)
    cid = chat(client, "What is the return window for clothes?")["conversation_id"]
    chat(client, "what about electronics?", cid)
    assert [m["content"] for m in histories[-1]] == [
        "What is the return window for clothes?",
        "Phones can only be replaced if defective.",
    ]


def test_rewritten_question_is_used_for_retrieval(client, monkeypatch):
    queries = []
    monkeypatch.setattr(service, "rewrite_query", lambda message, history: "What is the return window for electronics?")
    monkeypatch.setattr(service, "retrieve", lambda q: queries.append(q) or RetrievalResult([CHUNK], 0.62, False))
    chat(client, "what about electronics?")
    assert queries == ["What is the return window for electronics?"]


def test_rewriter_failure_falls_back_to_heuristic(client, monkeypatch):
    queries = []

    def down(message, history):
        raise LLMUnavailableError("rate limited")

    cid = chat(client, "What is the return window for clothes?")["conversation_id"]
    monkeypatch.setattr(service, "rewrite_query", down)
    monkeypatch.setattr(service, "retrieve", lambda q: queries.append(q) or RetrievalResult([CHUNK], 0.62, False))
    chat(client, "what about electronics?", cid)
    assert queries == ["What is the return window for clothes? what about electronics?"]


def test_bare_yes_with_nothing_to_confirm_asks_for_clarification(client, monkeypatch):
    monkeypatch.setattr(service, "rewrite_query", lambda message, history: "")
    body = chat(client, "yes")
    assert body["response"] == service.CLARIFY_RESPONSE and body["ticket_id"] is None


def test_greeting_skips_the_pipeline(client, monkeypatch):
    monkeypatch.setattr(service, "retrieve", lambda q: pytest.fail("greetings should not hit retrieval"))
    assert chat(client, "hello")["response"] == GREETING_REPLY


def test_human_request_opens_ticket_with_issue_and_transcript(client):
    cid = chat(client, "My coupon code is not working")["conversation_id"]
    body = chat(client, "connect me with a human representative.", cid)
    assert body["escalate"] is True and body["ticket_id"].startswith("#")

    ticket = client.get("/tickets").json()[0]
    assert ticket["message"] == "My coupon code is not working"
    assert "Customer: My coupon code is not working" in ticket["transcript"]
    assert "Customer: connect me with a human representative." in ticket["transcript"]


def test_escalation_creates_ticket(client, monkeypatch):
    monkeypatch.setattr(
        service, "classify_escalation", lambda *a, **k: EscalationDecision(escalate=True, reason="Legal threat")
    )
    body = chat(client, "I will file a complaint in consumer court")
    assert body["escalate"] is True and body["ticket_id"].startswith("#")

    tickets = client.get("/tickets").json()
    assert tickets[0]["ticket_id"] == body["ticket_id"]
    assert tickets[0]["reason"] == "Legal threat"


def test_out_of_scope_question_asks_before_creating_ticket(client, monkeypatch):
    monkeypatch.setattr(service, "classify_escalation", lambda *a, **k: OUT_OF_SCOPE)
    body = chat(client, "Weather in Mumbai?")
    assert body["offer_escalation"] is True
    assert body["escalate"] is False and body["ticket_id"] is None
    assert body["retrieved_sources"] == []
    assert client.get("/tickets").json() == []


def test_accepting_offer_creates_ticket_for_original_question(client, monkeypatch):
    monkeypatch.setattr(service, "classify_escalation", lambda *a, **k: OUT_OF_SCOPE)
    cid = chat(client, "Weather in Mumbai?")["conversation_id"]
    reply = chat(client, "yes", cid)
    assert reply["escalate"] is True and reply["ticket_id"].startswith("#")
    assert client.get("/tickets").json()[0]["message"] == "Weather in Mumbai?"


def test_declining_offer_creates_no_ticket(client, monkeypatch):
    monkeypatch.setattr(service, "classify_escalation", lambda *a, **k: OUT_OF_SCOPE)
    cid = chat(client, "Weather in Mumbai?")["conversation_id"]
    reply = chat(client, "no thanks", cid)
    assert reply["escalate"] is False and reply["ticket_id"] is None
    assert client.get("/tickets").json() == []


def test_new_question_drops_pending_offer(client, monkeypatch):
    monkeypatch.setattr(service, "classify_escalation", lambda *a, **k: OUT_OF_SCOPE)
    cid = chat(client, "Weather in Mumbai?")["conversation_id"]
    monkeypatch.setattr(service, "classify_escalation", lambda *a, **k: NO_ESCALATION)
    chat(client, "Can I return a phone?", cid)
    # The offer was dropped, so a later "yes" is not a handoff.
    monkeypatch.setattr(service, "rewrite_query", lambda message, history: "")
    later = chat(client, "yes", cid)
    assert later["ticket_id"] is None
    assert client.get("/tickets").json() == []


def test_immediate_escalation_does_not_ask_to_connect(client, monkeypatch):
    monkeypatch.setattr(service, "generate_response", lambda *a: "I don't have information on that.")
    monkeypatch.setattr(
        service, "classify_escalation", lambda *a, **k: EscalationDecision(escalate=True, reason="Legal threat")
    )
    body = chat(client, "My lawyer will be in touch")
    assert body["ticket_id"] and body["offer_escalation"] is False
    assert "passed your message to our support team" in body["response"] and "?" not in body["response"]


def test_missing_knowledge_base_returns_503(client, monkeypatch):
    def not_ready(_):
        raise KnowledgeBaseNotReadyError("Run ingest first")

    monkeypatch.setattr(service, "retrieve", not_ready)
    response = client.post("/chat", json={"message": "Can I return a phone?"})
    assert response.status_code == 503
    assert "ingest" in response.json()["detail"]


def test_llm_failure_returns_503(client, monkeypatch):
    def down(*_):
        raise LLMUnavailableError("AI is down")

    monkeypatch.setattr(service, "generate_response", down)
    response = client.post("/chat", json={"message": "Can I return a phone?"})
    assert response.status_code == 503
    assert response.json()["detail"] == "AI is down"


def test_empty_message_is_rejected(client):
    assert client.post("/chat", json={"message": ""}).status_code == 422


def test_classifier_falls_back_when_llm_fails(monkeypatch):
    import app.llm as llm

    def down(*_, **__):
        raise LLMUnavailableError("rate limited")

    monkeypatch.setattr(llm, "_chat_completion", down)
    decision = classify_escalation("How do I track my order?", "Go to Account > My Orders.", retrieval_confidence=0.6)
    assert decision.escalate is False


def test_low_confidence_escalates_without_calling_llm(monkeypatch):
    import app.llm as llm

    monkeypatch.setattr(llm, "_chat_completion", lambda *a, **k: pytest.fail("LLM should not be called"))
    decision = classify_escalation("What's the weather?", "I don't have information on that.", 0.05)
    assert decision.escalate is True and decision.requires_confirmation is True


def test_sensitive_topic_escalates_without_confirmation():
    decision = classify_escalation("My lawyer will contact you", "I don't have information on that.", 0.05)
    assert decision.escalate is True and decision.requires_confirmation is False
