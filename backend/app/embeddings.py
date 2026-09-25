"""Shared embedding model.

Loading a sentence-transformers model takes a few seconds, so it is loaded
once per process and reused by both ingestion and retrieval. Using the same
model for documents and queries is required for their vectors to be
comparable.
"""

from functools import lru_cache

from sentence_transformers import SentenceTransformer
from transformers.utils import logging as hf_logging

from app.config import EMBEDDING_MODEL

# The tokenizer warns whenever it sees text longer than the model's 256-token
# window. We deliberately count tokens of long text while chunking, and the
# encoder truncates on its own when embedding, so the warning is just noise.
hf_logging.set_verbosity_error()


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """Load (once) and return the sentence-transformers embedding model."""
    return SentenceTransformer(EMBEDDING_MODEL)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts into L2-normalised vectors.

    Normalising means cosine similarity equals the dot product, which keeps
    similarity scores in a predictable range.
    """
    vectors = get_embedding_model().encode(
        texts, normalize_embeddings=True, show_progress_bar=False
    )
    return vectors.tolist()


def count_tokens(text: str) -> int:
    """Count tokens using the embedding model's own tokenizer."""
    return len(get_embedding_model().tokenizer.tokenize(text))
