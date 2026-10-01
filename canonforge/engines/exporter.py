#!/usr/bin/env python3
"""
export_ebook.py

Authoritative E-Book & Reader Publication Generator for Convergence Studio.
Converts markdown manuscripts into:
1. Standalone Interactive HTML Book Reader (.html)
   - Self-contained, responsive, offline-ready.
   - Themes: Ivory Paper, Warm Sepia, Midnight Dark, High Contrast.
   - Features: Floating Table of Contents, Reading Progress, Drop-caps, Font Sizer.
2. Standard Valid EPUB 3.0 / 2.0 E-Book (.epub)
   - Built natively via Python standard library (zipfile, xml).
   - Valid metadata, spine, manifest, toc.ncx, and nav.xhtml.
   - Ready for Apple Books, Kindle (Send-to-Kindle), Kobo, and Calibre.

Usage:
    uv run scripts/export_ebook.py --book the-sun-sanctum-apprentice
    uv run scripts/export_ebook.py --book the-sun-sanctum-apprentice --html-only
    uv run scripts/export_ebook.py --book the-sun-sanctum-apprentice --epub-only
"""

import sys
import os
import re
import html
import uuid
import zipfile
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
CONVERGENCE_DIR = SCRIPT_DIR.parent
MANUSCRIPT_DIR = CONVERGENCE_DIR / "manuscript"
EXPORTS_DIR = MANUSCRIPT_DIR / "_build" / "exports"

BOOK_METADATA = {
    "the-sun-sanctum-apprentice": {
        "title": "The Sun-Sanctum Apprentice",
        "subtitle": "Book 1 of the Aurei Academy Saga",
        "author": "Convergence Studio",
        "publisher": "Aethelgard Imprint",
        "language": "en",
        "description": "An official 1:1 adaptation of the classic magical school journey into the high-fantasy aether-industrial universe of Convergence.",
        "rights": "All rights reserved. Convergence Universe.",
    },
    "the-sun-sanctum-adept": {
        "title": "The Sun-Sanctum Adept",
        "subtitle": "Book 2 of the Aurei Academy Saga",
        "author": "Convergence Studio",
        "publisher": "Aethelgard Imprint",
        "language": "en",
        "description": "An official 1:1 adaptation of the Chamber of Secrets journey into the high-fantasy aether-industrial universe of Convergence.",
        "rights": "All rights reserved. Convergence Universe.",
    },
    "the-sun-sanctum-disciple": {
        "title": "The Sun-Sanctum Disciple",
        "subtitle": "Book 3 of the Aurei Academy Saga",
        "author": "Convergence Studio",
        "publisher": "Aethelgard Imprint",
        "language": "en",
        "description": "An official 1:1 adaptation of the Prisoner of Azkaban journey into the high-fantasy aether-industrial universe of Convergence.",
        "rights": "All rights reserved. Convergence Universe.",
    },
    "book-1-the-stone-child": {
        "title": "The Stone Child",
        "subtitle": "Book 1 of the Convergence Saga",
        "author": "Convergence Studio",
        "publisher": "Aethelgard Imprint",
        "language": "en",
        "description": "The tragic journey of a mute orphan, an ancient granite golem, and a disgraced soldier during the brutal tri-polar war of Oryn.",
        "rights": "All rights reserved. Convergence Universe.",
    },
    "book-2-the-iron-pilgrimage": {
        "title": "The Iron Pilgrimage",
        "subtitle": "Book 2 of the Convergence Saga",
        "author": "Convergence Studio",
        "publisher": "Aethelgard Imprint",
        "language": "en",
        "description": "Following the tragic fall of the river willow, Kazan and the mute child Bryn traverse the war-torn frontier of Oryn under the shadow of the Gray Syndicate.",
        "rights": "All rights reserved. Convergence Universe.",
    },
    "the-sun-sanctum-champion": {
        "title": "The Sun-Sanctum Champion",
        "subtitle": "Book 4 of the Aurei Academy Saga",
        "author": "Convergence Studio",
        "publisher": "Aethelgard Imprint",
        "language": "en",
        "description": "The Tournament of the Three Spires ignites long-simmering hostilities between Aurei, Korvath, and Ghar-Valen as Vaelin is thrust into lethal trials.",
        "rights": "All rights reserved. Convergence Universe.",
    },
    "the-sun-sanctum-order": {
        "title": "The Sun-Sanctum Order",
        "subtitle": "Book 5 of the Aurei Academy Saga",
        "author": "Convergence Studio",
        "publisher": "Aethelgard Imprint",
        "language": "en",
        "description": "The high spires tremble under tyrannical decree as the Dawn-Shield stands against Synod denial and the gathering shadows of the Black Sun.",
        "rights": "All rights reserved. Convergence Universe.",
    },
    "the-sun-sanctum-prince": {
        "title": "The Sun-Sanctum Prince",
        "subtitle": "Book 6 of the Aurei Academy Saga",
        "author": "Convergence Studio",
        "publisher": "Aethelgard Imprint",
        "language": "en",
        "description": "Amidst open war and ancient memories, Vaelin unravels the mystery of the Seven Soul-Anchors guided by the battered grimoire of the Half-Blood Prince.",
        "rights": "All rights reserved. Convergence Universe.",
    },
    "the-sun-sanctum-relics": {
        "title": "The Sun-Sanctum Relics",
        "subtitle": "Book 7 of the Aurei Academy Saga",
        "author": "Convergence Studio",
        "publisher": "Aethelgard Imprint",
        "language": "en",
        "description": "The fall of the Ministry, the exile into the wilderness, and the desperate hunt for the Soul-Anchors as the shadow of the Black Sun tightens across Oryn.",
        "rights": "All rights reserved. Convergence Universe.",
    },
    "the-battle-of-the-spires": {
        "title": "The Battle of the Spires",
        "subtitle": "Book 8 of the Aurei Academy Saga — The Grand Finale",
        "author": "Convergence Studio",
        "publisher": "Aethelgard Imprint",
        "language": "en",
        "description": "The climactic siege of the mountain sanctum. The dragon's flight, the burning spires, and the sacrifice that decides the fate of the Living Force before the shadows of The Maw.",
        "rights": "All rights reserved. Convergence Universe.",
    }
}

