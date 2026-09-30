"""Retrieval: find the knowledge-base chunks most relevant to a query."""

from dataclasses import dataclass
from functools import lru_cache

import chromadb
from chromadb.errors import NotFoundError

from app.config import CHROMA_DIR, COLLECTION_NAME, DEFAULT_TOP_K, RELEVANCE_THRESHOLD
from app.embeddings import embed_texts


class KnowledgeBaseNotReadyError(RuntimeError):
    """Raised when the vector store is missing or empty (ingest not run)."""


@dataclass
class RetrievedChunk:
    """A single search hit with its citation metadata."""

    text: str
    source_file: str
    article_title: str
    chunk_index: int
    score: float  # cosine similarity in [-1, 1]; higher is more similar
    section: str = ""  # section heading within the article ("" = intro)


@dataclass
class RetrievalResult:
    """Search hits plus a confidence flag used for escalation decisions."""

    chunks: list[RetrievedChunk]
    top_score: float
    low_confidence: bool

    def relevant_chunks(self) -> list[RetrievedChunk]:
        """Return only chunks whose score clears the relevance threshold."""
        return [c for c in self.chunks if c.score >= RELEVANCE_THRESHOLD]


@lru_cache(maxsize=1)
def _get_client() -> chromadb.ClientAPI:
    """Return a process-wide persistent Chroma client."""
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def get_collection() -> chromadb.Collection:
    """Fetch the knowledge-base collection, validating that it is populated.

    The collection handle is looked up on every call (it's cheap) rather than
    cached, so re-running ingest while the server is up doesn't leave the API
    holding a handle to a deleted collection.
    """
    try:
        collection = _get_client().get_collection(COLLECTION_NAME)
    except (NotFoundError, ValueError) as exc:
        raise KnowledgeBaseNotReadyError(
            "Knowledge base not found. Run `python -m app.ingest` from the backend directory first."
        ) from exc
    if collection.count() == 0:
        raise KnowledgeBaseNotReadyError(
            "Knowledge base is empty. Run `python -m app.ingest` from the backend directory."
        )
    return collection


def is_knowledge_base_ready() -> bool:
    """Return True if the collection exists and has documents."""
    try:
        get_collection()
        return True
    except KnowledgeBaseNotReadyError:
        return False


def retrieve(query: str, top_k: int = DEFAULT_TOP_K) -> RetrievalResult:
    """Return the `top_k` chunks most similar to `query`.

    Chroma returns cosine *distance* (0 = identical); it is converted to
    similarity (1 - distance) so that higher means more relevant. If even the
    best match is below `RELEVANCE_THRESHOLD`, the result is flagged
    `low_confidence` — the knowledge base probably doesn't cover the question.
    """
    collection = get_collection()
    results = collection.query(
        query_embeddings=embed_texts([query]),
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    chunks = _to_chunks(results)
    top_score = chunks[0].score if chunks else 0.0
    return RetrievalResult(
        chunks=chunks,
        top_score=top_score,
        low_confidence=top_score < RELEVANCE_THRESHOLD,
    )


def _to_chunks(results: dict) -> list[RetrievedChunk]:
    """Convert Chroma's nested query response into `RetrievedChunk`s."""
    # Chroma returns one list per query embedding; we only ever send one.
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]
    return [
        RetrievedChunk(
            text=doc,
            source_file=meta["source_file"],
            article_title=meta["article_title"],
            chunk_index=int(meta["chunk_index"]),
            score=round(1.0 - dist, 4),
            section=meta.get("section", ""),
        )
        for doc, meta, dist in zip(documents, metadatas, distances)
    ]
