"""
CLI entrypoint for prose metrics analysis.
"""
import sys
import argparse
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent
MANUSCRIPT_DIR = PACKAGE_ROOT / "manuscript"

from canonforge.engines.metrics.cache import clear_metrics_cache
from canonforge.engines.metrics.calculator import get_chapter_metrics
from canonforge.engines.metrics.reporter import (
    print_chapter_dossier, print_book_summary, find_target_file
)

def main():
    parser = argparse.ArgumentParser(description="CanonForge Chapter Metrics & Content Counter Engine")
    parser.add_argument("target", nargs="?", help="Chapter path, filename, or book slug")
    parser.add_argument("--book", "-b", help="Audit all chapters in specified book slug")
    parser.add_argument("--all", "-a", action="store_true", help="Audit all chapters across all 4 books")
    parser.add_argument("--clear-cache", action="store_true", help="Clear SQLite cache table")
    parser.add_argument("--refresh", "-r", action="store_true", help="Force refresh metrics without cache")
    parser.add_argument("--json", action="store_true", help="Output raw JSON metrics")
    
    args = parser.parse_args()
    
    if args.clear_cache:
        clear_metrics_cache()
        return

    if args.all:
        md_files = [
            f for f in MANUSCRIPT_DIR.rglob("*.md")
            if not f.name.startswith((".", "MASTER-", "README")) and "_build" not in f.parts and "compiled" not in f.parts and "exports" not in f.parts and "darlings" not in f.parts
        ]
        print_book_summary("All Saga Books (Full Saga)", md_files)
        return

    if args.book:
        target_dir = MANUSCRIPT_DIR / args.book
        if not target_dir.exists():
            candidates = list(MANUSCRIPT_DIR.glob(f"*/{args.book}")) + [
                d for d in MANUSCRIPT_DIR.glob("*/*") if d.is_dir() and args.book in d.name
            ]
            if candidates:
                target_dir = candidates[0]
            else:
                for toc in MANUSCRIPT_DIR.glob("*/*/toc.yaml"):
                    if args.book.lower() in toc.read_text(encoding="utf-8").lower():
                        target_dir = toc.parent
                        break
                else:
                    print(f"❌ Book folder not found: {args.book}")
                    return
        files = [
            f for f in target_dir.rglob("*.md")
            if not f.name.startswith((".", "MASTER-", "README")) and "_build" not in f.parts and "compiled" not in f.parts and "exports" not in f.parts and "darlings" not in f.parts
        ]
        print_book_summary(target_dir.name, files)
        return

    if not args.target:
        print("\n" + "=" * 70)
        print("  CANONFORGE CHAPTER METRICS & CONTENT COUNTER ENGINE")
        print("=" * 70)
        print("Usage:")
        print("  ./ax stats <chapter_path_or_name>   : Audit single chapter file")
        print("  ./ax stats --book the-stone-child   : Audit entire Book 1")
        print("  ./ax stats --book the-sun-sanctum-champion : Audit entire Book 4")
        print("  ./ax stats --all                    : Audit all manuscript books")
        print("  ./ax stats --clear-cache            : Invalidate SQLite cache")
        print("=" * 70 + "\n")
        return

    # Check if target is a book directory
    book_candidate = MANUSCRIPT_DIR / args.target
    if book_candidate.exists() and book_candidate.is_dir():
        files = [f for f in book_candidate.rglob("*.md") if not f.name.startswith(".") and "compiled" not in f.parts]
        print_book_summary(book_candidate.name, files)
        return

    target_file = find_target_file(args.target)
    if not target_file:
        print(f"❌ Chapter file not found matching '{args.target}'")
        return

    metrics = get_chapter_metrics(target_file, force_refresh=args.refresh)
    if args.json:
        print(json.dumps(metrics, indent=2))
    else:
        print_chapter_dossier(metrics)


if __name__ == "__main__":
    main()