# ==============================================================================
# LIGHTWEIGHT MARKDOWN TO CLEAN XHTML/HTML CONVERTER
# ==============================================================================
def markdown_to_html_body(md_text: str) -> Tuple[str, str]:
    """Convert novel chapter markdown into semantic HTML/XHTML."""
    # Strip YAML frontmatter
    body = re.sub(r"^---\s*\n.*?\n---\s*\n", "", md_text, flags=re.DOTALL)
    
    # Extract chapter title
    title_match = re.search(r"^#\s+(.+)$", body, flags=re.MULTILINE)
    chapter_title = title_match.group(1).strip() if title_match else "Chapter"
    
    # Remove top-level h1 from body to avoid duplication
    body = re.sub(r"^#\s+.+$", "", body, count=1, flags=re.MULTILINE)
    
    # Replace wiki links [[Target|Display]] -> Display, [[Target]] -> Target
    body = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r"\2", body)
    body = re.sub(r"\[\[([^\]]+)\]\]", r"\1", body)

    lines = body.splitlines()
    html_lines = []
    in_blockquote = False
    in_list = False
    is_first_p = True

    for raw_line in lines:
        line = raw_line.strip()
        
        # Blank line
        if not line:
            if in_blockquote:
                html_lines.append("</blockquote>")
                in_blockquote = False
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            continue

        # Ornamental scene breaks
        if re.match(r"^(\*\s*\*\s*\*|\*{3,}|_{3,}|-{3,})$", line):
            if in_blockquote:
                html_lines.append("</blockquote>")
                in_blockquote = False
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append('<div class="scene-break">✦ &#160; ✦ &#160; ✦</div>')
            is_first_p = True
            continue

        # Headings (h2, h3)
        h2_match = re.match(r"^##\s+(.+)$", line)
        if h2_match:
            html_lines.append(f'<h2>{html.escape(h2_match.group(1).strip())}</h2>')
            continue
        h3_match = re.match(r"^###\s+(.+)$", line)
        if h3_match:
            html_lines.append(f'<h3>{html.escape(h3_match.group(1).strip())}</h3>')
            continue

        # Blockquote
        if line.startswith(">"):
            if not in_blockquote:
                html_lines.append("<blockquote>")
                in_blockquote = True
            q_text = line.lstrip("> ").strip()
            # Inline formatting
            q_text = format_inlines(q_text)
            html_lines.append(f"<p>{q_text}</p>")
            continue

        # Unordered list
        if line.startswith(("- ", "* ")) and not re.match(r"^(\*\s*\*\s*\*|\*{3,})$", line):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            item_text = line[2:].strip()
            item_text = format_inlines(item_text)
            html_lines.append(f"<li>{item_text}</li>")
            continue

        # Normal paragraph
        p_text = format_inlines(line)
        if is_first_p:
            html_lines.append(f'<p class="first-p">{p_text}</p>')
            is_first_p = False
        else:
            html_lines.append(f"<p>{p_text}</p>")

    if in_blockquote:
        html_lines.append("</blockquote>")
    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines), chapter_title

