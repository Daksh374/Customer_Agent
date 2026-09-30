from pathlib import Path

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate

from app.embeddings import count_tokens
from app.ingest import chunk_article, clean_pdf_text, find_headings, parse_article, split_sections, split_text

PARAGRAPH = "Refunds to UPI are credited within 1 to 3 business days after the pickup is completed. " * 6
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


def test_parse_markdown_uses_h1_as_title(tmp_path: Path):
    path = tmp_path / "sample.md"
    path.write_text("# Order Tracking\n\nBody text here.")
    article = parse_article(path)
    assert article.title == "Order Tracking"
    assert article.body == "Body text here."


def test_title_falls_back_to_filename(tmp_path: Path):
    path = tmp_path / "05-product-exchange.md"
    path.write_text("No heading here.")
    assert parse_article(path).title == "Product Exchange"


def test_clean_pdf_text_rejoins_wrapped_lines_and_marks_headings():
    raw = (
        "Refund timelines\n"
        "\x7f UPI: 1 to 3 business\ndays after pickup.\n"
        "EMI tenures are 3, 6, 12, and\n24 months.\n"
        "Cards take longer."
    )
    assert clean_pdf_text(raw, headings={"Refund timelines"}) == (
        "## Refund timelines\n"
        "- UPI: 1 to 3 business days after pickup.\n"
        "EMI tenures are 3, 6, 12, and 24 months.\n"
        "Cards take longer."
    )


def test_find_headings_uses_font_size_relative_to_body():
    fragments = [(20.0, "Title"), (13.0, "Refund timelines"), (10.5, "Body text " * 20), (10.5, "More body")]
    assert find_headings(fragments) == {"Title", "Refund timelines"}


def test_split_sections_keeps_intro_and_headings():
    body = "Intro line.\n## Charges\nExchanges are free.\n## Timeline\n3 to 7 days."
    assert split_sections(body) == [
        ("", "Intro line."),
        ("Charges", "Exchanges are free."),
        ("Timeline", "3 to 7 days."),
    ]


def test_chunks_never_span_two_sections(tmp_path: Path):
    path = tmp_path / "exchange.md"
    path.write_text("# Product Exchange\n\n## Charges\n\nExchanges are free.\n\n## Timeline\n\n3 to 7 days.")
    chunks = chunk_article(parse_article(path))
    assert [(c.section, c.text) for c in chunks] == [("Charges", "Exchanges are free."), ("Timeline", "3 to 7 days.")]


def test_parse_pdf_reads_metadata_title_and_body(tmp_path: Path):
    path = tmp_path / "09-cash-on-delivery.pdf"
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), title="Cash on Delivery")
    doc.build([
        Paragraph("Cash on Delivery", styles["Title"]),
        Paragraph("COD limits", styles["Heading2"]),
        Paragraph("COD is available on orders up to Rs. 50,000.", styles["BodyText"]),
    ])

    article = parse_article(path)
    assert article.title == "Cash on Delivery"
    assert article.body == "## COD limits\nCOD is available on orders up to Rs. 50,000."
