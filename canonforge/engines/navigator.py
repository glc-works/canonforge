#!/usr/bin/env python3
"""
canonforge.engines.navigator

Unified Interactive Book & Chapter Navigator Engine.
Provides clean two-step hierarchical resolution:
    1. Select Book (by number 1-N, alias, or menu)
    2. Suggests and selects Chapter (by chapter number, slug, or menu)
100% Free of Universe-Specific Hardcoding.
"""

import sys
import os
import re
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from canonforge.core.manifest import find_universe_root

UNIVERSE_DIR = find_universe_root()
MANUSCRIPT_DIR = UNIVERSE_DIR / "manuscript"


def get_book_registry() -> List[Dict[str, Any]]:
    """Dynamically scan MANUSCRIPT_DIR for series.yaml and toc.yaml to build authoritative registry."""
    registry: List[Dict[str, Any]] = []
    if not MANUSCRIPT_DIR.exists():
        return registry

    counter = 1
    series_dirs = sorted([
        d for d in MANUSCRIPT_DIR.iterdir()
        if d.is_dir() and not d.name.startswith((".", "_", "compiled", "darlings", "exports"))
    ])

    for s_dir in series_dirs:
        series_yaml_path = s_dir / "series.yaml"
        series_meta = {}
        if series_yaml_path.exists() and HAS_YAML:
            try:
                with open(series_yaml_path, encoding="utf-8") as sf:
                    series_meta = yaml.safe_load(sf) or {}
            except Exception:
                pass

        series_title = series_meta.get("display_name", s_dir.name.replace("-", " ").title())
        series_slug = series_meta.get("series_id", s_dir.name)

        book_dirs = sorted([d for d in s_dir.iterdir() if d.is_dir() and (d / "chapters").exists()])
        for b_dir in book_dirs:
            toc_path = b_dir / "toc.yaml"
            toc_meta = {}
            if toc_path.exists() and HAS_YAML:
                try:
                    with open(toc_path, encoding="utf-8") as tf:
                        toc_meta = yaml.safe_load(tf) or {}
                except Exception:
                    pass

            book_title = toc_meta.get("title", b_dir.name.replace("-", " ").title())
            book_id = toc_meta.get("book_id", toc_meta.get("book", f"{s_dir.name}/{b_dir.name}"))

            aliases = [
                str(counter),
                f"b{counter}",
                b_dir.name,
                book_id,
            ]
            for word in re.findall(r"[a-zA-Z0-9]+", book_title.lower()):
                if len(word) >= 4 and word not in ("the", "book", "saga", "series"):
                    aliases.append(word)

            registry.append({
                "num": counter,
                "id": f"{s_dir.name}/{b_dir.name}",
                "title": book_title,
                "series": series_title,
                "series_id": series_slug,
                "book_id": book_id,
                "universe": UNIVERSE_DIR.name,
                "aliases": sorted(list(set(aliases)))
            })
            counter += 1

    return registry


def list_books() -> List[Dict[str, Any]]:
    """Return all books enriched with current on-disk chapter counts."""
    registry = get_book_registry()
    enriched = []
    for b in registry:
        b_copy = dict(b)
        b_dir = MANUSCRIPT_DIR / b["id"]
        chaps_dir = b_dir / "chapters"
        written_count = 0
        if chaps_dir.exists():
            written_count = len(list(chaps_dir.glob("*.md")))
        b_copy["written_chapters"] = written_count
        b_copy["dir"] = b_dir
        enriched.append(b_copy)
    return enriched


def resolve_book(query: str) -> Optional[Dict[str, Any]]:
    """Match query to a book by number, alias, id slug, or title substring."""
    q = str(query).strip().lower()
    books = list_books()

    # Exact alias match
    for b in books:
        if q == str(b["num"]) or q in b["aliases"] or q == b["id"].lower():
            return b

    # Substring match on id or title
    for b in books:
        if q in b["id"].lower() or q in b["title"].lower():
            return b

    return None


