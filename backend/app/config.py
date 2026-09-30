"""Central configuration.

All tunable values live here so the rest of the code never reads environment
variables directly. Paths are resolved relative to the backend directory, so
scripts work no matter which directory they are launched from.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

# --- Paths -----------------------------------------------------------------
KNOWLEDGE_BASE_DIR = BACKEND_DIR / "knowledge_base"
CHROMA_DIR = BACKEND_DIR / "chroma_db"
# SQLite database holding escalation tickets and conversation memory.
DB_PATH = BACKEND_DIR / "support.db"

# --- Embeddings / vector store -----------------------------------------------
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME = "support_kb"

# Chunking, measured in tokens of the embedding model's tokenizer. Articles
# are first split at their section headings, then long sections are split
# further. all-MiniLM-L6-v2 only embeds the first 256 tokens of its input, so
# chunks are kept just under that window. On a 44-question retrieval check,
# 500-token chunks (half never embedded) ranked the right article first 38/44
# times, flat 250-token chunks 40/44, and section-aware 250-token chunks 41/44.
CHUNK_SIZE_TOKENS = 250
CHUNK_OVERLAP_TOKENS = 50

# --- Retrieval -----------------------------------------------------------------
# Chunks are small (one section each), so 6 of them still fit comfortably in the prompt.
DEFAULT_TOP_K = 6
# Cosine similarity below which the best match is considered "low confidence".
# Set low on purpose: refusing a real question is worse than letting an
# off-topic one through, because the LLM still answers "I don't have
# information on that" for off-topic questions, which triggers the same offer.
RELEVANCE_THRESHOLD = float(os.getenv("RELEVANCE_THRESHOLD", "0.30"))

# --- LLM -----------------------------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
# The spec called for llama-3.3-70b-versatile, but Groq no longer serves it to
# this account; gpt-oss-120b is the closest large general-purpose replacement.
# Any Groq chat model can be swapped in via the GROQ_MODEL env var.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
# Escalation classification is a simple yes/no task, so a smaller, faster model
# is used. It also has its own rate-limit bucket on Groq's free tier.
GROQ_CLASSIFIER_MODEL = os.getenv("GROQ_CLASSIFIER_MODEL", "openai/gpt-oss-20b")
LLM_TIMEOUT_SECONDS = 20.0
# Retries honour Groq's Retry-After header, which smooths over brief rate limits.
LLM_MAX_RETRIES = 2

# --- Conversations -------------------------------------------------------------
# Number of previous messages (user + assistant) sent to the LLM for context.
MAX_HISTORY_MESSAGES = 6
# Earlier assistant replies are trimmed to this many characters in prompts;
# the gist is enough to resolve follow-ups and it keeps token usage low.
HISTORY_MESSAGE_MAX_CHARS = 500
# Number of recent messages copied into a ticket so the agent sees the context.
TICKET_TRANSCRIPT_MESSAGES = 10

# --- API -----------------------------------------------------------------------
CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
