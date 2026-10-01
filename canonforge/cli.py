#!/usr/bin/env python3
"""
OKF STUDIO: ROOT MULTI-UNIVERSE ORCHESTRATOR & CLI
--------------------------------------------------------------------------------
Top-level entrypoint for managing, discovering, and auditing novel universes
under the Open Knowledge Fiction (OKF v0.3) standard.
"""

import sys
import os
import re
import shutil
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

PACKAGE_ROOT = Path(__file__).resolve().parent
SCHEMAS_DIR = PACKAGE_ROOT / "schemas"
DATA_DIR = PACKAGE_ROOT / "data"

def find_workspace_root(start_dir: Optional[Path] = None) -> Path:
    """Dynamically discover workspace root containing universes or universe.yaml."""
    curr = (start_dir or Path.cwd()).resolve()
    for parent in [curr, *curr.parents]:
        if (parent / "universe.yaml").is_file():
            return parent.parent
        if any(p.is_dir() and (p / "universe.yaml").is_file() for p in parent.iterdir() if not p.name.startswith(".")):
            return parent
    return curr

def discover_universes(workspace_root: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Scan root directories for universe.yaml manifests."""
    root = workspace_root or find_workspace_root()
    universes = []

    # Case 1: Active directory itself is a universe
    if (root / "universe.yaml").is_file():
        u = _load_universe_meta(root)
        if u:
            universes.append(u)
        return universes

    # Case 2: Multi-universe workspace (search child folders)
    for item in sorted(root.iterdir()):
        if not item.is_dir() or item.name.startswith((".", "_", "dist", "build", "canonforge")):
            continue
        if item.name == "examples":
            for sub in item.iterdir():
                if sub.is_dir() and (sub / "universe.yaml").is_file():
                    u = _load_universe_meta(sub)
                    if u:
                        universes.append(u)
            continue

        if (item / "universe.yaml").is_file():
            u = _load_universe_meta(item)
            if u:
                universes.append(u)

    return universes

def _load_universe_meta(u_dir: Path) -> Optional[Dict[str, Any]]:
    u_manifest = u_dir / "universe.yaml"
    if not u_manifest.is_file():
        return None

    raw_text = u_manifest.read_text(encoding="utf-8")
    meta = {}
    if HAS_YAML:
        try:
            meta = yaml.safe_load(raw_text) or {}
        except Exception:
            pass
    else:
        # Regex fallback for pure standard library environments
        m_id = re.search(r'universe_id:\s*["\']?([^"\']+)["\']?', raw_text)
        if m_id:
            meta["universe_id"] = m_id.group(1).strip()
        m_name = re.search(r'display_name:\s*["\']?([^"\']+)["\']?', raw_text)
        if m_name:
            meta["display_name"] = m_name.group(1).strip()
        m_sensory = re.search(r'sensory_profile:\s*["\']?([^"\']+)["\']?', raw_text)
        if m_sensory:
            meta["sensory_profile"] = m_sensory.group(1).strip()


    ms_dir = u_dir / "manuscript"
    series_count = 0
    book_count = 0
    chapter_count = 0
    total_words = 0

    if ms_dir.is_dir():
        series_count = len(list(ms_dir.glob("*/series.yaml")))
        book_count = len(list(ms_dir.glob("*/*/toc.yaml")))

        for ch in ms_dir.glob("*/*/chapters/*.md"):
            chapter_count += 1
            try:
                words = len(ch.read_text(encoding="utf-8").split())
                total_words += words
            except Exception:
                pass

    return {
        "id": meta.get("universe_id", u_dir.name),
        "name": meta.get("display_name", u_dir.name.replace("-", " ").title()),
        "dir": u_dir,
        "genre": meta.get("genre", ["Fiction"]),
        "sensory_profile": meta.get("sensory_profile", "core"),
        "status": meta.get("status", "draft"),
        "series_count": series_count,
        "book_count": book_count,
        "chapter_count": chapter_count,
        "total_words": total_words
    }

def cmd_list(args):
    """List all registered universes."""
    root = find_workspace_root()
    universes = discover_universes(root)

    print("\n" + "=" * 80)
    print("OKF STUDIO: MULTI-UNIVERSE WORKSPACE DISCOVERY")
    print(f"Workspace Root: {root}")
    print("=" * 80)

    if not universes:
        print("  (No valid universes found. Run 'okf scaffold <name>' to create one.)\n")
        return

    table_data = []
    for u in universes:
        genre_str = ", ".join(u["genre"]) if isinstance(u["genre"], list) else str(u["genre"])
        table_data.append([
            u["id"],
            u["name"],
            genre_str,
            u["sensory_profile"],
            f"{u['series_count']} series",
            f"{u['book_count']} books",
            f"{u['chapter_count']} ch ({u['total_words']:,} w)"
        ])

    headers = ["ID", "Universe Name", "Genre", "Sensory Profile", "Series", "Books", "Volume"]
    if HAS_TABULATE:
        print(tabulate(table_data, headers=headers, tablefmt="psql"))
    else:
        for row in table_data:
            print(f"• [{row[0]}] {row[1]} | {row[2]} | {row[4]}, {row[5]}, {row[6]}")
    print("=" * 80 + "\n")

def cmd_verify(args):
    """Run verification suites across one or all universes."""
    universes = discover_universes()
    target_id = args.universe.lower() if args.universe else None

    if target_id:
        targets = [u for u in universes if u["id"] == target_id or u["dir"].name.lower() == target_id]
        if not targets:
            print(f"❌ Error: Universe '{args.universe}' not found.")
            sys.exit(1)
    else:
        targets = universes

    if not targets:
        print("❌ Error: No universes found to verify.")
        sys.exit(1)

    overall_pass = True
    for u in targets:
        print(f"\n🚀 Running Verification Suite for: {u['name']} ({u['id']})...")
        # Run internal verification engine
        from canonforge.universe_cli import verify_universe
        passed = verify_universe(u["dir"])
        if not passed:
            overall_pass = False

    if overall_pass:
        print("\n🎉 ALL UNIVERSES VERIFIED SUCCESSFULLY!\n")
        sys.exit(0)
    else:
        print("\n💥 ONE OR MORE UNIVERSES FAILED VERIFICATION.\n")
        sys.exit(1)

def cmd_stats(args):
    """Display comprehensive workspace prose telemetry."""
    universes = discover_universes()
    total_series = sum(u["series_count"] for u in universes)
    total_books = sum(u["book_count"] for u in universes)
    total_chapters = sum(u["chapter_count"] for u in universes)
    total_words = sum(u["total_words"] for u in universes)

    print("\n" + "=" * 70)
    print("OKF STUDIO: MULTI-UNIVERSE PROSE STATISTICS")
    print("=" * 70)
    print(f"• Total Universes          : {len(universes)}")
    print(f"• Total Series Lines       : {total_series}")
    print(f"• Total Books Manifested   : {total_books}")
    print(f"• Total Chapters Authored  : {total_chapters:,}")
    print(f"• Total Prose Word Count   : {total_words:,} words")
    print("-" * 70)
    for u in universes:
        print(f"  🌌 {u['name']} [{u['id']}]: {u['book_count']} books | {u['chapter_count']:,} ch | {u['total_words']:,} words")
    print("=" * 70 + "\n")

def cmd_scaffold(args):
    """Scaffold a brand new universe repository with full 5-tier OKF hierarchy."""
    slug = re.sub(r"[^a-zA-Z0-9_-]", "-", args.slug.lower()).strip("-")
    root = find_workspace_root()
    u_dir = root / slug
    if u_dir.exists():
        print(f"❌ Error: Directory '{slug}' already exists at {u_dir}")
        sys.exit(1)

    display_name = args.title or slug.replace("-", " ").title()
    genre = args.genre or "Science Fiction"
    sensory = args.sensory_profile or "cyberpunk_scifi"

    print(f"\n🏗️  Scaffolding New Universe: {display_name} [{slug}]...")

    # 1. Directory Structure
    (u_dir / "manuscript" / "series-01" / "book-01" / "chapters").mkdir(parents=True, exist_ok=True)
    (u_dir / "manuscript" / "_build" / "compiled").mkdir(parents=True, exist_ok=True)
    (u_dir / "wiki" / "terms" / "characters").mkdir(parents=True, exist_ok=True)
    (u_dir / "wiki" / "terms" / "factions").mkdir(parents=True, exist_ok=True)
    (u_dir / "wiki" / "terms" / "places").mkdir(parents=True, exist_ok=True)
    (u_dir / "wiki" / "systems").mkdir(parents=True, exist_ok=True)
    (u_dir / "data").mkdir(parents=True, exist_ok=True)
    (u_dir / "schemas").mkdir(parents=True, exist_ok=True)

    # 2. universe.yaml
    u_content = f"""universe_id: "{slug}"
display_name: "{display_name}"
version: "1.0.0"
authority: "canon-lead"
status: "in-development"

genre:
  - "{genre}"

sensory_profile: "{sensory}"

metaphysics:
  primary_source: "Atmospheric Mana / Neural Grid"
  core_conflict: "Organic Heritage vs Synthetic Transcendence"

series_catalog:
  - id: "series-01"
    title: "{display_name} - Series One"
    path: "manuscript/series-01"
    status: "in-progress"
"""
    (u_dir / "universe.yaml").write_text(u_content, encoding="utf-8")

    # 3. series.yaml
    s_content = f"""series_id: "series-01"
title: "{display_name} - Series One"
universe: "{slug}"
status: "in-progress"
author: "Author"

books:
  - book_number: 1
    directory: "book-01"
    title: "Book 1: Awakening"
    status: "in-progress"
"""
    (u_dir / "manuscript" / "series-01" / "series.yaml").write_text(s_content, encoding="utf-8")

    # 4. toc.yaml
    t_content = f"""book:
  id: "book-01"
  book_number: 1
  series_id: "series-01"
  title: "Book 1: Awakening"
  status: "in-progress"
  act_structure: "3-act"

acts:
  - act: 1
    title: "The Descent"
    chapters:
      - file: "ch01-the-first-signal.md"
        title: "The First Signal"
        chapter_number: 1
        pov: "Protagonist"
"""
    (u_dir / "manuscript" / "series-01" / "book-01" / "toc.yaml").write_text(t_content, encoding="utf-8")

    # 5. First Chapter
    ch_content = f"""---
okf_version: "0.3"
chapter: 1
act: 1
title: "The First Signal"
pov: "Protagonist"
timeline: "Year 1"
setting: "District Sector"
word_count: 500
characters:
  - "Protagonist"
sensory_focus:
  - "Sight: Neon flare on wet chrome"
  - "Sound: Low hydraulic whine"
  - "Smell: Ozone and hot machine grease"
  - "Taste: Bitter ration wafer"
  - "Touch: Biting cold rain"
status: "draft"
---

# Chapter 1: The First Signal

The neon beacon over the alleyway flickered with a quiet, persistent buzz, casting cold shadows across the wet chrome deck.
"""
    (u_dir / "manuscript" / "series-01" / "book-01" / "chapters" / "ch01-the-first-signal.md").write_text(ch_content, encoding="utf-8")

    # 6. Copy chapter schema
    if SCHEMAS_DIR.is_dir():
        for sf in SCHEMAS_DIR.glob("*.json"):
            shutil.copy(sf, u_dir / "schemas" / sf.name)

    # 7. Generate ax wrapper script
    ax_content = """#!/usr/bin/env bash
set -e
if command -v okf >/dev/null 2>&1; then
    exec okf "$@"
elif command -v ax >/dev/null 2>&1; then
    exec ax "$@"
else
    python3 -m canonforge.universe_cli "$@"
fi
"""
    u_ax = u_dir / "ax"
    u_ax.write_text(ax_content, encoding="utf-8")
    u_ax.chmod(0o755)

    print(f"✅ Successfully scaffolded universe '{slug}' at: {u_dir}")
    print(f"💡 Get started:")
    print(f"   cd {slug}")
    print(f"   ./ax verify\n")

def main():
    parser = argparse.ArgumentParser(description="OKF Studio: Open Knowledge Fiction Multi-Universe Orchestrator")
    subparsers = parser.add_subparsers(dest="subcommand", help="Sub-commands")

    # list
    p_list = subparsers.add_parser("list", aliases=["list-universes"], help="List all registered universes")
    p_list.set_defaults(func=cmd_list)

    # verify
    p_verify = subparsers.add_parser("verify", help="Run verification suites across universes")
    p_verify.add_argument("universe", nargs="?", default=None, help="Optional universe ID or folder to verify")
    p_verify.set_defaults(func=cmd_verify)

    # stats
    p_stats = subparsers.add_parser("stats", help="Display workspace prose and chapter statistics")
    p_stats.set_defaults(func=cmd_stats)

    # scaffold / init
    p_scaffold = subparsers.add_parser("scaffold", aliases=["init"], help="Scaffold a new universe directory")
    p_scaffold.add_argument("slug", help="Slug/Folder name for the universe (e.g. aetheria, neon-city)")
    p_scaffold.add_argument("--title", help="Display title (e.g. 'Aetheria: Skies of Iron')")
    p_scaffold.add_argument("--genre", help="Universe genre (e.g. 'Cyberpunk', 'Space Opera')")
    p_scaffold.add_argument("--sensory-profile", help="Default sensory profile")
    p_scaffold.set_defaults(func=cmd_scaffold)

    # If first argument is an author experience command, forward to universe_cli
    author_commands = {"sensory", "pov", "prose", "polish", "thesaurus"}
    if len(sys.argv) > 1 and sys.argv[1] in author_commands:
        from canonforge import universe_cli
        universe_cli.main()
        return

    args, unknown = parser.parse_known_args()
    if not args.subcommand:
        cmd_list(args)
        return

    args.func(args)

if __name__ == "__main__":
    main()
