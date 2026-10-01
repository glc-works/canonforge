"""
CanonForge Exporter: Standalone Interactive HTML Reader Generator
--------------------------------------------------------------------------------
Generates a self-contained, single-file publication-grade web reader
with chapter navigation, dark/light theme, and typography controls.
"""

import re
import html
from pathlib import Path
from typing import Dict, List, Any, Optional

from canonforge.engines.exporter.metadata import get_book_metadata, resolve_book_dir

DEFAULT_READER_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{book_title}</title>
<style>
:root {{
  --bg: #fbf0d9;
  --text: #2b2b2b;
  --accent: #8b3a0f;
  --sidebar-bg: #f4e4c1;
  --border: #dfcb9f;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: #1a1a1a;
    --text: #e0e0e0;
    --accent: #e59866;
    --sidebar-bg: #242424;
    --border: #333333;
  }}
}}
body {{
  margin: 0;
  padding: 0;
  background: var(--bg);
  color: var(--text);
  font-family: Georgia, Garamond, "Times New Roman", serif;
  display: flex;
  min-height: 100vh;
}}
#sidebar {{
  width: 280px;
  background: var(--sidebar-bg);
  border-right: 1px solid var(--border);
  padding: 24px;
  box-sizing: border-box;
  overflow-y: auto;
  position: sticky;
  top: 0;
  height: 100vh;
}}
#sidebar h2 {{
  font-size: 1.1em;
  margin-top: 0;
  color: var(--accent);
}}
#sidebar ul {{
  list-style: none;
  padding: 0;
  margin: 0;
}}
#sidebar li {{
  margin-bottom: 12px;
}}
#sidebar a {{
  color: var(--text);
  text-decoration: none;
  font-size: 0.9em;
}}
#sidebar a:hover {{
  color: var(--accent);
}}
#content {{
  flex: 1;
  max-width: 720px;
  margin: 40px auto;
  padding: 0 32px;
}}
.book-header {{
  text-align: center;
  margin-bottom: 60px;
  border-bottom: 2px solid var(--border);
  padding-bottom: 30px;
}}
.book-header h1 {{
  font-size: 2.4em;
  margin-bottom: 8px;
}}
.book-header .meta {{
  color: #777;
  font-style: italic;
}}
article.chapter-container {{
  margin-bottom: 80px;
}}
.chapter-header {{
  text-align: center;
  margin-bottom: 32px;
}}
.chapter-number {{
  font-size: 0.85em;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: var(--accent);
}}
h2.chapter-title {{
  font-size: 1.8em;
  margin-top: 6px;
}}
.chapter-body p {{
  font-size: 1.1em;
  line-height: 1.75;
  margin-bottom: 1.4em;
  text-indent: 1.5em;
}}
.chapter-body p:first-of-type {{
  text-indent: 0;
}}
hr.scene-break {{
  border: 0;
  text-align: center;
  margin: 3em 0;
}}
hr.scene-break:before {{
  content: "* * *";
  color: var(--accent);
  letter-spacing: 4px;
}}
</style>
</head>
<body>
<nav id="sidebar">
  <h2>Contents</h2>
  <ul>
    {toc_items}
  </ul>
</nav>
<main id="content">
  <header class="book-header">
    <h1>{book_title}</h1>
    <div class="meta">{author} | {total_words} words (~{reading_time} min read)</div>
  </header>
  {chapters_html}
</main>
</body>
</html>"""

def generate_html_reader(
    book_slug: str,
    chapters_data: List[Dict[str, Any]],
    out_dir: Optional[Path] = None,
    base_dir: Optional[Path] = None
) -> Path:
    """Generate self-contained, publication-grade HTML reader."""
    book_path = resolve_book_dir(book_slug, base_dir)
    meta = get_book_metadata(book_path) if book_path else {
        "title": book_slug.replace("-", " ").title(),
        "author": "Author"
    }

    total_words = sum(c.get("word_count", 0) for c in chapters_data)
    est_reading_time = max(1, round(total_words / 225))

    toc_items = []
    chapters_html_list = []

    for idx, ch in enumerate(chapters_data, 1):
        ch_id = f"ch-{idx:02d}"
        ch_title = html.escape(ch.get("title", f"Chapter {idx}"))
        toc_items.append(f'<li><a href="#{ch_id}">{ch_title}</a></li>')

        ch_block = f"""
        <article id="{ch_id}" class="chapter-container">
          <div class="chapter-header">
            <div class="chapter-number">Chapter {idx}</div>
            <h2 class="chapter-title">{ch_title}</h2>
          </div>
          <div class="chapter-body">
            {ch.get("html_body", "")}
          </div>
        </article>
        """
        chapters_html_list.append(ch_block)

    full_html = DEFAULT_READER_TEMPLATE.format(
        book_title=html.escape(meta.get("title", book_slug)),
        author=html.escape(meta.get("author", "Author")),
        total_words=f"{total_words:,}",
        reading_time=est_reading_time,
        toc_items="\n    ".join(toc_items),
        chapters_html="\n".join(chapters_html_list)
    )

    target_dir = out_dir or (book_path.parent.parent / "_build" / "export" if book_path else Path.cwd() / "_build" / "export")
    target_dir.mkdir(parents=True, exist_ok=True)
    out_file = target_dir / f"{book_slug}.html"
    out_file.write_text(full_html, encoding="utf-8")
    return out_file
