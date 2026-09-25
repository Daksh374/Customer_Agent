"""Ingestion pipeline: markdown articles -> chunks -> embeddings -> ChromaDB.

Run from the backend directory with either:

    python -m app.ingest
    python app/ingest.py

The script is idempotent: it drops and rebuilds the collection on every run,
so editing an article and re-running always leaves the store in sync.
"""

import sys
from dataclasses import dataclass
from pathlib import Path

# Allow `python app/ingest.py` (no package context) as well as `python -m app.ingest`.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb

from app.config import (
    CHROMA_DIR,
    CHUNK_OVERLAP_TOKENS,
    CHUNK_SIZE_TOKENS,
    COLLECTION_NAME,
    KNOWLEDGE_BASE_DIR,
)
from app.embeddings import count_tokens, embed_texts

# Tried in order: split on the coarsest boundary that exists in the text,
# falling back to finer ones only for pieces that are still too large.
SEPARATORS = ["\n\n", "\n", ". ", " "]


@dataclass
class Article:
    """A knowledge-base article loaded from disk."""

    source_file: str
    title: str
    body: str


@dataclass
class Chunk:
    """A piece of an article, ready to embed and store."""

    text: str
    source_file: str
    article_title: str
    chunk_index: int

    @property
    def id(self) -> str:
        """Stable, human-readable ID, e.g. `06-refund-policy.md::1`."""
        return f"{self.source_file}::{self.chunk_index}"


# --- Loading -------------------------------------------------------------------


def load_articles(directory: Path = KNOWLEDGE_BASE_DIR) -> list[Article]:
    """Load every `.md` file in `directory`, sorted by filename."""
    paths = sorted(directory.glob("*.md"))
    if not paths:
        raise FileNotFoundError(f"No markdown files found in {directory}")
    return [parse_article(path) for path in paths]


def parse_article(path: Path) -> Article:
    """Split a markdown file into its H1 title and the remaining body.

    Falls back to a title derived from the filename if there is no H1.
    """
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()
        body = "\n".join(lines[1:]).strip()
    else:
        title = path.stem.replace("-", " ").title()
        body = "\n".join(lines)
    return Article(source_file=path.name, title=title, body=body)


# --- Chunking ------------------------------------------------------------------


def split_text(
    text: str,
    chunk_size: int = CHUNK_SIZE_TOKENS,
    overlap: int = CHUNK_OVERLAP_TOKENS,
) -> list[str]:
    """Recursively split `text` into chunks of roughly `chunk_size` tokens.

    Two phases:
      1. Break the text into small pieces (at most `overlap` tokens) along
         natural boundaries: paragraphs, then lines, sentences, words.
      2. Greedily merge pieces back into chunks of up to `chunk_size`
         tokens, carrying the trailing pieces of each chunk (up to `overlap`
         tokens) into the start of the next one.

    Pieces must be no larger than the overlap, otherwise the overlap could
    never be filled (a whole paragraph is usually bigger than 50 tokens).
    """
    pieces = _split_recursive(text, max(overlap, 1), SEPARATORS)
    return _merge_pieces(pieces, chunk_size, overlap)


def _split_recursive(text: str, max_tokens: int, separators: list[str]) -> list[str]:
    """Split text into pieces no larger than `max_tokens` tokens.

    Uses the first separator; any resulting piece that is still too large is
    split again with the next separator. Separators are kept attached to the
    end of each piece so that joining the pieces reproduces the original text.
    """
    if count_tokens(text) <= max_tokens or not separators:
        return [text]

    separator, finer = separators[0], separators[1:]
    parts = text.split(separator)
    pieces = [part + separator for part in parts[:-1]] + [parts[-1]]

    result: list[str] = []
    for piece in pieces:
        if not piece:
            continue
        if count_tokens(piece) > max_tokens:
            result.extend(_split_recursive(piece, max_tokens, finer))
        else:
            result.append(piece)
    return result


def _merge_pieces(pieces: list[str], chunk_size: int, overlap: int) -> list[str]:
    """Greedily join pieces into chunks, with token overlap between chunks."""
    chunks: list[str] = []
    current: list[tuple[str, int]] = []  # (piece, token_count)
    current_tokens = 0

    for piece in pieces:
        tokens = count_tokens(piece)
        if current and current_tokens + tokens > chunk_size:
            chunks.append("".join(p for p, _ in current).strip())
            # Keep trailing pieces (up to `overlap` tokens) as the next chunk's start.
            while current and (current_tokens > overlap or current_tokens + tokens > chunk_size):
                current_tokens -= current.pop(0)[1]
        current.append((piece, tokens))
        current_tokens += tokens

    if current:
        chunks.append("".join(p for p, _ in current).strip())
    return [chunk for chunk in chunks if chunk]


def chunk_article(article: Article) -> list[Chunk]:
    """Turn one article into a list of `Chunk`s with citation metadata."""
    return [
        Chunk(
            text=text,
            source_file=article.source_file,
            article_title=article.title,
            chunk_index=index,
        )
        for index, text in enumerate(split_text(article.body))
    ]


# --- Storing -------------------------------------------------------------------


def text_for_embedding(chunk: Chunk) -> str:
    """Prefix the article title so every chunk carries its topic.

    A chunk from the middle of an article may never mention what the article
    is about; including the title makes those chunks far easier to retrieve.
    """
    return f"{chunk.article_title}\n\n{chunk.text}"


def rebuild_collection(client: chromadb.ClientAPI) -> chromadb.Collection:
    """Drop the collection if it exists and create a fresh, empty one."""
    if COLLECTION_NAME in [c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION_NAME)
    return client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def store_chunks(collection: chromadb.Collection, chunks: list[Chunk]) -> None:
    """Embed chunks and write them, with metadata, to ChromaDB."""
    collection.add(
        ids=[chunk.id for chunk in chunks],
        documents=[chunk.text for chunk in chunks],
        embeddings=embed_texts([text_for_embedding(chunk) for chunk in chunks]),
        metadatas=[
            {
                "source_file": chunk.source_file,
                "article_title": chunk.article_title,
                "chunk_index": chunk.chunk_index,
            }
            for chunk in chunks
        ],
    )


def ingest() -> int:
    """Run the full pipeline and return the number of chunks stored."""
    articles = load_articles()
    chunks = [chunk for article in articles for chunk in chunk_article(article)]

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = rebuild_collection(client)
    store_chunks(collection, chunks)

    print(f"Ingested {len(articles)} articles as {len(chunks)} chunks into '{COLLECTION_NAME}'.")
    for article in articles:
        n = sum(1 for c in chunks if c.source_file == article.source_file)
        print(f"  {article.source_file:<40} {n} chunk(s)  —  {article.title}")
    return len(chunks)


if __name__ == "__main__":
    ingest()
