"""
CanonForge Exporter: Series Omnibus / Box Set Exporter
--------------------------------------------------------------------------------
Compiles an entire multi-book series into a unified Omnibus Edition:
  - Monolithic Series Markdown
  - Series Standalone HTML Reader
  - Series Omnibus EPUB 3.0 with multi-volume table of contents.
"""

import re
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from canonforge.engines.exporter.formatter import markdown_to_html_body
from canonforge.engines.exporter.reader_html import generate_html_reader
from canonforge.engines.exporter.epub import generate_epub

def resolve_series_dir(series_arg: str, base_dir: Optional[Path] = None) -> Optional[Path]:
    """Find series directory containing series.yaml."""
    curr = base_dir or Path.cwd()
    # Check current or parent manuscript directories
    cand_dirs = [curr, curr / "manuscript", *curr.parents]
    for c in cand_dirs:
        ms = c / "manuscript" if (c / "manuscript").is_dir() else c
        target = ms / series_arg
        if target.is_dir() and (target / "series.yaml").is_file():
            return target
        # Check subdirectories
        if ms.is_dir():
            for sub in ms.iterdir():
                if sub.is_dir() and (sub / "series.yaml").is_file():
                    if sub.name.lower() == series_arg.lower():
                        return sub
    return None

def export_series_omnibus(
    series_slug: str,
    base_dir: Optional[Path] = None,
    html_only: bool = False,
    epub_only: bool = False
) -> Dict[str, Any]:
    """Compile and export all books in a series into a single Omnibus edition."""
    s_dir = resolve_series_dir(series_slug, base_dir)
    if not s_dir:
        raise FileNotFoundError(f"Series directory for '{series_slug}' not found.")

    s_manifest_path = s_dir / "series.yaml"
    s_meta: Dict[str, Any] = {}
    if HAS_YAML:
        try:
            s_meta = yaml.safe_load(s_manifest_path.read_text(encoding="utf-8")) or {}
        except Exception:
            pass

    series_title = s_meta.get("title", s_dir.name.replace("-", " ").title())
    omnibus_title = f"{series_title}: The Complete Collection"

    # Discover books in order
    books_meta = s_meta.get("books", [])
    book_dirs: List[Path] = []
    if books_meta:
        for b_entry in books_meta:
            b_sub = b_entry.get("directory") or b_entry.get("id") or b_entry.get("slug")
            if b_sub and (s_dir / b_sub).is_dir():
                book_dirs.append(s_dir / b_sub)
    if not book_dirs:
        # Fallback to discovering subdirectories with toc.yaml
        for sub in sorted(s_dir.iterdir()):
            if sub.is_dir() and (sub / "toc.yaml").is_file():
                book_dirs.append(sub)

    if not book_dirs:
        raise ValueError(f"No books with toc.yaml found under series '{series_slug}'.")

    # Aggregate chapters across all books
    omnibus_chapters = []
    omnibus_markdown_parts = [f"# {omnibus_title}\n\n"]
    total_words = 0
    total_chapters = 0

    for book_idx, b_dir in enumerate(book_dirs, 1):
        b_toc_path = b_dir / "toc.yaml"
        b_title = f"Book {book_idx}: {b_dir.name.replace('-', ' ').title()}"
        if b_toc_path.is_file() and HAS_YAML:
            try:
                toc_data = yaml.safe_load(b_toc_path.read_text(encoding="utf-8")) or {}
                b_info = toc_data.get("book", {})
                b_title = b_info.get("title", b_title)
            except Exception:
                pass

        # Book divider page
        divider_html = f'<div class="book-divider"><h1>{b_title}</h1></div>'
        omnibus_chapters.append({
            "filename": f"book-{book_idx:02d}-divider.html",
            "title": b_title,
            "html_body": divider_html,
            "word_count": 0
        })
        omnibus_markdown_parts.append(f"\n\n---\n\n# {b_title}\n\n---\n\n")

        # Collect chapters
        ch_files = sorted(list((b_dir / "chapters").glob("*.md")))
        for ch_file in ch_files:
            raw_text = ch_file.read_text(encoding="utf-8")
            html_body, ch_title = markdown_to_html_body(raw_text)
            words = len(re.sub(r"<[^>]+>", " ", html_body).split())
            total_words += words
            total_chapters += 1

            full_ch_title = f"{b_title} - {ch_title}"
            omnibus_chapters.append({
                "filename": f"{b_dir.name}_{ch_file.name}",
                "title": full_ch_title,
                "html_body": html_body,
                "word_count": words
            })
            omnibus_markdown_parts.append(f"\n\n## {ch_title}\n\n{raw_text}")

    # Build export target
    export_dir = s_dir.parent.parent / "_build" / "export" / "series"
    export_dir.mkdir(parents=True, exist_ok=True)

    omnibus_slug = f"{s_dir.name}-omnibus"
    md_file = export_dir / f"{omnibus_slug}.md"
    md_file.write_text("".join(omnibus_markdown_parts), encoding="utf-8")

    result = {
        "series_title": series_title,
        "omnibus_title": omnibus_title,
        "total_books": len(book_dirs),
        "total_chapters": total_chapters,
        "total_words": total_words,
        "markdown_file": md_file
    }

    if not epub_only:
        html_file = generate_html_reader(omnibus_slug, omnibus_chapters)
        result["html_file"] = html_file

    if not html_only:
        epub_file = generate_epub(omnibus_slug, omnibus_chapters)
        result["epub_file"] = epub_file

    return result
