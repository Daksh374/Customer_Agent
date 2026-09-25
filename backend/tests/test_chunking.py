from pathlib import Path

from app.embeddings import count_tokens
from app.ingest import parse_article, split_text

PARAGRAPH = "TaskFlow syncs changes in real time across web, desktop, and mobile apps. " * 6
LONG_TEXT = "\n\n".join(f"## Section {i}\n\n{PARAGRAPH}" for i in range(12))


def test_short_text_is_a_single_chunk():
    assert split_text("A short article.", chunk_size=500, overlap=50) == ["A short article."]


def test_chunks_respect_size_limit():
    chunks = split_text(LONG_TEXT, chunk_size=200, overlap=30)
    assert len(chunks) > 1
    # Piece token counts are summed, so allow a small tokenizer boundary tolerance.
    assert all(count_tokens(chunk) <= 210 for chunk in chunks)


def test_consecutive_chunks_overlap():
    chunks = split_text(LONG_TEXT, chunk_size=200, overlap=30)
    for previous, current in zip(chunks, chunks[1:]):
        tail = previous[-40:].strip()
        assert tail.split()[-1] in current[:300]


def test_parse_article_uses_h1_as_title(tmp_path: Path):
    path = tmp_path / "sample.md"
    path.write_text("# Resetting Your Password\n\nBody text here.")
    article = parse_article(path)
    assert article.title == "Resetting Your Password"
    assert article.body == "Body text here."


def test_parse_article_falls_back_to_filename(tmp_path: Path):
    path = tmp_path / "data-export.md"
    path.write_text("No heading here.")
    assert parse_article(path).title == "Data Export"
