# TaskFlow AI Support Agent

A full-stack customer support chatbot for **TaskFlow**, a fictional project-management SaaS product. It answers questions using **Retrieval-Augmented Generation (RAG)** over a knowledge base of 18 support articles and cites its sources. It **escalates to a human agent** (logging a ticket) when a conversation is sensitive or frustrated. For questions outside the knowledge base, it first **asks** whether the customer wants a human.

**Stack:** FastAPI · sentence-transformers (local embeddings) · ChromaDB · Groq LLM API · React (Vite) · SQLite

---

## Architecture

```
                         ┌──────────────────────────── OFFLINE (python -m app.ingest) ───────────────────────────┐
                         │                                                                                        │
                         │  knowledge_base/*.md ──► parse title ──► recursive split ──► embed (MiniLM) ──► ChromaDB│
                         │  (18 articles)            (H1 = title)   (~500 tok, 50 overlap)  title-prefixed   (cosine)│
                         └────────────────────────────────────────────────────────────────────────────────────────┘

 ┌──────────────┐  POST /chat   ┌──────────────────────────── FastAPI (app/main.py) ─────────────────────────────┐
 │ React (Vite) │ ────────────► │                                                                                │
 │              │               │  1. retrieve()            rag.py   embed query → top-4 chunks → similarity     │
 │ ChatWindow   │               │                                    top score < 0.35 → low_confidence           │
 │ MessageBubble│               │  2. generate_response()   llm.py   relevant chunks only → Groq (gpt-oss-120b)  │
 │ KnowledgePanel               │                                    no relevant chunks → fixed "no info" reply  │
 │ EscalationBanner             │  3. classify_escalation() llm.py   rules → confidence → "no info" → LLM judge  │
 │              │ ◄──────────── │  4. create_ticket()       db.py    sensitive → ticket now; out of scope → ask  │
 └──────────────┘  JSON reply   │                                                                                │
                                │  In-memory ConversationStore keeps recent turns per conversation_id            │
                                └────────────────────────────────────────────────────────────────────────────────┘
```

### Request lifecycle (`POST /chat`)

