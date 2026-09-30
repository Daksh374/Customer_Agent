"""Render the help-center articles in `kb_source/*.md` into PDFs in `knowledge_base/`.

The PDFs are what the chatbot ingests. The markdown files are the editable
source: edit an article there, re-run this script, then re-run ingestion.

    python scripts/build_kb_pdfs.py
    python -m app.ingest

Only the small markdown subset used by the articles is supported:
`# title`, `## heading`, paragraphs, `- bullets`, `1. numbered steps`, and **bold**.
"""

import html
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate

BACKEND_DIR = Path(__file__).resolve().parent.parent
SOURCE_DIR = BACKEND_DIR / "kb_source"
OUTPUT_DIR = BACKEND_DIR / "knowledge_base"

BULLET = re.compile(r"^- (.*)")
NUMBERED = re.compile(r"^(\d+)\. (.*)")


def build_styles() -> dict[str, ParagraphStyle]:
    """Paragraph styles for the help-center PDF layout."""
    base = getSampleStyleSheet()
    body = ParagraphStyle("Body", parent=base["BodyText"], fontSize=10.5, leading=15, spaceAfter=6)
    return {
        "title": ParagraphStyle(
            "ArticleTitle", parent=base["Title"], fontSize=20, leading=24,
            alignment=0, textColor=colors.HexColor("#1f2a44"), spaceAfter=14,
        ),
        "heading": ParagraphStyle(
            "Heading", parent=base["Heading2"], fontSize=13, leading=17,
            textColor=colors.HexColor("#3b3f99"), spaceBefore=10, spaceAfter=4,
        ),
        "body": body,
        "list": ParagraphStyle("ListItem", parent=body, leftIndent=16, bulletIndent=4, spaceAfter=3),
    }


def inline_markup(text: str) -> str:
    """Escape XML special characters, then convert **bold** to ReportLab <b> tags."""
    escaped = html.escape(text, quote=False)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)


def parse_blocks(markdown: str) -> list[tuple[str, str, str | None]]:
    """Split markdown into (kind, text, bullet) blocks.

    Consecutive plain lines are joined into one paragraph; blank lines end it.
    """
    blocks: list[tuple[str, str, str | None]] = []
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            blocks.append(("body", " ".join(paragraph), None))
            paragraph.clear()

    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            flush()
        elif line.startswith("# "):
            flush()
            blocks.append(("title", line[2:], None))
        elif line.startswith("## "):
            flush()
            blocks.append(("heading", line[3:], None))
        elif match := BULLET.match(line):
            flush()
            blocks.append(("list", match.group(1), "•"))
        elif match := NUMBERED.match(line):
            flush()
            blocks.append(("list", match.group(2), f"{match.group(1)}."))
        else:
            paragraph.append(line)
    flush()
    return blocks


def render_pdf(source: Path, output: Path, styles: dict[str, ParagraphStyle]) -> str:
    """Render one markdown article to a PDF and return its title."""
    blocks = parse_blocks(source.read_text(encoding="utf-8"))
    title = next(text for kind, text, _ in blocks if kind == "title")

    story = []
    for kind, text, bullet in blocks:
        story.append(Paragraph(inline_markup(text), styles[kind], bulletText=bullet))

    doc = SimpleDocTemplate(
        str(output), pagesize=A4, title=title, author="Customer Help Center",
        leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
    )
    doc.build(story)
    return title


def main() -> None:
    """Rebuild every PDF from its markdown source, removing stale PDFs first."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    for old_pdf in OUTPUT_DIR.glob("*.pdf"):
        old_pdf.unlink()

    styles = build_styles()
    for source in sorted(SOURCE_DIR.glob("*.md")):
        output = OUTPUT_DIR / f"{source.stem}.pdf"
        title = render_pdf(source, output, styles)
        print(f"  {output.name:<48} {title}")


if __name__ == "__main__":
    main()
