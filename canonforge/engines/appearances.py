#!/usr/bin/env python3
"""
CANONFORGE ENGINE: MANUSCRIPT APPEARANCE & CITATION INDEXER
--------------------------------------------------------------------------------
Scans manuscript chapters to build authoritative chapter-by-chapter citations
distinguishing active scene presence from passing references:
- "Appears in": Character holds POV, speaks dialogue, or is present in scene.
- "Mentioned in": Character is referenced or recalled in prose/dialogue without being present.

Zero Creative IP Contamination: Discovers characters and manuscript dynamically.
--------------------------------------------------------------------------------
"""

import sys
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from canonforge.core.manifest import find_universe_root


def parse_chapter_metadata(file_path: Path) -> Tuple[Dict[str, Any], str]:
    """Extract frontmatter and text from a chapter markdown file."""
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    fm: Dict[str, Any] = {}
    body = text
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if match:
        body = text[match.end():]
        raw_yaml = match.group(1)
        if HAS_YAML:
            try:
                parsed = yaml.safe_load(raw_yaml)
                if isinstance(parsed, dict):
                    fm = parsed
            except Exception:
                pass
        if not fm:
            for line in raw_yaml.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm, body


def scan_character_appearances(
    character_name: str,
    universe_dir: Path,
    aliases: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Scan all manuscript chapters and categorize into Appears vs Mentioned."""
    manuscript_dir = universe_dir / "manuscript"
    if not manuscript_dir.exists():
        return {"character": character_name, "appears_in": [], "mentioned_in": []}

    all_chapters = sorted([
        p for p in manuscript_dir.glob("**/*.md")
        if not p.name.startswith(("_", "."))
        and p.parent.name not in ("compiled", "_build", "dist")
        and not p.stem.startswith(("series", "README", "readme", "MASTER", "master", "SUMMARY", "summary", "TOC", "toc"))
    ])

    search_terms = [character_name.strip()]
    if aliases:
        for a in aliases:
            if isinstance(a, str) and len(a.strip()) >= 3:
                search_terms.append(a.strip())

    # Extract single-word first name if >= 4 chars
    first_name = character_name.split()[0].strip(",.")
    if len(first_name) >= 4 and first_name.lower() not in ("elder", "brother", "sister", "mother", "father", "lord", "lady", "commander", "inquisitor"):
        if first_name not in search_terms:
            search_terms.append(first_name)

    appears_in: List[Dict[str, Any]] = []
    mentioned_in: List[Dict[str, Any]] = []

    for ch_path in all_chapters:
        fm, body = parse_chapter_metadata(ch_path)
        book_slug = ch_path.parent.parent.name if ch_path.parent.name in ("chapters", "act-1", "act-2", "act-3", "act-4") else ch_path.parent.name
        ch_title = fm.get("title", ch_path.stem.replace("-", " ").title())
        ch_num = fm.get("chapter", "")

        # 1. Check if explicitly in frontmatter characters list or POV
        declared_chars = [str(c).lower() for c in fm.get("characters", [])]
        pov = str(fm.get("pov", "")).lower()

        is_declared_present = False
        for term in search_terms:
            term_lower = term.lower()
            if term_lower in pov or any(term_lower in dc for dc in declared_chars):
                is_declared_present = True
                break

        # 2. Check occurrences in text body
        body_lower = body.lower()
        found_in_body = any(re.search(rf"\b{re.escape(term.lower())}\b", body_lower) for term in search_terms)

        if not found_in_body and not is_declared_present:
            continue

        chapter_info = {
            "book": book_slug,
            "chapter": ch_num,
            "title": ch_title,
            "file": ch_path.name,
            "path": str(ch_path.relative_to(universe_dir)),
        }

        # Check dialogue barks or speaking patterns
        dialogue_pattern = False
        for term in search_terms:
            # e.g., 'said Kira', 'Kira whispered', '"...," Kira'
            if re.search(rf'(said|muttered|whispered|screamed|demanded|asked|answered|nodded)\s+{re.escape(term)}', body, re.IGNORECASE) or \
               re.search(rf'{re.escape(term)}\s+(said|muttered|whispered|screamed|demanded|asked|answered|nodded)', body, re.IGNORECASE):
                dialogue_pattern = True
                break

        if is_declared_present or dialogue_pattern or pov in [t.lower() for t in search_terms]:
            appears_in.append(chapter_info)
        else:
            mentioned_in.append(chapter_info)

    return {
        "character": character_name,
        "appears_in": appears_in,
        "mentioned_in": mentioned_in,
        "total_appearances": len(appears_in),
        "total_mentions": len(mentioned_in),
    }


def print_appearances_report(data: Dict[str, Any]):
    """Format and print appearance citation index."""
    char = data["character"]
    appears = data["appears_in"]
    mentioned = data["mentioned_in"]

    print("=" * 75)
    print(f"📖 CHAPTER CITATION INDEX: {char.upper()}")
    print(f"   Physical Presence: {len(appears)} chapters | Passing Mentions: {len(mentioned)} chapters")
    print("=" * 75)

    print("\n🟢 ACTIVE PRESENCE ('Appears in'):")
    if appears:
        by_book: Dict[str, List[Dict[str, Any]]] = {}
        for a in appears:
            by_book.setdefault(a["book"], []).append(a)

        for b, chs in by_book.items():
            print(f"  • {b.upper()}:")
            for c in chs:
                ch_tag = f"Ch {c['chapter']}: " if c.get('chapter') else ""
                print(f"    - {ch_tag}{c['title']} ({c['file']})")
    else:
        print("  (No direct on-page appearances recorded)")

    print("\n⚪ REFERENCED IN CONVERSATION / MEMORY ('Mentioned in'):")
    if mentioned:
        by_book_m: Dict[str, List[Dict[str, Any]]] = {}
        for m in mentioned:
            by_book_m.setdefault(m["book"], []).append(m)

        for b, chs in by_book_m.items():
            print(f"  • {b.upper()}:")
            for c in chs:
                ch_tag = f"Ch {c['chapter']}: " if c.get('chapter') else ""
                print(f"    - {ch_tag}{c['title']} ({c['file']})")
    else:
        print("  (No passing mentions in absence recorded)")

    print("=" * 75 + "\n")


def main():
    parser = argparse.ArgumentParser(description="CanonForge Manuscript Appearance & Citation Indexer")
    parser.add_argument("character", nargs="?", help="Target character name")
    parser.add_argument("--json", action="store_true", help="Output raw JSON citations")
    args = parser.parse_args()

    if not args.character:
        print("\nUsage: cf appearances <character_name> [--json]\n")
        return

    u_root = find_universe_root()
    res = scan_character_appearances(args.character, u_root)

    if args.json:
        print(json.dumps(res, indent=2))
    else:
        print_appearances_report(res)


if __name__ == "__main__":
    main()