def get_book_chapters(book: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Retrieve ordered list of chapters for a given book via toc.yaml or directory scan."""
    b_dir = MANUSCRIPT_DIR / book["id"]
    chaps_dir = b_dir / "chapters"
    toc_file = b_dir / "toc.yaml"
    chapters = []

    if toc_file.exists():
        try:
            raw_toc = toc_file.read_text(encoding="utf-8")
            if HAS_YAML:
                toc = yaml.safe_load(raw_toc) or {}
            else:
                toc = {"acts": [{"title": "Manifest", "chapters": re.findall(r"-\s*([a-zA-Z0-9_\-]+\.md)", raw_toc)}]}
            ch_num = 1
            for act in toc.get("acts", []):
                act_title = act.get("title", f"Act {act.get('act', 1)}")
                for ch_entry in act.get("chapters", []):
                    ch_filename = ch_entry if isinstance(ch_entry, str) else ch_entry.get("file", "")
                    ch_path = chaps_dir / ch_filename
                    exists = ch_path.exists()
                    title = ch_filename.replace(".md", "").replace("-", " ").title()
                    word_count = 0

                    if exists:
                        txt = ch_path.read_text(encoding="utf-8")
                        fm = re.match(r"^---\s*\n(.*?)\n---\s*\n", txt, re.DOTALL)
                        if fm:
                            if HAS_YAML:
                                try:
                                    meta = yaml.safe_load(fm.group(1)) or {}
                                    title = meta.get("title", title)
                                except Exception:
                                    pass
                            else:
                                t_m = re.search(r'title:\s*["\']?(.*?)["\']?\s*$', fm.group(1), re.MULTILINE)
                                if t_m:
                                    title = t_m.group(1).strip()
                            body = txt[fm.end():]
                        else:
                            body = txt
                        word_count = len(re.findall(r"\b\w+\b", body))

                    chapters.append({
                        "num": ch_num,
                        "filename": ch_filename,
                        "path": ch_path,
                        "exists": exists,
                        "title": title,
                        "act_title": act_title,
                        "words": word_count
                    })
                    ch_num += 1
            if chapters:
                return chapters
        except Exception:
            pass

    # Fallback to scanning chapters/ directly
    if chaps_dir.exists():
        ch_files = sorted(chaps_dir.glob("*.md"))
        for idx, cf in enumerate(ch_files, 1):
            txt = cf.read_text(encoding="utf-8")
            title = cf.stem.replace("-", " ").title()
            fm = re.match(r"^---\s*\n(.*?)\n---\s*\n", txt, re.DOTALL)
            if fm:
                try:
                    meta = yaml.safe_load(fm.group(1)) or {}
                    title = meta.get("title", title)
                except Exception:
                    pass
                body = txt[fm.end():]
            else:
                body = txt
            words = len(re.findall(r"\b\w+\b", body))
            chapters.append({
                "num": idx,
                "filename": cf.name,
                "path": cf,
                "exists": True,
                "title": title,
                "act_title": "",
                "words": words
            })

    return chapters


def get_git_active_chapter() -> Optional[Path]:
    """Check git status for a currently modified chapter in manuscript/."""
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain", "manuscript/"],
            cwd=str(UNIVERSE_DIR),
            capture_output=True,
            text=True
        )
        for line in res.stdout.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2:
                p = UNIVERSE_DIR / parts[-1]
                if p.suffix == ".md" and "chapters" in str(p) and p.exists():
                    return p
    except Exception:
        pass
    return None


def print_book_menu():
    """Render list of available books in terminal."""
    books = list_books()
    print("\n" + "=" * 65)
    print(f"  📚 SELECT BOOK ({UNIVERSE_DIR.name.upper()}):")
    print("=" * 65)
    for b in books:
        ch_info = f"{b['written_chapters']} chapters written"
        print(f"  [{b['num']}] {b['title']:<38} ({ch_info})")
    print("=" * 65)


def print_chapter_suggestions(book: Dict[str, Any], chapters: List[Dict[str, Any]]):
    """Render list of chapters with suggestion markers for a given book."""
    print("\n" + "=" * 65)
    print(f"  📖 CHAPTER DIRECTORY: {book['title'].upper()}")
    print("=" * 65)
    for ch in chapters:
        if ch["exists"]:
            status_str = f"🟢 {ch['words']:,} words"
        else:
            status_str = "⚪ [Planned]"
        print(f"  [{ch['num']:>2}] Ch {ch['num']:02d}: {ch['title']:<36} {status_str}")
    print("=" * 65)


def resolve_interactive_or_cli(
    target_1: Optional[str] = None,
    target_2: Optional[str] = None,
    allow_interactive: bool = True
) -> Optional[Tuple[Dict[str, Any], Path]]:
    """Master resolution logic for book + chapter targeting."""
    # 1. Direct file path
    if target_1:
        p1 = Path(target_1)
        if p1.exists() and p1.is_file():
            for b in list_books():
                if b["id"] in str(p1):
                    return b, p1
            books = list_books()
            return books[0] if books else {"title": "Book", "id": "b1"}, p1

        p_conv = UNIVERSE_DIR / target_1
        if p_conv.exists() and p_conv.is_file():
            for b in list_books():
                if b["id"] in str(p_conv):
                    return b, p_conv
            books = list_books()
            return books[0] if books else {"title": "Book", "id": "b1"}, p_conv

    # 2. Check if target_1 is a Book
    book = resolve_book(target_1) if target_1 else None

    if not book:
        # Check standalone chapter query
        if target_1:
            q_clean = target_1.lower().replace(".md", "").strip()
            all_mds = list(MANUSCRIPT_DIR.rglob("*.md"))
            chaps = [f for f in all_mds if not f.name.startswith(("compiled", ".", "_"))]
            exact = [f for f in chaps if f.stem.lower() == q_clean or f.name.lower() == q_clean]
            if exact:
                for b in list_books():
                    if b["id"] in str(exact[0]):
                        return b, exact[0]
                books = list_books()
                return books[0] if books else {"title": "Book", "id": "b1"}, exact[0]

        # Check git active chapter
        git_active = get_git_active_chapter()
        if git_active and not target_1:
            for b in list_books():
                if b["id"] in str(git_active):
                    return b, git_active
            books = list_books()
            return books[0] if books else {"title": "Book", "id": "b1"}, git_active

        is_test = "unittest" in sys.modules or "pytest" in sys.modules
        if allow_interactive and sys.stdin.isatty() and not is_test:
            print_book_menu()
            choice = input("Select Book [1-N] or name/alias > ").strip()
            if not choice:
                return None
            book = resolve_book(choice)
            if not book:
                print(f"❌ Book selection '{choice}' unrecognized.")
                return None
        else:
            all_mds = list(MANUSCRIPT_DIR.rglob("*.md"))
            chaps = [f for f in all_mds if not f.name.startswith(("compiled", ".", "_"))]
            if chaps:
                chaps.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                for b in list_books():
                    if b["id"] in str(chaps[0]):
                        return b, chaps[0]
                books = list_books()
                return books[0] if books else {"title": "Book", "id": "b1"}, chaps[0]
            return None

    chapters = get_book_chapters(book)
    if not chapters:
        print(f"❌ No registered chapters in book: {book['title']}")
        return None

    # 3. target_2 provided
    if target_2:
        t2_str = str(target_2).strip().lower()
        if t2_str.isdigit():
            c_num = int(t2_str)
            for ch in chapters:
                if ch["num"] == c_num:
                    return book, ch["path"]
        for ch in chapters:
            if t2_str in ch["filename"].lower() or t2_str in ch["title"].lower():
                return book, ch["path"]

    # 4. Display chapter suggestions
    print_chapter_suggestions(book, chapters)

    is_test = "unittest" in sys.modules or "pytest" in sys.modules
    if allow_interactive and sys.stdin.isatty() and not is_test:
        ch_choice = input(f"Select chapter [1-{len(chapters)}] (Enter for latest) > ").strip()
        if not ch_choice:
            existing = [c for c in chapters if c["exists"]]
            return book, existing[-1]["path"] if existing else book, chapters[0]["path"]
        if ch_choice.isdigit():
            c_num = int(ch_choice)
            for ch in chapters:
                if ch["num"] == c_num:
                    return book, ch["path"]
        for ch in chapters:
            if ch_choice.lower() in ch["filename"].lower() or ch_choice.lower() in ch["title"].lower():
                return book, ch["path"]
        print(f"❌ Chapter selection '{ch_choice}' not found.")
        return None
    else:
        existing = [c for c in chapters if c["exists"]]
        return book, existing[-1]["path"] if existing else book, chapters[0]["path"]


def main():
    """CLI runner for navigator."""
    args = sys.argv[1:]
    arg1 = args[0] if len(args) > 0 else None
    arg2 = args[1] if len(args) > 1 else None

    result = resolve_interactive_or_cli(arg1, arg2, allow_interactive=True)
    if result:
        book, chapter_path = result
        print(f"\n✅ Selected: Book '{book['title']}' -> {chapter_path.name}")
        print(f"   Path: {chapter_path}")


if __name__ == "__main__":
    main()
