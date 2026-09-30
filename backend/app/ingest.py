"""Ingestion pipeline: PDF / markdown articles -> chunks -> embeddings -> ChromaDB.

Run from the backend directory with either:

    python -m app.ingest
    python app/ingest.py

The script is idempotent: it drops and rebuilds the collection on every run,
so editing an article and re-running always leaves the store in sync.
"""

import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

# Allow `python app/ingest.py` (no package context) as well as `python -m app.ingest`.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chromadb
from pypdf import PdfReader

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

SUPPORTED_EXTENSIONS = {".pdf", ".md"}

# pypdf extracts ReportLab's bullet glyph as U+007F; other generators use
# U+2022 or the Symbol-font private-use character U+F0B7.
PDF_BULLET = re.compile(r"^[\s\x7f\u2022\uf0b7]*[\x7f\u2022\uf0b7]\s*", re.MULTILINE)
LIST_ITEM = re.compile(r"^(- |\d+\. )")

# Text at least this much larger than the body font is treated as a heading.
HEADING_SIZE_RATIO = 1.15


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
    section: str = ""  # heading of the section the chunk came from ("" = intro)

    @property
    def id(self) -> str:
        """Stable, human-readable ID, e.g. `04-returns-and-refunds.pdf::1`."""
        return f"{self.source_file}::{self.chunk_index}"


# --- Loading -------------------------------------------------------------------


def load_articles(directory: Path = KNOWLEDGE_BASE_DIR) -> list[Article]:
    """Load every PDF and markdown article in `directory`, sorted by filename.

    Files without extractable text (e.g. scanned PDFs, which would need OCR)
    are skipped with a warning rather than failing the whole ingest.
    """
    paths = sorted(p for p in directory.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS)
    if not paths:
        raise FileNotFoundError(f"No .pdf or .md files found in {directory}")

    articles = []
    for path in paths:
        article = parse_article(path)
        if article.body:
            articles.append(article)
        else:
            print(f"  WARNING: skipped {path.name}: no extractable text (scanned PDF?)")
    return articles


def parse_article(path: Path) -> Article:
    """Dispatch to the parser for the file's format."""
    if path.suffix.lower() == ".pdf":
        return parse_pdf(path)
    return parse_markdown(path)


def parse_pdf(path: Path) -> Article:
    """Extract an article from a PDF, marking section headings as `## ` lines.

    The body uses the same `## heading` convention as the markdown files, so
    both formats go through the same section-aware chunking. The title comes
    from the PDF's metadata, falling back to the first line of text, and is
    removed from the body (it is prepended again at embedding time).
    """
    reader = PdfReader(path)
    fragments: list[tuple[float, str]] = []

    def collect(text, cm, tm, font_dict, font_size):  # pypdf visitor callback
        if text.strip():
            fragments.append((round(font_size * tm[0], 1), text.strip()))

    raw = "\n".join(page.extract_text(visitor_text=collect) or "" for page in reader.pages)
    lines = clean_pdf_text(raw, find_headings(fragments)).splitlines()

    metadata_title = reader.metadata.title if reader.metadata else None
    first_line = lines[0].removeprefix("## ") if lines else ""
    title = (metadata_title or first_line or _title_from_filename(path)).strip()
    if lines and lines[0].removeprefix("## ").strip() == title:
        lines = lines[1:]
    return Article(source_file=path.name, title=title, body="\n".join(lines).strip())


def find_headings(fragments: list[tuple[float, str]]) -> set[str]:
    """Return text set in a noticeably larger font than the body text.

    The body font is the most common size, weighted by characters, so this
    works for any PDF generator without hard-coding point sizes.
    """
    if not fragments:
        return set()
    chars_per_size: Counter[float] = Counter()
    for size, text in fragments:
        chars_per_size[size] += len(text)
    body_size = chars_per_size.most_common(1)[0][0]
    return {text for size, text in fragments if size >= body_size * HEADING_SIZE_RATIO}


def clean_pdf_text(text: str, headings: set[str] = frozenset()) -> str:
    """Undo PDF layout artefacts so the text chunks and embeds like prose.

    Bullet glyphs become "- ", heading lines become "## heading", and lines
    that were broken only to fit the page width are joined back together.
    """
    text = PDF_BULLET.sub("- ", text)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    lines = [f"## {line}" if line in headings else line for line in lines if line]

    joined: list[str] = []
    for line in lines:
        if joined and _continues_previous_line(joined[-1], line):
            joined[-1] = f"{joined[-1]} {line}"
        else:
            joined.append(line)
    return "\n".join(joined)


def _continues_previous_line(previous: str, line: str) -> bool:
    """True if `line` is the wrapped continuation of `previous`.

    Headings and list items always start a new line. Otherwise a line
    continues the previous one if it starts in lowercase, or if the previous
    line stopped mid-sentence (no closing punctuation).
    """
    if previous.startswith("## ") or line.startswith("## ") or LIST_ITEM.match(line):
        return False
    return line[0].islower() or not previous.endswith((".", ":", "!", "?", ")"))


def parse_markdown(path: Path) -> Article:
    """Split a markdown file into its H1 title and the remaining body.

    Falls back to a title derived from the filename if there is no H1.
    """
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()
        body = "\n".join(lines[1:]).strip()
    else:
        title = _title_from_filename(path)
        body = "\n".join(lines)
    return Article(source_file=path.name, title=title, body=body)


def _title_from_filename(path: Path) -> str:
    """`05-product-exchange.pdf` -> `Product Exchange`."""
    stem = re.sub(r"^\d+[-_]", "", path.stem)
    return stem.replace("-", " ").replace("_", " ").title()


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


def split_sections(body: str) -> list[tuple[str, str]]:
    """Split an article body at `## ` headings into (heading, text) pairs.

    Text before the first heading (the introduction) gets an empty heading.
    """
    sections: list[tuple[str, list[str]]] = [("", [])]
    for line in body.splitlines():
        if line.startswith("## "):
            sections.append((line[3:].strip(), []))
        else:
            sections[-1][1].append(line)
    return [(heading, "\n".join(lines).strip()) for heading, lines in sections if any(lines)]


def chunk_article(article: Article) -> list[Chunk]:
    """Chunk each section of an article separately.

    Keeping chunks inside one section means a chunk never mixes two topics,
    e.g. the end of "Money deducted" with the start of "Charged twice", which
    would blur its embedding and hurt retrieval for both.
    """
    chunks: list[Chunk] = []
    for heading, text in split_sections(article.body):
        for piece in split_text(text):
            chunks.append(
                Chunk(
                    text=piece,
                    source_file=article.source_file,
                    article_title=article.title,
                    chunk_index=len(chunks),
                    section=heading,
                )
            )
    return chunks


# --- Storing -------------------------------------------------------------------


def text_for_embedding(chunk: Chunk) -> str:
    """Prefix the article title and section heading so every chunk carries its topic.

    A chunk from the middle of an article may never mention what it is about;
    "Payment Methods & Failures > Charged twice for one order" says it outright.
    """
    header = f"{chunk.article_title} > {chunk.section}" if chunk.section else chunk.article_title
    return f"{header}\n\n{chunk.text}"


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
                "section": chunk.section,
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
        print(f"  {article.source_file:<46} {n} chunk(s)  —  {article.title}")
    return len(chunks)


if __name__ == "__main__":
    ingest()