def format_inlines(text: str) -> str:
    """Format bold, italic, and escape xml/html."""
    # Escape basic HTML chars first (except we handle bold/italic safely)
    t = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    # Bold italic: ***text***
    t = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", t)
    # Bold: **text**
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    # Italic: *text*
    t = re.sub(r"\*([^*\n]+?)\*", r"<em>\1</em>", t)
    # Inline code: `text`
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return t

# ==============================================================================
# 1. STANDALONE INTERACTIVE HTML READER GENERATOR
# ==============================================================================
HTML_READER_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{book_title} — Reader Edition</title>
<style>
:root {{
  --bg: #fbf9f4;
  --text: #2c2523;
  --accent: #9a471b;
  --secondary: #6e655f;
  --border: #e6dfd5;
  --card-bg: #f4eee1;
  --font-body: 'Iowan Old Style', 'Palatino Linotype', 'Book Antiqua', Palatino, Georgia, serif;
  --font-ui: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  --max-w: 680px;
  --font-size: 19px;
  --line-height: 1.82;
}}

body[data-theme="sepia"] {{
  --bg: #f4ecd8;
  --text: #3c3227;
  --accent: #8b3a0f;
  --secondary: #706253;
  --border: #dfd4bc;
  --card-bg: #e8debe;
}}

body[data-theme="dark"] {{
  --bg: #161514;
  --text: #ded9d2;
  --accent: #e58a4e;
  --secondary: #9c958c;
  --border: #2a2826;
  --card-bg: #211f1d;
}}

body[data-theme="clean"] {{
  --bg: #ffffff;
  --text: #1a1a1a;
  --accent: #b22222;
  --secondary: #555555;
  --border: #eaeaea;
  --card-bg: #f9f9f9;
}}

* {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
  background-color: var(--bg);
  color: var(--text);
  font-family: var(--font-body);
  font-size: var(--font-size);
  line-height: var(--line-height);
  transition: background-color 0.25s ease, color 0.25s ease;
  -webkit-font-smoothing: antialiased;
}}

/* Top Navigation Bar */
header.top-nav {{
  position: sticky;
  top: 0;
  z-index: 100;
  background-color: var(--bg);
  border-bottom: 1px solid var(--border);
  padding: 12px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: var(--font-ui);
  font-size: 14px;
  backdrop-filter: blur(10px);
}}

.nav-title {{
  font-weight: 600;
  color: var(--accent);
  letter-spacing: 0.5px;
}}

.nav-controls {{
  display: flex;
  gap: 12px;
  align-items: center;
}}

.btn {{
  background: var(--card-bg);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-family: var(--font-ui);
  transition: all 0.2s ease;
}}
.btn:hover {{
  border-color: var(--accent);
  color: var(--accent);
}}