1. **Retrieve.** The query is embedded locally and the 4 nearest chunks are fetched from ChromaDB. Cosine distance is converted to similarity (`1 − distance`). Short follow-ups ("what about Business?") are prefixed with the previous question so retrieval has context.
2. **Generate.** Only chunks above the relevance threshold go to the LLM, with a system prompt that forbids outside knowledge. The model must reply *"I don't have information on that"* when the context is insufficient. If no chunk clears the threshold, the LLM isn't called at all.
3. **Classify.** The escalation classifier decides whether a human should take over (see [Escalation logic](#how-escalation-works)).
4. **Log or ask.** Sensitive conversations create a mock ticket (e.g. `#84231`) in SQLite right away, visible at `GET /tickets`. Out-of-scope questions get *"Would you like me to connect you with a human agent?"* with no sources. A ticket is created only if the customer's next message is a yes (a button or a typed reply such as "yes please"). A "no" closes the offer, and any other message is treated as a new question.

---

## Project structure

```
backend/
  knowledge_base/          18 TaskFlow support articles (markdown, H1 = citation title)
  app/
    config.py              All settings in one place (paths, model names, thresholds)
    embeddings.py          Shared sentence-transformers model (loaded once)
    ingest.py              Load → chunk → embed → store. Idempotent.
    rag.py                 retrieve() + low-confidence flag + "KB not ingested" check
    llm.py                 Groq calls: generate_response(), classify_escalation()
    escalation_rules.py    Deterministic escalation rules (regex + heuristics)
    models.py              Pydantic request/response schemas
    db.py                  SQLite ticket log
    main.py                FastAPI app, routes, error handling, conversation memory
  tests/                   pytest suite (rules, chunking, API with mocked LLM)
  requirements.txt
  .env.example
frontend/
  src/
    api.js                 fetch wrapper → user-friendly ApiError messages
    App.jsx                Header + "New chat"
    components/
      ChatWindow.jsx       Messages, input, typing indicator, auto-scroll, retry
      MessageBubble.jsx    User / AI / error bubbles, 👍👎 feedback, Yes/No handoff buttons
      KnowledgePanel.jsx   Collapsible "Sources" list
      EscalationBanner.jsx "Escalated to a human agent. Ticket #XXXXX"
```

---

## Setup

**Prerequisites:** Python 3.11+ and Node.js 18+. You'll also need a free Groq API key from [console.groq.com](https://console.groq.com/keys).

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then paste your key into GROQ_API_KEY
```

### 2. Build the knowledge base

```bash
python -m app.ingest               # or: python app/ingest.py
```

The first run downloads the embedding model (~90 MB). Re-run this any time you edit an article: it drops and rebuilds the collection.

### 3. Start the API

```bash
uvicorn app.main:app --reload --reload-dir app --port 8000
```

`--reload-dir app` limits the file watcher to the source code. Without it, the watcher also sees `.venv` and restarts in a loop.

Interactive API docs: http://localhost:8000/docs

### 4. Start the frontend (new terminal)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

### 5. Run the tests (optional)

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest
```

The API tests mock retrieval and the LLM, so they run offline and don't use Groq quota.

---

## Example questions

| Try this | What you should see |
|---|---|
| How do I reset my password? | Step-by-step answer, source: *Resetting Your Password* |
| Can I get a refund on my monthly plan? | "No" + policy explanation, **no** escalation (it's a question, not a dispute) |
| How much does Pro cost? → *what about Business?* | Follow-up answered using conversation context |
| What's the API rate limit on the Pro plan? | 100 req/min, 50,000/day |
| How do I connect TaskFlow to Slack? | Setup steps from the Slack article |
| You charged me twice this month! | Answer + 🟧 escalation: *Billing dispute* |
| I want to delete my account | Deletion steps + escalation: *Account deletion request* |
| My lawyer will be in touch | Escalation: *Legal threat* |
| THIS IS BROKEN AND NOBODY HELPS ME | Escalation: *all caps / frustration* |
| Slack notifications aren't working → *I already tried reconnecting, still not working* | Second message escalates: *repeated negative sentiment* |
| Does TaskFlow have a native Linux app? | "I don't have information on that. Would you like me to connect you with a human agent?" with **Yes / No** buttons, no sources, no ticket yet |
| What's the weather in Mumbai? → **Yes, connect me** | Low retrieval confidence → offer (LLM not called) → ticket created on "yes" |
| Can you write me a poem? → *no thanks* | Offer declined, no ticket |

Then open http://localhost:8000/tickets to see the logged tickets.

---

## How escalation works

`classify_escalation()` in `llm.py` runs checks **cheapest first** and stops at the first one that fires. They're ordered so the most specific reason wins, so "Legal threat" is reported instead of a generic "low confidence".

| # | Check | Where | Example trigger | Ticket |
|---|---|---|---|---|
| 1 | **Sensitive topic** (regex) | `escalation_rules.py` | "charged me twice", "refund was denied", "delete my account", "lawyer" | immediately |
| 1 | **Explicit human request** | `escalation_rules.py` | "can I talk to a real person", "connect me to an agent" | immediately |
| 1 | **Frustration** | `escalation_rules.py` | ≥70% capital letters; "this is ridiculous"; **2+ mildly negative messages** across the conversation ("still not working", "already tried") | immediately |
| 2 | **Low retrieval confidence** | `rag.py` score | best cosine similarity < `0.35` | **ask first** |
| 3 | **Model couldn't answer** | `llm.py` | reply contains "I don't have information on that" | **ask first** |
| 4 | **LLM judge** | `gpt-oss-20b`, JSON mode | nuanced cases, e.g. "I'm about to switch to Asana, nothing works" or "you took money after I cancelled" | immediately |

**Ask-first handoff.** Checks 2–3 mean the question is simply out of scope, not urgent. Opening a ticket for "what's the weather?" would flood the support queue, so the decision carries `requires_confirmation=True`. The API replies with `offer_escalation: true`, and the offer is stored per conversation (`PendingOffer`). The customer's **next** message resolves it:

- **Yes:** a ticket is logged with the *original* question.
- **No:** "No problem! Is there anything else I can help you with?"
- **Anything else:** the offer is dropped and the message is answered as a new question.

Why this hybrid:

- **Rules are precise, free, and testable.** High-risk cases (legal, billing disputes) never depend on an LLM call succeeding.
- **Rules are tuned to avoid false positives.** "What is your refund policy?" and "How do I delete a task?" do *not* escalate. See `tests/test_escalation_rules.py`.
- **The LLM judge adds recall** for paraphrases that regex can't anticipate. Its prompt explicitly separates *questions about policy* from *disputes*.
- **It fails safe.** If the judge's call fails (rate limit, bad JSON), the decision defaults to "don't escalate", because checks 1–3 already covered the high-risk cases. A classifier outage never fails the customer's request.

---

## Error handling

| Situation | Backend | Frontend |
|---|---|---|
| `ingest` hasn't been run | `503`: "Knowledge base not found. Run `python -m app.ingest`…" | Shows the message in a red bubble |
| Groq rate limit / timeout / connection / bad key / unknown model | Mapped to a specific, customer-safe message → `503` | Shows the message + **Try again** |
| Escalation classifier fails | Logged; defaults to no escalation (request still succeeds) | — |
| Unexpected exception | Global handler → `500` `{"detail": "An unexpected server error occurred."}` (no stack trace leaked) | "Something went wrong on our end" |
| Backend unreachable / request timeout (45 s) | — | "We can't reach the support server…" + **Try again** |
| Empty or >2,000-character message | `422` (Pydantic validation) | Input enforces `maxLength`; friendly message |

---

## API reference

| Method | Path | Description |
|---|---|---|
| `POST` | `/chat` | `{message, conversation_id?}` → `{response, retrieved_sources[{title, snippet, score}], escalate, escalation_reason, ticket_id, offer_escalation, conversation_id}` |
| `GET` | `/health` | `{"status": "ok"}` |
| `GET` | `/tickets` | All escalation tickets, newest first (mock admin view) |

`conversation_id` is returned on the first message. Send it back to continue the same conversation, which enables follow-up questions, repeated-frustration detection, and answering a handoff offer. When `offer_escalation` is `true`, send `"yes"` or `"no"` as the next message.

---

## Design decisions & trade-offs

- **LLM model.** The spec asked for `llama-3.3-70b-versatile`, but Groq no longer serves it to this account (404 `model_not_found`). The default is `openai/gpt-oss-120b`, the largest general-purpose model available. It runs with `reasoning_effort="low"` for latency. Any Groq model can be swapped in via `GROQ_MODEL` in `.env`.
- **Separate classifier model.** Escalation classification uses the smaller `gpt-oss-20b`. It's a simple yes/no task, and on Groq's free tier each model has its own ~8K tokens-per-minute budget, so this roughly doubles throughput.
- **Chunk size: 500 tokens (as specified), measured.** `all-MiniLM-L6-v2` only embeds the first **256** tokens of its input, so the tail of a 500-token chunk isn't embedded. I compared it with 250-token chunks on 26 labelled questions. 500 put the correct article first **25/26** times, 250 only **23/26**. Larger chunks keep each article's opening (title + overview) together, which is what queries match best. The truncated tail still reaches the LLM as context.
- **Title-prefixed embeddings.** Each chunk is embedded as `"{article title}\n\n{chunk}"`, so chunks from the middle of an article still carry their topic. Stored text (shown as the snippet) stays clean.
- **Overlap at sentence level.** The splitter breaks text into pieces no larger than the overlap (≈ sentences), then merges them up to 500 tokens. If it split only on paragraphs, the 50-token overlap would almost always be empty, because a paragraph is longer than 50 tokens.
- **Only relevant chunks reach the LLM.** In testing, passing loosely related chunks for "My lawyer will be in touch" made the model invent a billing email address. Filtering by the relevance threshold, and skipping the LLM entirely when nothing passes, removed that failure mode.
- **In-memory conversation store** (history + pending handoff offers). Simple and thread-safe for a single process. Production would use Redis or a database so history survives restarts and scales across workers.
- **Sync endpoints.** `/chat` is a plain `def`, so FastAPI runs it in a thread pool. Every dependency (embeddings, Chroma, Groq SDK, sqlite3) is blocking.

## Limitations & next steps

- Retrieval is pure vector search. Adding hybrid BM25 + vector search would help with exact tokens like error codes (`dispatch_failed`, `429`).
- Answers aren't streamed. Server-sent events would make responses feel faster.
- Feedback (👍/👎) is only logged to the browser console. Persisting it would enable evaluating answer quality over time.
- Ticket IDs are random 5-digit mocks. A real system would integrate with a helpdesk (Zendesk, Intercom).
