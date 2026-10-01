"""
CanonForge Exporter: Unified Multi-Level CLI Entrypoint
--------------------------------------------------------------------------------
Exports manuscripts across 3 distinct granularities:
1. Chapter : Web serial platforms (Substack, Patreon, Royal Road, clean MD/HTML)
2. Book    : Standard volumes (EPUB 3.0, HTML Reader, Shunn Manuscript, Clean MD)
3. Series  : Box Set & Omnibus Editions (Single multi-volume EPUB/HTML/MD)
"""

import sys
import re
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

from canonforge.engines.exporter.metadata import resolve_book_dir
from canonforge.engines.exporter.formatter import markdown_to_html_body
from canonforge.engines.exporter.reader_html import generate_html_reader
from canonforge.engines.exporter.epub import generate_epub
from canonforge.engines.exporter.chapter_export import export_chapter_file
from canonforge.engines.exporter.series_export import export_series_omnibus
from canonforge.engines.exporter.shunn import export_shunn_file

def _find_manuscript_dir() -> Path:
    curr = Path.cwd().resolve()
    for cand in [curr, *curr.parents]:
        ms = cand / "manuscript"
        if ms.is_dir():
            return ms
    return curr

def export_single_book(
    book_slug: str,
    output_format: str = "all",
    base_dir: Optional[Path] = None
) -> bool:
    """Export a book to EPUB, HTML, Shunn, or Markdown."""
    ms_dir = base_dir or _find_manuscript_dir()
    book_dir = resolve_book_dir(book_slug, ms_dir)
    if not book_dir:
        print(f"❌ Error: Book folder '{book_slug}' not found under {ms_dir}")
        return False

    chapters_dir = book_dir / "chapters"
    chapter_files = sorted(chapters_dir.glob("*.md")) if chapters_dir.exists() else []
    if not chapter_files:
        print(f"❌ Error: No chapter markdown files found in {chapters_dir}")
        return False

    slug_label = f"{book_dir.parent.name}/{book_dir.name}"
    print("\n" + "=" * 75)
    print(f"CANONFORGE NOVEL EXPORTER: {slug_label.upper()}")
    print("=" * 75)
    print(f"• Total Chapters : {len(chapter_files)}")

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
            "raw_body": raw_text,
            "word_count": clean_words
        })

    print(f"• Word Count     : {total_words:,} words")
    print("-" * 75)

    export_dir = book_dir.parent.parent / "_build" / "export"
    export_dir.mkdir(parents=True, exist_ok=True)
    book_name = book_dir.name

    # 1. HTML Reader
    if output_format in ("html", "all"):
        html_file = generate_html_reader(book_name, chapters_data)
        size_kb = html_file.stat().st_size / 1024
        print(f"  ✓ 📖 Standalone HTML Reader : {html_file.name} ({size_kb:.1f} KB)")

    # 2. EPUB
    if output_format in ("epub", "all"):
        epub_file = generate_epub(book_name, chapters_data)
        size_kb = epub_file.stat().st_size / 1024
        print(f"  ✓ 📱 EPUB 3.0 E-Book        : {epub_file.name} ({size_kb:.1f} KB)")

    # 3. Shunn Manuscript
    if output_format in ("shunn", "all"):
        shunn_path = export_dir / f"{book_name}-shunn.txt"
        export_shunn_file(shunn_path, book_name.replace("-", " ").title(), "Author", chapters_data)
        print(f"  ✓ 📄 Shunn Manuscript       : {shunn_path.name}")

    # 4. Clean Markdown
    if output_format in ("markdown", "all"):
        md_path = export_dir / f"{book_name}.md"
        full_md = f"# {book_name.replace('-', ' ').title()}\n\n" + "\n\n".join([c["raw_body"] for c in chapters_data])
        md_path.write_text(full_md, encoding="utf-8")
        print(f"  ✓ 📝 Monolithic Markdown    : {md_path.name}")

    print("=" * 75 + "\n")
    return True

