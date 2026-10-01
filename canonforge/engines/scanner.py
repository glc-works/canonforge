"""
canonforge/engines/scanner.py

Authoritative Entity Scanner & Autodiscovery Engine for CanonForge Studio.
Scans novel manuscript chapters for wikilinks and entity mentions, cross-referencing
them against wiki dossiers to detect unregistered lore entities, with auto-scaffolding.
100% Free of Universe-Specific Hardcoding.
"""

import sys
import os
import re
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PACKAGE_ROOT / "templates"

def find_universe_root(start_dir: Optional[Path] = None) -> Path:
    cwd = (start_dir or Path.cwd()).resolve()
    for parent in [cwd, *cwd.parents]:
        if (parent / "universe.yaml").is_file():
            return parent
    return cwd

def get_registered_entities(wiki_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Index all known entities and their aliases from wiki dossiers."""
    entities = {}
    if not wiki_dir.is_dir():
        return entities

    for f in wiki_dir.rglob("*.md"):
        if f.name.lower() in ("readme.md", "index.md", "summary.md"):
            continue

        stem = f.stem.lower()
        title = f.stem.replace("-", " ")
        
        # Read frontmatter
        try:
            content = f.read_text(encoding="utf-8")
        except Exception:
            continue

        m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        aliases = [stem, title.lower()]
        category = "character"
        
        if m:
            for line in m.group(1).splitlines():
                if ":" in line and not line.strip().startswith("#"):
                    k, v = line.split(":", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k in ("name", "title") and v:
                        title = v
                        aliases.append(v.lower())
                    elif k in ("aliases", "labels"):
                        for item in v.split(","):
                            cleaned = item.strip().lstrip("-").strip()
                            if cleaned:
                                aliases.append(cleaned.lower())

        rel_parts = f.relative_to(wiki_dir).parts
        if len(rel_parts) > 1:
            category = rel_parts[0]
            if category in ("terms", "database") and len(rel_parts) > 2:
                category = rel_parts[1]

        info = {
            "id": f.stem,
            "title": title,
            "category": category,
            "file": f,
            "aliases": list(set(aliases))
        }

        entities[stem] = info
        for a in aliases:
            entities[a] = info

    return entities

def scan_chapter_entities(chapter_path: Path) -> List[str]:
    """Extract all wikilink targets and capitalised proper names from a chapter."""
    text = chapter_path.read_text(encoding="utf-8")
    
    # Strip frontmatter
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.DOTALL)
    
    # Extract [[Target|Label]] or [[Target]]
    wikilinks = re.findall(r"\[\[([^|\]]+)(?:\|[^\]]+)?\]\]", text)
    return [w.strip() for w in wikilinks if w.strip()]

def scaffold_missing_entity(name: str, wiki_dir: Path, category: str = "characters") -> Path:
    """Scaffold a missing entity dossier using bundled templates."""
    slug = re.sub(r"[^a-zA-Z0-9_-]", "-", name.lower()).strip("-")
    target_dir = wiki_dir / "terms" / category
    if not target_dir.exists():
        target_dir = wiki_dir / category
    target_dir.mkdir(parents=True, exist_ok=True)
    
    out_file = target_dir / f"{slug}.md"
    if out_file.exists():
        return out_file

    tmpl_name = "character.md"
    if "place" in category or "location" in category:
        tmpl_name = "scene.md"
    elif "item" in category or "relic" in category:
        tmpl_name = "item.md"
    elif "monster" in category or "bestiary" in category:
        tmpl_name = "monster.md"
    elif "faction" in category:
        tmpl_name = "faction.md"

    tmpl_file = TEMPLATES_DIR / tmpl_name
    if tmpl_file.is_file():
        content = tmpl_file.read_text(encoding="utf-8")
        content = content.replace("{{title}}", name).replace("{{title_lower}}", slug)
    else:
        content = f"---\nokf_version: \"0.3\"\ntitle: \"{name}\"\nid: \"{slug}\"\nstatus: \"draft\"\n---\n\n# {name}\n\n*Scaffolded dossier draft.*\n"

    out_file.write_text(content, encoding="utf-8")
    return out_file

def run_entity_scan(
    root_dir: Optional[Path] = None,
    book_filter: Optional[str] = None,
    scaffold: bool = False
) -> Dict[str, Any]:
    root = root_dir or find_universe_root()
    wiki_dir = root / "wiki"
    manuscript_dir = root / "manuscript"

    registered = get_registered_entities(wiki_dir)
    
    # Discover chapter files
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

    unregistered: Dict[str, List[str]] = {}
    total_mentions = 0
    resolved_mentions = 0

    for ch in sorted(chapters):
        mentions = scan_chapter_entities(ch)
        for m in mentions:
            total_mentions += 1
            m_norm = m.lower().replace("-", " ")
            m_stem = m.lower()
            if m_norm in registered or m_stem in registered:
                resolved_mentions += 1
            else:
                if m not in unregistered:
                    unregistered[m] = []
                unregistered[m].append(ch.stem)

    scaffolded_files = []
    if scaffold and unregistered:
        for ent_name in unregistered.keys():
            created = scaffold_missing_entity(ent_name, wiki_dir)
            scaffolded_files.append(created)

    return {
        "total_chapters": len(chapters),
        "total_indexed_entities": len(set(e["id"] for e in registered.values())),
        "total_mentions": total_mentions,
        "resolved_mentions": resolved_mentions,
        "unregistered": unregistered,
        "scaffolded": scaffolded_files,
    }

def print_scan_report(results: Dict[str, Any], root: Path):
    print("\n" + "=" * 75)
    print("CANONFORGE: UNREGISTERED ENTITY & MANUSCRIPT SCANNER")
    print("=" * 75)
    print(f"• Total Chapters Scanned : {results['total_chapters']}")
    print(f"• Total Indexed Entities : {results['total_indexed_entities']}")
    print(f"• Entity Mentions Checked: {results['total_mentions']}")
    print(f"• Successfully Resolved  : {results['resolved_mentions']}")
    print(f"• Unregistered Entities  : {len(results['unregistered'])}")
    print("-" * 75)

    if not results["unregistered"]:
        print("🎉 100% CLEAN! All wikilinks and entity mentions exist in the wiki.\n")
        return

    rows = []
    for ent, chs in sorted(results["unregistered"].items(), key=lambda x: len(x[1]), reverse=True):
        count_str = f"{len(chs)} ch"
        sample_chs = ", ".join(chs[:2]) + (f" (+{len(chs)-2} more)" if len(chs) > 2 else "")
        rows.append([ent, count_str, sample_chs])

    headers = ["Unregistered Entity", "Occurrences", "Sample Chapters"]
    if HAS_TABULATE:
        print(tabulate(rows, headers=headers, tablefmt="rounded_grid"))
    else:
        for r in rows:
            print(f"• {r[0]:<30} | {r[1]:<10} | {r[2]}")

    if results["scaffolded"]:
        print("\n✨ Auto-Scaffolded Dossiers:")
        for sf in results["scaffolded"]:
            print(f"   ✓ Created: {sf.relative_to(root)}")
    else:
        print("\n💡 TIP: Run 'cf scan --scaffold' to automatically generate OKF v0.3 stubs for these entities.\n")

def main():
    parser = argparse.ArgumentParser(description="CanonForge Unregistered Entity Scanner & Scaffolder")
    parser.add_argument("--book", "-b", help="Filter scan to specific book slug or folder")
    parser.add_argument("--scaffold", "-s", action="store_true", help="Auto-scaffold missing OKF v0.3 dossiers")
    args = parser.parse_args()

    root = find_universe_root()
    res = run_entity_scan(root_dir=root, book_filter=args.book, scaffold=args.scaffold)
    print_scan_report(res, root)

if __name__ == "__main__":
    main()
