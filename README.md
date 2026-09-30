# E-commerce AI Customer Support Agent

A full-stack customer support chatbot for an online shopping store. It answers questions about orders, delivery, returns, refunds, payments, and accounts using **Retrieval-Augmented Generation (RAG)** over a help center of 15 PDF articles, and it cites its sources. It **remembers the conversation**, so follow-ups like "what about electronics?" or "I paid by UPI" work. It **escalates to a human agent** (logging a ticket with the transcript) when a conversation involves a payment dispute, a legal threat, a counterfeit report, account deletion, frustration, or a request for a person. For questions outside the help center, it first **asks** whether the customer wants a human. The chat UI is mobile-first and responsive.

**Stack:** FastAPI · sentence-transformers (local embeddings) · ChromaDB · Groq LLM API · React (Vite) · SQLite · pypdf

---

## Architecture

```
                 ┌─────────────────────────────── OFFLINE (python -m app.ingest) ────────────────────────────────┐
                 │                                                                                                │
                 │  knowledge_base/*.pdf ─► extract text ─► detect headings ─► split into ─► chunk ─► embed ─► ChromaDB│
                 │  (15 help articles)     (pypdf)          (by font size)     sections     (≤250 tok) (MiniLM) (cosine)│
                 └────────────────────────────────────────────────────────────────────────────────────────────────┘

 ┌──────────────┐  POST /chat   ┌────────────────────── FastAPI (main.py → chat_service.py) ──────────────────────┐
 │ React (Vite) │ ────────────► │                                                                                │
 │ mobile-first │               │  1. Pending offer?     "yes" → ticket · "no" → close offer                     │
 │              │               │  2. Human request?     "talk to an agent" → ticket with transcript, no LLM     │
 │ ChatWindow   │               │  3. Small talk?        "hi" / "thanks" / "ok" → canned reply, no LLM           │
 │ MessageBubble│               │  4. Question:                                                                  │
 │ KnowledgePanel               │     rewrite_query()      history + message → standalone English question       │
 │ Escalation   │               │     retrieve()           embed → top-6 chunks → similarity (< 0.30 = low)      │
 │   Banner     │               │     generate_response()  relevant chunks + history → Groq (gpt-oss-120b)       │
 │              │ ◄──────────── │     classify_escalation() rules → confidence → "no info" → LLM judge           │
 └──────────────┘  JSON reply   │                                                                                │
                                │  memory.py: every turn + pending offers in SQLite (survives restarts)          │
                                │  db.py:     tickets (with transcript) in the same SQLite file                  │
                                └────────────────────────────────────────────────────────────────────────────────┘
```

### Request lifecycle (`POST /chat`)

`chat_service.handle_message()` routes each message through these steps, in order:

