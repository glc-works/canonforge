"""
CLI entrypoint for manuscript compilation.
"""
import sys
import re
import argparse
from pathlib import Path
from typing import Optional

from canonforge.engines.compiler.assembler import (
    load_from_manifest, discover_chapters_fallback, compile_manuscript, resolve_book_dir,
    MANUSCRIPT_DIR, COMPILED_DIR
)
from canonforge.engines.compiler.analytics import generate_analytics_report
from canonforge.engines.compiler.epub import build_epub

def process_book(book_target: str, output_override: Optional[str] = None, export_epub: bool = False):
    book_dir = resolve_book_dir(book_target)
    if not book_dir or not book_dir.exists():
        print(f"Error: Book '{book_target}' not found in {MANUSCRIPT_DIR}.", file=sys.stderr)
        return False

    manifest_data = load_from_manifest(book_dir)
    if manifest_data:
        chapters = manifest_data["chapters"]
        manifest = manifest_data["manifest"]
    else:
        chapters = discover_chapters_fallback(book_dir)
        manifest = None

    if not chapters:
        print(f"No chapters found in {book_dir}.")
        return False

    # Determine canonical export slug from manifest or directory
    export_slug = book_dir.name
    if manifest:
        export_slug = manifest.get("book_id") or manifest.get("book") or manifest.get("slug")
        if not export_slug and "title" in manifest:
            export_slug = re.sub(r"[^a-zA-Z0-9]+", "-", manifest["title"]).strip("-").lower()
    if not export_slug:
        export_slug = f"{book_dir.parent.name}-{book_dir.name}"

    out_path = Path(output_override) if output_override else COMPILED_DIR / f"{export_slug}.md"
    compile_manuscript(chapters, manifest, export_slug, out_path)
    generate_analytics_report(chapters, export_slug)

    if export_epub:
        epub_path = COMPILED_DIR / f"{export_slug}.epub"
        build_epub(chapters, manifest, export_slug, epub_path)

    return True

def main():
    parser = argparse.ArgumentParser(description="CanonForge Novel Manuscript Compiler")
    parser.add_argument("--book", default="stone-child/book-01", help="Book identifier, path, or number")
    parser.add_argument("--output", help="Custom output path for compiled markdown")
    parser.add_argument("--all", action="store_true", help="Compile all books found in manuscript/")
    parser.add_argument("--epub", action="store_true", help="Generate KDP-compliant EPUB 3 e-book")

    args = parser.parse_args()

    if args.all:
        books_found = []
        for toc in sorted(MANUSCRIPT_DIR.glob("*/*/toc.yaml")):
            books_found.append(toc.parent)
        for b_dir in books_found:
            process_book(str(b_dir.relative_to(MANUSCRIPT_DIR)), export_epub=args.epub)
    else:
        process_book(args.book, args.output, export_epub=args.epub)

if __name__ == "__main__":
    main()

