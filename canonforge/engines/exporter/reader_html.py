"""
Single-file standalone interactive HTML reader generator.
"""
import re
import html
from pathlib import Path
from typing import Dict, List, Any

PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent
TEMPLATE_FILE = PACKAGE_ROOT / "data" / "templates" / "reader.html"

def get_reader_template() -> str:
    if TEMPLATE_FILE.is_file():
        return TEMPLATE_FILE.read_text(encoding="utf-8")
    return ""

def generate_html_reader(book_slug: str, chapters_data: List[Dict[str, Any]]) -> Path:
    """Generate self-contained, publication-grade HTML reader."""
    meta = get_book_metadata(MANUSCRIPT_DIR / book_slug)

    total_words = sum(c["word_count"] for c in chapters_data)
    est_reading_time = int(total_words / 225)

    toc_items = []
    chapters_html_list = []

    for idx, ch in enumerate(chapters_data, 1):
        ch_id = f"ch-{idx:02d}"
        toc_items.append(f'<li><a href="#{ch_id}" onclick="closeTocIfOpen()">Chapter {idx}: {html.escape(ch["title"])}</a></li>')

        ch_block = f"""
        <article id="{ch_id}" class="chapter-container">
          <div class="chapter-header">
            <div class="chapter-number">Chapter {idx}</div>
            <h2 class="chapter-title">{html.escape(ch["title"])}</h2>
          </div>
          <div class="chapter-body">
            {ch["html_body"]}
          </div>
        </article>
        """
        chapters_html_list.append(ch_block)

    full_html = get_reader_template().format(
        book_title=html.escape(meta["title"]),
        book_subtitle=html.escape(meta["subtitle"]),
        book_author=html.escape(meta["author"]),
        total_chapters=len(chapters_data),
        total_words=total_words,
        reading_time=est_reading_time,
        toc_items="\n".join(toc_items),
        chapters_html="\n".join(chapters_html_list)
    )

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = EXPORTS_DIR / f"{book_slug}.html"
    out_file.write_text(full_html, encoding="utf-8")
    return out_file

# ==============================================================================
# 2. STANDARDIZED VALID EPUB 3.0 GENERATOR (NATIVE PYTHON ZIPFILE)
# ==============================================================================
EPUB_CONTAINER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>
"""

EPUB_CSS = """
@charset "UTF-8";
body {
    font-family: Georgia, "Times New Roman", serif;
    font-size: 1.05em;
    line-height: 1.7;
    margin: 5%;
    padding: 0;
    text-align: justify;
}
h1, h2, h3 {
    text-align: center;
    font-weight: normal;
    color: #8b3a0f;
    margin-top: 1.5em;
    margin-bottom: 0.8em;
}
.chapter-number {
    text-align: center;
    font-size: 0.8em;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #666;
    margin-bottom: 0.3em;
}
p {
    margin-top: 0;
    margin-bottom: 1.2em;
    text-indent: 0;
}
p.first-p {
    text-indent: 0;
}
.scene-break {
    text-align: center;
    color: #8b3a0f;
    margin: 2em 0;
    font-size: 1.1em;
}
blockquote {
    border-left: 2px solid #8b3a0f;
    padding-left: 1em;
    margin: 1.5em 0;
    font-style: italic;
    color: #555;
}
.titlepage {
    text-align: center;
    margin-top: 20%;
}
.titlepage h1 {
    font-size: 2.2em;
    margin-bottom: 0.2em;
}
.titlepage .subtitle {
    font-size: 1.2em;
    font-style: italic;
    color: #666;
    margin-bottom: 2em;
}
.titlepage .author {
    font-size: 1.1em;
    text-transform: uppercase;
    letter-spacing: 2px;
}
"""

