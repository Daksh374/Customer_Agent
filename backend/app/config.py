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
TICKETS_DB_PATH = BACKEND_DIR / "tickets.db"

# --- Embeddings / vector store -----------------------------------------------
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME = "taskflow_kb"

# Chunking, measured in tokens of the embedding model's tokenizer.
CHUNK_SIZE_TOKENS = 500
CHUNK_OVERLAP_TOKENS = 50

# --- Retrieval -----------------------------------------------------------------
DEFAULT_TOP_K = 4
# Cosine similarity below which the best match is considered "low confidence".
RELEVANCE_THRESHOLD = float(os.getenv("RELEVANCE_THRESHOLD", "0.35"))

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
LLM_MAX_RETRIES = 1

# --- Conversations -------------------------------------------------------------
# Number of previous messages (user + assistant) sent to the LLM for context.
MAX_HISTORY_MESSAGES = 6

# --- API -----------------------------------------------------------------------
CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
