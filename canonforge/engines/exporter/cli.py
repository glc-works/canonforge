"""
CLI entrypoint for standalone HTML & EPUB export.
"""
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any

from canonforge.engines.exporter.metadata import get_book_metadata, resolve_book_dir
from canonforge.engines.exporter.formatter import markdown_to_html_body
from canonforge.engines.exporter.reader_html import generate_html_reader
from canonforge.engines.exporter.epub import generate_epub

PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent
MANUSCRIPT_DIR = PACKAGE_ROOT / "manuscript"

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
    print(f"CANONFORGE E-BOOK & READER EXPORTER: {slug_label.upper()}")
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
    parser = argparse.ArgumentParser(description="Export CanonForge novels into Standalone HTML and EPUB")
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