/* Progress Bar */
#progress-bar {{
  position: fixed;
  top: 0;
  left: 0;
  height: 3px;
  background: var(--accent);
  width: 0%;
  z-index: 999;
  transition: width 0.1s linear;
}}

/* Sidebar TOC Drawer */
#toc-drawer {{
  position: fixed;
  top: 49px;
  left: -320px;
  width: 320px;
  height: calc(100vh - 49px);
  background: var(--card-bg);
  border-right: 1px solid var(--border);
  z-index: 90;
  overflow-y: auto;
  padding: 24px;
  transition: left 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  font-family: var(--font-ui);
}}

#toc-drawer.open {{
  left: 0;
}}

#toc-drawer h3 {{
  font-size: 16px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--secondary);
  margin-bottom: 16px;
}}

#toc-drawer ul {{
  list-style: none;
}}

#toc-drawer li {{
  margin-bottom: 10px;
}}

#toc-drawer a {{
  color: var(--text);
  text-decoration: none;
  font-size: 14px;
  display: block;
  padding: 6px 8px;
  border-radius: 4px;
  transition: all 0.15s ease;
}}

#toc-drawer a:hover {{
  background: var(--border);
  color: var(--accent);
}}

/* Book Container */
main.book-content {{
  max-width: var(--max-w);
  margin: 0 auto;
  padding: 60px 24px 120px 24px;
}}

/* Title Page Presentation */
.title-page {{
  text-align: center;
  padding: 80px 0 100px 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 80px;
}}

.title-page h1 {{
  font-size: 42px;
  line-height: 1.2;
  color: var(--accent);
  margin-bottom: 12px;
  letter-spacing: -0.5px;
}}

.title-page .subtitle {{
  font-size: 20px;
  font-style: italic;
  color: var(--secondary);
  margin-bottom: 32px;
}}

.title-page .author {{
  font-size: 16px;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: var(--text);
  margin-bottom: 16px;
}}

.title-page .meta-pills {{
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 24px;
  font-family: var(--font-ui);
  font-size: 13px;
  color: var(--secondary);
}}

.pill {{
  background: var(--card-bg);
  border: 1px solid var(--border);
  padding: 4px 12px;
  border-radius: 20px;
}}

/* Chapter Styling */
.chapter-container {{
  margin-bottom: 100px;
  padding-bottom: 60px;
  border-bottom: 1px solid var(--border);
}}

.chapter-header {{
  text-align: center;
  margin-bottom: 40px;
}}

.chapter-number {{
  font-family: var(--font-ui);
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 2.5px;
  color: var(--accent);
  margin-bottom: 8px;
}}

.chapter-title {{
  font-size: 32px;
  line-height: 1.25;
  color: var(--text);
  font-weight: normal;
}}

/* Typography Details */
p {{
  margin-bottom: 1.4em;
  text-align: justify;
  text-justify: inter-word;
  hyphens: auto;
}}

p.first-p::first-letter {{
  font-size: 3.6em;
  float: left;
  line-height: 0.8;
  margin: 6px 12px 0 0;
  color: var(--accent);
  font-family: var(--font-body);
  font-weight: bold;
}}

blockquote {{
  border-left: 3px solid var(--accent);
  padding-left: 20px;
  margin: 24px 0;
  font-style: italic;
  color: var(--secondary);
}}

.scene-break {{
  text-align: center;
  font-size: 16px;
  color: var(--accent);
  margin: 40px 0;
  letter-spacing: 4px;
}}

h2, h3 {{
  margin: 32px 0 16px 0;
  color: var(--accent);
}}

code {{
  font-family: monospace;
  background: var(--card-bg);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
}}

/* Footer */
footer.book-footer {{
  text-align: center;
  font-family: var(--font-ui);
  font-size: 13px;
  color: var(--secondary);
  padding: 40px 0;
  border-top: 1px solid var(--border);
}}
</style>
</head>
<body data-theme="paper">

<div id="progress-bar"></div>