def handle_chapter_export(args):
    """Handle cf export chapter ..."""
    target = args.target
    p = Path(target)
    if not p.is_file():
        # Search chapter in workspace
        ms_dir = _find_manuscript_dir()
        cands = list(ms_dir.glob(f"**/*{target}*.md"))
        if not cands:
            print(f"❌ Error: Chapter matching '{target}' not found.")
            sys.exit(1)
        p = cands[0]

    res = export_chapter_file(
        chapter_path=p,
        platform=getattr(args, "platform", "clean"),
        output_format=getattr(args, "format", "markdown"),
        author_note=getattr(args, "author_note", None)
    )
    print(f"\n✅ Chapter Exported: {res['title']} ({res['word_count']:,} words, ~{res['reading_time_min']} min read)")
    print(f"   Platform Target : {res['platform'].title()}")
    print(f"   File Generated  : {res['out_file']}\n")

def handle_series_export(args):
    """Handle cf export series ..."""
    series_slug = args.target
    res = export_series_omnibus(
        series_slug=series_slug,
        html_only=(getattr(args, "format", "all") == "html"),
        epub_only=(getattr(args, "format", "all") == "epub")
    )
    print(f"\n🎉 Series Omnibus Generated: {res['omnibus_title']}")
    print(f"   Books Included : {res['total_books']} books ({res['total_chapters']} chapters | {res['total_words']:,} words)")
    if "epub_file" in res:
        print(f"   📱 Omnibus EPUB: {res['epub_file']}")
    if "html_file" in res:
        print(f"   📖 Omnibus HTML: {res['html_file']}")
    print(f"   📝 Omnibus MD  : {res['markdown_file']}\n")

def main():
    parser = argparse.ArgumentParser(description="CanonForge Multi-Level Manuscript Exporter")
    subparsers = parser.add_subparsers(dest="export_type", help="Export target level")

    # Level 1: Chapter
    p_ch = subparsers.add_parser("chapter", help="Export chapter for serialization (Substack, Patreon, Royal Road)")
    p_ch.add_argument("target", help="Chapter filename, slug, or relative path")
    p_ch.add_argument("--platform", choices=["clean", "substack", "patreon", "royalroad"], default="clean", help="Target platform")
    p_ch.add_argument("--format", choices=["markdown", "html"], default="markdown", help="Output format")
    p_ch.add_argument("--author-note", help="Author note to append")
    p_ch.set_defaults(func=handle_chapter_export)

    # Level 2: Book
    p_bk = subparsers.add_parser("book", help="Export full book volume (EPUB, HTML, Shunn, Markdown)")
    p_bk.add_argument("target", nargs="?", default="book-01", help="Book directory or slug")
    p_bk.add_argument("--format", choices=["all", "epub", "html", "shunn", "markdown"], default="all", help="Output format")
    p_bk.set_defaults(func=lambda a: export_single_book(a.target, output_format=a.format))

    # Level 3: Series Omnibus
    p_sr = subparsers.add_parser("series", help="Export entire series as Omnibus / Complete Collection")
    p_sr.add_argument("target", help="Series directory or slug")
    p_sr.add_argument("--format", choices=["all", "epub", "html", "markdown"], default="all", help="Output format")
    p_sr.set_defaults(func=handle_series_export)

    # Top-level fallback / legacy arguments
    parser.add_argument("book_or_legacy", nargs="?", default=None, help="Book slug (legacy usage)")
    parser.add_argument("--all", action="store_true", help="Export all books found in manuscript")
    parser.add_argument("--format", choices=["all", "epub", "html", "shunn", "markdown"], default="all", help="Output format")

    args, unknown = parser.parse_known_args()

    if getattr(args, "func", None):
        args.func(args)
    elif args.all:
        ms = _find_manuscript_dir()
        tocs = sorted(list(ms.glob("*/*/toc.yaml")))
        for toc in tocs:
            export_single_book(str(toc.parent.relative_to(ms)), output_format=args.format, base_dir=ms)
    elif args.book_or_legacy:
        export_single_book(args.book_or_legacy, output_format=args.format)
    else:
        # Default to first discovered book
        ms = _find_manuscript_dir()
        tocs = sorted(list(ms.glob("*/*/toc.yaml")))
        if tocs:
            export_single_book(str(tocs[0].parent.relative_to(ms)), output_format=args.format, base_dir=ms)
        else:
            parser.print_help()

if __name__ == "__main__":
    main()
