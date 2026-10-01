"""
canonforge/engines/linker.py

Authoritative Semantic Entity Linker for CanonForge Studio.
Enriches manuscript chapters with Obsidian Wikilinks [[Entity-Slug|Display Name]]
connecting characters, factions, locations, bestiary, and relics to wiki dossiers.
Idempotent, non-destructive, and strictly 100% free of universe hardcoding.
"""

import sys
import os
import re
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional

def find_universe_root(start_dir: Optional[Path] = None) -> Path:
    cwd = (start_dir or Path.cwd()).resolve()
    for parent in [cwd, *cwd.parents]:
        if (parent / "universe.yaml").is_file():
            return parent
    return cwd

def get_linkable_entities(wiki_dir: Path) -> List[Tuple[str, str, str]]:
    """
    Retrieve all linkable entities across wiki folders.
    Returns sorted list of (search_pattern, slug, display_name).
    Longer multi-word phrases appear first to avoid partial-matching substrings.
    """
    if not wiki_dir.is_dir():
        return []

    entities = []
    seen_patterns = set()

    for f in wiki_dir.rglob("*.md"):
        if f.name.lower() in ("readme.md", "index.md", "summary.md"):
            continue

        slug = f.stem
        title = f.stem.replace("-", " ")
        aliases = [title]

        # Extract title and aliases from frontmatter
        try:
            content = f.read_text(encoding="utf-8")
            m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if m:
                for line in m.group(1).splitlines():
                    if ":" in line and not line.strip().startswith("#"):
                        k, v = line.split(":", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k in ("name", "title") and v:
                            title = v
                            aliases.append(v)
                        elif k in ("aliases", "labels"):
                            for item in v.split(","):
                                cleaned = item.strip().lstrip("-").strip()
                                if cleaned and len(cleaned) >= 3:
                                    aliases.append(cleaned)
        except Exception:
            pass

        for alias in set(aliases):
            alias_clean = alias.strip()
            if len(alias_clean) >= 3 and alias_clean.lower() not in seen_patterns:
                seen_patterns.add(alias_clean.lower())
                entities.append((alias_clean, slug, title))

    # Sort descending by pattern length so longer phrases match before shorter tokens
    entities.sort(key=lambda x: len(x[0]), reverse=True)
    return entities

def link_chapter_text(text: str, entities: List[Tuple[str, str, str]]) -> Tuple[str, int]:
    """
    Idempotently link first occurrence of entities in prose.
    Preserves frontmatter, code blocks, and existing wikilinks.
    """
    # Separate frontmatter
    fm_match = re.match(r"^(---[\r\n]+.*?[\r\n]+---[\r\n]+)(.*)$", text, re.DOTALL)
    if fm_match:
        frontmatter, body = fm_match.group(1), fm_match.group(2)
    else:
        frontmatter, body = "", text

    links_added = 0
    already_linked_slugs = set()

    # Track existing wikilinks
    for existing in re.findall(r"\[\[([^|\]]+)(?:\|[^\]]+)?\]\]", body):
        already_linked_slugs.add(existing.strip().lower())

    # Protect code blocks and existing links with placeholders
    placeholders = []
    def protect(m):
        placeholders.append(m.group(0))
        return f"__CANONFORGE_PROTECTED_{len(placeholders)-1}__"

    body = re.sub(r"```[\s\S]*?```", protect, body)
    body = re.sub(r"`[^`]+`", protect, body)
    body = re.sub(r"<!--[\s\S]*?-->", protect, body)
    body = re.sub(r"\[\[[^\]]+\]\]", protect, body)
    body = re.sub(r"\[[^\]]+\]\([^)]+\)", protect, body)

    for alias, slug, title in entities:
        if slug.lower() in already_linked_slugs:
            continue

        # Match whole word boundary, case-insensitive
        escaped_alias = re.escape(alias)
        pattern = rf"\b({escaped_alias})\b"
        
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            matched_text = match.group(1)
            # Only link first mention in chapter
            replacement = f"[[{slug}|{matched_text}]]" if matched_text != slug else f"[[{slug}]]"
            body = body[:match.start()] + replacement + body[match.end():]
            already_linked_slugs.add(slug.lower())
            links_added += 1

    # Restore placeholders in reverse
    for i in range(len(placeholders) - 1, -1, -1):
        body = body.replace(f"__CANONFORGE_PROTECTED_{i}__", placeholders[i])

    return f"{frontmatter}{body}", links_added

def link_manuscript(
    root_dir: Optional[Path] = None,
    book_filter: Optional[str] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    root = root_dir or find_universe_root()
    wiki_dir = root / "wiki"
    manuscript_dir = root / "manuscript"

    entities = get_linkable_entities(wiki_dir)
    
    if book_filter:
        chapters = list(manuscript_dir.glob(f"**/*{book_filter}*/**/chapters/*.md"))
        if not chapters:
            chapters = list(manuscript_dir.glob(f"**/*{book_filter}*/*.md"))
    else:
        chapters = list(manuscript_dir.glob("*/*/*/chapters/*.md"))
        if not chapters:
            chapters = list(manuscript_dir.glob("*/chapters/*.md"))
            if not chapters:
                chapters = list(manuscript_dir.glob("**/*.md"))

    chapters = [c for c in chapters if not any(x in c.parts for x in ("_build", "compiled", "archive", "exports"))]

    total_links = 0
    updated_files = []

    for ch in sorted(chapters):
        orig_text = ch.read_text(encoding="utf-8")
        linked_text, count = link_chapter_text(orig_text, entities)
        if count > 0:
            total_links += count
            updated_files.append((ch, count))
            if not dry_run:
                ch.write_text(linked_text, encoding="utf-8")

    return {
        "total_chapters": len(chapters),
        "total_entities_indexed": len(entities),
        "total_links_added": total_links,
        "updated_files": updated_files,
        "dry_run": dry_run,
    }

def print_link_report(res: Dict[str, Any], root: Path):
    print("\n" + "=" * 70)
    print("CANONFORGE: SEMANTIC ENTITY WIKILINKER")
    print("=" * 70)
    print(f"• Total Chapters Examined : {res['total_chapters']}")
    print(f"• Total Entities Indexed  : {res['total_entities_indexed']}")
    print(f"• Total Wikilinks Added   : {res['total_links_added']}")
    if res["dry_run"]:
        print("  (Dry-Run Mode: No files were modified)")
    print("-" * 70)

    if not res["updated_files"]:
        print("✨ All entities are already linked. No changes needed.\n")
        return

    for ch, count in res["updated_files"]:
        print(f"  ✓ {ch.relative_to(root)} (+{count} links)")
    print()

def main():
    parser = argparse.ArgumentParser(description="CanonForge Semantic Entity Wikilinker")
    parser.add_argument("--book", "-b", help="Filter linking to specific book slug or folder")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Preview links without writing to files")
    args = parser.parse_args()

    root = find_universe_root()
    res = link_manuscript(root_dir=root, book_filter=args.book, dry_run=args.dry_run)
    print_link_report(res, root)

if __name__ == "__main__":
    main()