<header class="top-nav">
  <div style="display:flex; align-items:center; gap:16px;">
    <button class="btn" onclick="toggleToc()">☰ Table of Contents</button>
    <div class="nav-title">{book_title}</div>
  </div>
  <div class="nav-controls">
    <button class="btn" onclick="changeFontSize(-1)">A-</button>
    <button class="btn" onclick="changeFontSize(1)">A+</button>
    <button class="btn" onclick="cycleTheme()">🎨 Theme</button>
  </div>
</header>

<div id="toc-drawer">
  <h3>Table of Contents</h3>
  <ul>
    {toc_items}
  </ul>
</div>

<main class="book-content" onclick="closeTocIfOpen()">

  <div class="title-page">
    <h1>{book_title}</h1>
    <div class="subtitle">{book_subtitle}</div>
    <div class="author">{book_author}</div>
    <div class="meta-pills">
      <span class="pill">{total_chapters} Chapters</span>
      <span class="pill">{total_words:,} Words</span>
      <span class="pill">~{reading_time} min read</span>
    </div>
  </div>

  {chapters_html}

  <footer class="book-footer">
    <p>Published in the Convergence Universe &bull; Aethelgard Canonical Imprint</p>
    <p style="margin-top:6px; font-size:12px;">Generated via Convergence Novel Studio</p>
  </footer>
</main>

<script>
function toggleToc() {{
  document.getElementById('toc-drawer').classList.toggle('open');
}}
function closeTocIfOpen() {{
  document.getElementById('toc-drawer').classList.remove('open');
}}

let currentSize = 19;
function changeFontSize(delta) {{
  currentSize = Math.max(15, Math.min(26, currentSize + delta));
  document.body.style.setProperty('--font-size', currentSize + 'px');
}}

const themes = ['paper', 'sepia', 'dark', 'clean'];
let themeIdx = 0;
function cycleTheme() {{
  themeIdx = (themeIdx + 1) % themes.length;
  document.body.setAttribute('data-theme', themes[themeIdx]);
}}

window.addEventListener('scroll', () => {{
  const total = document.documentElement.scrollHeight - window.innerHeight;
  const progress = (window.scrollY / Math.max(1, total)) * 100;
  document.getElementById('progress-bar').style.width = progress + '%';
}});
</script>
</body>
</html>
"""

def generate_html_reader(book_slug: str, chapters_data: List[Dict[str, Any]]) -> Path:
    """Generate self-contained, publication-grade HTML reader."""
    meta = BOOK_METADATA.get(book_slug, {
        "title": book_slug.replace("-", " ").title(),
        "subtitle": "A Novel of Convergence",
        "author": "Convergence Studio",
        "publisher": "Aethelgard Imprint"
    })

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

    full_html = HTML_READER_TEMPLATE.format(
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

def generate_epub(book_slug: str, chapters_data: List[Dict[str, Any]]) -> Path:
    """Natively compile valid, publication-grade EPUB 3.0 file."""
    meta = BOOK_METADATA.get(book_slug, {
        "title": book_slug.replace("-", " ").title(),
        "subtitle": "A Novel of Convergence",
        "author": "Convergence Studio",
        "publisher": "Aethelgard Imprint",
        "language": "en",
        "description": "Convergence Universe Saga",
        "rights": "All rights reserved."
    })

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    epub_path = EXPORTS_DIR / f"{book_slug}.epub"
    book_uuid = str(uuid.uuid4())
    mod_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    with zipfile.ZipFile(epub_path, "w") as zf:
        # 1. Mimetype must be uncompressed and first entry
        mimetype_info = zipfile.ZipInfo("mimetype")
        mimetype_info.compress_type = zipfile.ZIP_STORED
        zf.writestr(mimetype_info, b"application/epub+zip")

        # 2. META-INF/container.xml
        zf.writestr("META-INF/container.xml", EPUB_CONTAINER_XML)

        # 3. OEBPS/style.css
        zf.writestr("OEBPS/style.css", EPUB_CSS)

        # 4. Titlepage
        titlepage_html = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en">
<head>
    <title>{html.escape(meta["title"])}</title>
    <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
    <div class="titlepage">
        <h1>{html.escape(meta["title"])}</h1>
        <div class="subtitle">{html.escape(meta["subtitle"])}</div>
        <div class="author">{html.escape(meta["author"])}</div>
        <p style="margin-top: 3em; font-size: 0.85em; color: #888;">{html.escape(meta["publisher"])}</p>
    </div>
</body>
</html>
"""
        zf.writestr("OEBPS/titlepage.xhtml", titlepage_html)

        # 5. Chapters XHTML
        manifest_items = [
            '<item id="style" href="style.css" media-type="text/css"/>',
            '<item id="titlepage" href="titlepage.xhtml" media-type="application/xhtml+xml"/>',
            '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
            '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
        ]
        spine_items = [
            '<itemref idref="titlepage"/>'
        ]
        nav_toc_list = []
        ncx_nav_points = []

        for idx, ch in enumerate(chapters_data, 1):
            ch_filename = f"ch{idx:02d}.xhtml"
            ch_id = f"ch{idx:02d}"
            manifest_items.append(f'<item id="{ch_id}" href="{ch_filename}" media-type="application/xhtml+xml"/>')
            spine_items.append(f'<itemref idref="{ch_id}"/>')
            
            nav_toc_list.append(f'<li><a href="{ch_filename}">Chapter {idx}: {html.escape(ch["title"])}</a></li>')
            ncx_nav_points.append(f"""
            <navPoint id="navPoint-{idx+1}" playOrder="{idx+1}">
                <navLabel><text>Chapter {idx}: {html.escape(ch["title"])}</text></navLabel>
                <content src="{ch_filename}"/>
            </navPoint>
            """)

            chapter_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en">