1. **Pending offer.** If the previous reply asked *"Would you like me to connect you with a human agent?"*, a yes (button or typed) opens a ticket for the original question, and a no closes the offer. Anything else drops the offer and continues below.
2. **Human request.** "Connect me with a human" or "talk to customer care" opens a ticket immediately. The ticket records the customer's latest real question plus the recent transcript, so the agent has context. No LLM call.
3. **Small talk.** Whole-message greetings, thanks, "ok", "no thanks", and "bye" get a canned reply without retrieval. (A bare "ok" right after the assistant asked a question is treated as an answer, not small talk.)
4. **Question.**
   - **Rewrite.** A small LLM (`gpt-oss-20b`) turns the message into a standalone English question using the conversation: "what about electronics?" becomes "What is the return window for electronics?", and Hinglish or typos are normalised. If the message isn't a question at all (e.g. a bare "yes" with nothing to agree to), the bot asks what the customer needs.
   - **Retrieve.** The standalone question is embedded and the 6 nearest chunks are fetched from ChromaDB (chunks are single sections, so 6 still fit easily in the prompt). Up to 3 articles scoring close to the best match are shown as sources.
   - **Generate.** Only chunks above the relevance threshold go to `gpt-oss-120b`, with the recent conversation and a system prompt that forbids outside knowledge, invented contact details, claims to have seen the customer's order, and self-made handoff offers. If no chunk is relevant, the LLM isn't called.
   - **Classify and log.** The escalation classifier decides whether a human should take over (see [How escalation works](#how-escalation-works)). Sensitive conversations get a ticket right away; out-of-scope questions get the ask-first offer, with no sources.

Every turn is saved to conversation memory in SQLite, so context survives a server restart. The frontend also saves the visible chat in `localStorage`, so a page refresh keeps the conversation.

---

## Knowledge base

The help center is **15 PDF articles** (about 11,700 words) for a fictional Indian online store. Prices are in rupees, written "Rs." because the PDFs' built-in font has no `₹` glyph.

| # | Article | Main questions it handles |
|---|---|---|
| 01 | Order Cancellation | Cancel an order, cancellation window, cancellation after shipping |
| 02 | Order Tracking | Where is my order, tracking status, delayed tracking, delivered but not received |
| 03 | Shipping & Delivery | Delivery times, shipping charges, delivery areas, failed delivery |
| 04 | Returns & Refunds | Return eligibility by category, refund process, refund timelines |
| 05 | Product Exchange | Size/colour exchange, exchange window, doorstep swap |
| 06 | Damaged, Defective or Wrong Product | Damaged, defective, or wrong item; proof required; replacement |
| 07 | Missing Items & Incomplete Orders | Missing product, missing accessories, split shipments |
| 08 | Payment Methods & Failures | UPI, cards, net banking, EMI, failed payment, money deducted, double charge |
| 09 | Cash on Delivery | COD availability, Rs. 50,000 limit, COD fee, verification |
| 10 | Coupons & Discounts | Coupon not working, coupon rules, bank offers, discounts on returns |
| 11 | Account, Login & Password | OTP issues, password reset, change mobile number, account deletion |
| 12 | Warranty & Replacement | Manufacturer warranty, claims, extended warranty and protection plans |
| 13 | Product Information & Availability | Size charts, stock, Notify Me, pre-orders, genuine products |
| 14 | Invoice & Order Documents | Download invoice, GST invoice, credit notes |
| 15 | General Customer Support FAQ | Support hours, tickets, grievance officer, gift wrapping, fraud safety |

**Editing articles.** The PDFs are generated from editable markdown sources in `backend/kb_source/`. To change an article:

```bash
python scripts/build_kb_pdfs.py    # kb_source/*.md → knowledge_base/*.pdf
python -m app.ingest               # rebuild the vector store
```

Ingestion also accepts **any other PDF or `.md` file** dropped into `knowledge_base/`. Scanned (image-only) PDFs are skipped with a warning, because they need OCR.

---

## Project structure

```
backend/
  knowledge_base/          15 help-center PDFs (what the chatbot ingests)
  kb_source/               Editable markdown sources for the PDFs
  scripts/build_kb_pdfs.py Renders kb_source/*.md into PDFs (ReportLab)
  app/
    config.py              All settings in one place (paths, model names, thresholds)
    embeddings.py          Shared sentence-transformers model (loaded once)
    ingest.py              Parse PDF/markdown → sections → chunks → embed → store. Idempotent.
    rag.py                 retrieve() + low-confidence flag + "KB not ingested" check
    llm.py                 Groq calls: rewrite_query(), generate_response(), classify_escalation()
    escalation_rules.py    Deterministic escalation rules (regex + heuristics)
    intents.py             Small talk and yes/no detection
    chat_service.py        The conversation pipeline (offer → human request → small talk → RAG)
    memory.py              Conversation history + pending offers, persisted in SQLite
    models.py              Pydantic request/response schemas
    db.py                  SQLite schema and ticket storage
    main.py                FastAPI app: routes, startup, HTTP error mapping
  tests/                   pytest suite (rules, intents, PDF parsing, chunking, pipeline with mocked LLM)
  requirements.txt
  requirements-dev.txt     pytest, httpx, reportlab (tests + PDF generation)
  .env.example
frontend/
  src/
    api.js                 fetch wrapper → user-friendly ApiError messages
    storage.js             Saves the open chat in localStorage (survives refresh)
    App.jsx                Mounts the chat; "New chat" resets it
    components/
      ChatWindow.jsx       Conversation state, sending, retry, smart auto-scroll
      ChatHeader.jsx       TaskFlow brand + "New chat" button
      WelcomeScreen.jsx    Topic cards + popular questions for an empty chat
      MessageBubble.jsx    User / AI / error bubbles, timestamps, Yes/No quick replies
      Composer.jsx         Auto-growing input, send button, Enter to send / Shift+Enter for a new line
      KnowledgePanel.jsx   Collapsible "Sources" list
      EscalationBanner.jsx Ticket card: "Escalated to a human agent · Ticket #XXXXX"
      Icons.jsx            Inline SVG icons
    styles.css             Design tokens, light/dark themes, mobile-first layout
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

### 2. Build the vector store

```bash
python -m app.ingest               # or: python app/ingest.py
```

The first run downloads the embedding model (~90 MB). Re-run this whenever the files in `knowledge_base/` change: it drops and rebuilds the collection.

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
| How do I return a product? | Step-by-step answer, source: *Returns & Refunds* |
| What is the return window for clothes? → *what about electronics?* → *and for a laptop?* | 10 days, then 7 days replacement-only, then the same for laptops (memory) |
| hi → I want to return my shoes → *how long will the refund take?* → *I paid by UPI* | Greeting, return steps, refund timelines, then "1 to 3 business days" |
| mera refund kab tak aayega? | Hinglish is understood (answer in English) |
| Where is my order? | How to track it in My Orders (the bot doesn't claim to see your order) |
| Money was deducted but my order was not placed | Auto-reversal timelines, **no** escalation (routine) |
| My coupon code is not working → *Yes* → *connect me with a human representative* | Checklist, then "what would you like help with?", then a ticket with the coupon issue and transcript |
| You charged me twice for one order! | Duplicate-payment answer + escalation: *Payment dispute* |
| I want to delete my account | Deletion steps + escalation: *Account deletion request* |
| This phone is fake, not original | Report steps + escalation: *Counterfeit or fraud report* |
| I will file a complaint in consumer court | Grievance info + escalation: *Legal threat* |
| THIS IS RIDICULOUS WHERE IS MY PARCEL | Escalation: *all caps / frustration* |
| The coupon is not working → *I already tried that, still not working* | Second message escalates: *repeated negative sentiment* |
| Do you sell second-hand cars? → **Yes, connect me** | Ask-first offer (no sources), then a ticket |
| Tell me a joke → *no* | Offer declined, no ticket |

Then open http://localhost:8000/tickets to see the logged tickets, including each one's transcript.

---|---|
| How do I return a product? | Step-by-step answer, source: *Returns & Refunds* |
| What is the return window for clothes? → *what about electronics?* | 10 days, then 7 days replacement-only (follow-up uses conversation context) |
| How long does a refund to UPI take? | 1 to 3 business days |
| What is the maximum order value for cash on delivery? | Rs. 50,000 |
| Where is my order? | How to track it in My Orders (the bot doesn't claim to see your order) |
| Money was deducted but my order was not placed | Auto-reversal timelines, **no** escalation (routine) |
| You charged me twice for one order! | Duplicate-payment answer + 🟧 escalation: *Payment dispute* |
| I want to delete my account | Deletion steps + escalation: *Account deletion request* |
| This phone is fake, not original | Report steps + escalation: *Counterfeit or fraud report* |
| I will file a complaint in consumer court | Grievance info + escalation: *Legal threat* |
| THIS IS RIDICULOUS WHERE IS MY PARCEL | Escalation: *all caps / frustration* |
| My coupon code is not working → *I already tried that, it is still not working* | Second message escalates: *repeated negative sentiment* |
| Do you sell second-hand cars? | "I don't have information on that. Would you like me to connect you with a human agent?" with **Yes / No** buttons, no sources, no ticket yet |
| What's the weather in Mumbai? → **Yes, connect me** | Offer, then a ticket created on "yes" |
| Can you write me a poem? → *no thanks* | Offer declined, no ticket |

Then open http://localhost:8000/tickets to see the logged tickets.

---

## How escalation works

`classify_escalation()` in `llm.py` runs checks **cheapest first** and stops at the first one that fires. They're ordered so the most specific reason wins, so "Legal threat" is reported instead of a generic "low confidence".

| # | Check | Where | Example trigger | Ticket |
|---|---|---|---|---|
| 1 | **Sensitive topic** (regex) | `escalation_rules.py` | "charged me twice", "refund was rejected", "delete my account", "consumer court", "fake, not original" | immediately |
| — | **Explicit human request** | `chat_service.py` (step 2, before any LLM call) | "connect me with a human", "talk to customer care" | immediately |
| 1 | **Frustration** | `escalation_rules.py` | ≥70% capital letters; "this is ridiculous"; **2+ mildly negative messages** across the conversation ("still not working", "already tried") | immediately |
| 2 | **Low retrieval confidence** | `rag.py` score | best cosine similarity < `0.30` | **ask first** |
| 3 | **Model couldn't answer** | `llm.py` | reply contains "I don't have information on that" | **ask first** |
| 4 | **LLM judge** | `gpt-oss-20b`, JSON mode | nuanced cases, e.g. "I'm never shopping here again" or "it's been 12 days and the deducted money still hasn't come back" | immediately |

**Ask-first handoff.** Checks 2–3 mean the question is simply out of scope, not urgent. Opening a ticket for "what's the weather?" would flood the support queue, so the decision carries `requires_confirmation=True`. The API replies with `offer_escalation: true`, and the offer is stored per conversation (`PendingOffer`). The customer's **next** message resolves it:

- **Yes:** a ticket is logged with the *original* question.
- **No:** "No problem! Is there anything else I can help you with?"
- **Anything else:** the offer is dropped and the message is answered as a new question.

Why this hybrid:

- **Rules are precise, free, and testable.** High-risk cases (legal threats, payment disputes) never depend on an LLM call succeeding.
- **Rules are tuned to avoid false positives.** "What is your refund policy?" and "How do I delete an address from my account?" do *not* escalate. See `tests/test_escalation_rules.py`.
- **The LLM judge adds recall** for paraphrases that regex can't anticipate. Its prompt separates *routine questions* ("money was deducted but no order", "can I return shoes after 15 days?") from *disputes* ("it's been 12 days and still no refund").
- **It fails safe.** If the judge's call fails (rate limit, bad JSON), the decision defaults to "don't escalate", because checks 1–3 already covered the high-risk cases. A classifier outage never fails the customer's request.

---

## Error handling

| Situation | Backend | Frontend |
|---|---|---|
| `ingest` hasn't been run | `503`: "Knowledge base not found. Run `python -m app.ingest`…" | Shows the message in a red bubble |
| Groq rate limit / timeout / connection / bad key / unknown model | Mapped to a specific, customer-safe message → `503` | Shows the message + **Try again** |
| Escalation classifier fails | Logged; defaults to no escalation (request still succeeds) | — |
| Scanned PDF with no text layer | Skipped during ingest with a warning | — |
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

- **Section-aware chunking.** PDFs lose their structure when converted to text, so headings are recovered by **font size**: any line noticeably larger than the most common (body) size is a heading. Each article is split at its headings, and each section is chunked separately. A chunk therefore never mixes two topics (e.g. the end of "Money deducted" with the start of "Charged twice"). Each chunk is embedded as `"{article title} > {section}\n\n{text}"`.
- **Chunk size chosen by measurement.** `all-MiniLM-L6-v2` only embeds the first **256** tokens of its input, so chunks are capped at 250 tokens with 50 tokens of overlap. I checked this on 44 labelled questions:

  | Chunking | Correct article ranked 1st | In top 4 | Lowest in-scope score | Highest out-of-scope score |
  |---|---|---|---|---|
  | 500 tokens, flat | 38/44 | 43/44 | 0.13 | 0.33 |
  | 250 tokens, flat | 40/44 | 44/44 | 0.24 | 0.34 |
  | **250 tokens, section-aware** | **41/44** | **44/44** | **0.32** | **0.25** |

  With section-aware chunks, in-scope and out-of-scope scores stop overlapping, so the **0.30 relevance threshold** cleanly separates them on this set. It's a small spot check, not a benchmark.
- **PDF text cleanup.** pypdf returns hard-wrapped lines and odd bullet glyphs. Ingestion turns bullets into `- ` and re-joins lines that were only wrapped to fit the page, so chunks read like prose.
- **LLM model.** The original spec asked for `llama-3.3-70b-versatile`, but Groq no longer serves it to this account (404 `model_not_found`). The default is `openai/gpt-oss-120b`, the largest general-purpose model available. It runs with `reasoning_effort="low"` for latency. Any Groq model can be swapped in via `GROQ_MODEL` in `.env`.
- **Separate classifier model.** Escalation classification uses the smaller `gpt-oss-20b`. It's a simple yes/no task, and on Groq's free tier each model has its own ~8K tokens-per-minute budget, so this roughly doubles throughput.
- **Only relevant chunks reach the LLM.** In testing, passing loosely related chunks made the model invent a contact email address. Filtering by the relevance threshold, and skipping the LLM entirely when nothing passes, removed that failure mode.
- **The bot is told it has no order data.** Without that rule, "Where is my order?" invites the model to make up a status.
- **Only the system offers human handoffs.** The model used to end answers with "Let me know if you'd like me to connect you…", but nothing tracked that offer, so the customer's "Yes" was answered as a new question. The prompt now forbids self-made offers, and the router owns every handoff.
- **Query rewriting for memory.** Passing history to the answering LLM isn't enough: retrieval also needs to know what "yes" or "what about electronics?" refers to. A cheap rewrite call on the small model produces a standalone question for retrieval. If that call fails, a heuristic (prefix the previous question) keeps things working.
- **Conversation memory in SQLite.** History and pending offers are stored per `conversation_id` in the same SQLite file as tickets, so they survive restarts. Older assistant replies are trimmed in prompts to save tokens.
- **Tested with a live conversation sweep.** About 80 turns (every article, multi-turn follow-ups, small talk, Hinglish, typos, off-topic questions) were run against the live API. The misses it surfaced were fixed: retrieving 6 chunks instead of 4, adding synonyms ("shoes", "customer care timings") and missing facts (PayPal not accepted) to the articles, making the rewriter turn statements like "I need a GST invoice" into questions, and stopping unnecessary disclaimers and clarifying questions.
- **Deterministic small talk.** Greetings and thanks don't need retrieval; routing them through RAG produced odd answers and wasted quota.
- **Sync endpoints.** `/chat` is a plain `def`, so FastAPI runs it in a thread pool. Every dependency (embeddings, Chroma, Groq SDK, sqlite3) is blocking.