<head>
    <title>Chapter {idx}: {html.escape(ch["title"])}</title>
    <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
    <div class="chapter-number">Chapter {idx}</div>
    <h2>{html.escape(ch["title"])}</h2>
    {ch["html_body"]}
</body>
</html>
"""
            zf.writestr(f"OEBPS/{ch_filename}", chapter_xhtml)

        # 6. Nav Document (EPUB 3)
        nav_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en">
<head>
    <title>Table of Contents</title>
    <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
    <nav epub:type="toc" id="toc">
        <h1>Table of Contents</h1>
        <ol>
            {chr(10).join(nav_toc_list)}
        </ol>
    </nav>
</body>
</html>
"""
        zf.writestr("OEBPS/nav.xhtml", nav_xhtml)

        # 7. NCX Document (EPUB 2 backward compatibility)
        toc_ncx = f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="urn:uuid:{book_uuid}"/>
        <meta name="dtb:depth" content="1"/>
        <meta name="dtb:totalPageCount" content="0"/>
        <meta name="dtb:maxPageNumber" content="0"/>
    </head>
    <docTitle><text>{html.escape(meta["title"])}</text></docTitle>
    <docAuthor><text>{html.escape(meta["author"])}</text></docAuthor>
    <navMap>
        <navPoint id="navPoint-1" playOrder="1">
            <navLabel><text>Title Page</text></navLabel>
            <content src="titlepage.xhtml"/>
        </navPoint>
        {"".join(ncx_nav_points)}
    </navMap>
</ncx>
"""
        zf.writestr("OEBPS/toc.ncx", toc_ncx)

        # 8. Content.opf (Master Package Document)
        content_opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="3.0">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:identifier id="BookId">urn:uuid:{book_uuid}</dc:identifier>
        <dc:title>{html.escape(meta["title"])}</dc:title>
        <dc:creator>{html.escape(meta["author"])}</dc:creator>
        <dc:publisher>{html.escape(meta["publisher"])}</dc:publisher>
        <dc:language>{meta["language"]}</dc:language>
        <dc:description>{html.escape(meta["description"])}</dc:description>
        <dc:rights>{html.escape(meta["rights"])}</dc:rights>
        <meta property="dcterms:modified">{mod_time}</meta>
    </metadata>
    <manifest>
        {chr(10).join(manifest_items)}
    </manifest>
    <spine toc="ncx">
        {chr(10).join(spine_items)}
    </spine>
</package>
"""
        zf.writestr("OEBPS/content.opf", content_opf)

    return epub_path

def resolve_book_dir(book_slug: str) -> Optional[Path]:
    p = MANUSCRIPT_DIR / book_slug
    if p.exists() and (p / "chapters").exists():
        return p
    for b_dir in list(MANUSCRIPT_DIR.glob(f"*/{book_slug}")) + list(MANUSCRIPT_DIR.glob(f"*/*{book_slug}*")):
        if b_dir.is_dir() and (b_dir / "chapters").exists():
            return b_dir
    for toc in MANUSCRIPT_DIR.glob("*/*/toc.yaml"):
        if book_slug.lower() in toc.parent.name.lower() or book_slug.lower() in toc.read_text(encoding="utf-8").lower():
            return toc.parent
    return None

def export_single_book(book_slug: str, html_only: bool = False, epub_only: bool = False) -> bool:
    book_dir = resolve_book_dir(book_slug)
    if not book_dir:
        print(f"❌ Error: Book folder '{book_slug}' not found in {MANUSCRIPT_DIR}")
        return False

    chapters_dir = book_dir / "chapters"
    chapter_files = sorted(chapters_dir.glob("*.md")) if chapters_dir.exists() else []
    if not chapter_files:
        print(f"❌ Error: No chapter markdown files found in {chapters_dir}")
        return False

    slug_label = f"{book_dir.parent.name}/{book_dir.name}"
    print("\n" + "=" * 70)
    print(f"CONVERGENCE E-BOOK & READER EXPORTER: {slug_label.upper()}")
    print("=" * 70)
    print(f"• Total Chapters: {len(chapter_files)}")

    # Parse all chapters
    chapters_data = []
    total_words = 0
    for f in chapter_files:
        raw_text = f.read_text(encoding="utf-8")
        html_body, title = markdown_to_html_body(raw_text)
        clean_words = len(re.sub(r"<[^>]+>", " ", html_body).split())
        total_words += clean_words
        chapters_data.append({
            "filename": f.name,
            "title": title,
            "html_body": html_body,
            "word_count": clean_words
        })

    print(f"• Total Word Count: {total_words:,} words")
    print("-" * 70)

    # 1. HTML Reader Export
    if not epub_only:
        html_file = generate_html_reader(book_dir.name, chapters_data)
        print(f"📖 HTML Reader Generated: {html_file.relative_to(CONVERGENCE_DIR)}")
        print(f"   Size: {html_file.stat().st_size / 1024:.1f} KB (Self-contained, offline-ready)")

    # 2. EPUB Export
    if not html_only:
        epub_file = generate_epub(book_dir.name, chapters_data)
        print(f"📱 EPUB E-Book Generated: {epub_file.relative_to(CONVERGENCE_DIR)}")
        print(f"   Size: {epub_file.stat().st_size / 1024:.1f} KB (EPUB 3.0 / Apple Books / Kindle compatible)")

    print("=" * 70)
    return True

def main():
    parser = argparse.ArgumentParser(description="Export Convergence novels into Standalone HTML and EPUB")
    parser.add_argument("--book", default="book-01", help="Book slug (default: book-01)")
    parser.add_argument("--all-books", action="store_true", help="Export all detected book manuscripts")
    parser.add_argument("--html-only", action="store_true", help="Generate only standalone HTML reader")
    parser.add_argument("--epub-only", action="store_true", help="Generate only EPUB e-book")
    args = parser.parse_args()

    if args.all_books:
        # Discover all books
        books = [str(ch.parent.relative_to(MANUSCRIPT_DIR)) for ch in sorted(MANUSCRIPT_DIR.glob("*/*/chapters"))]
        print(f"\n📚 Discovered {len(books)} book manuscript(s) for batch export: {', '.join(books)}")
        for b in books:
            export_single_book(b, html_only=args.html_only, epub_only=args.epub_only)
    else:
        export_single_book(args.book, html_only=args.html_only, epub_only=args.epub_only)

if __name__ == "__main__":
    main()
