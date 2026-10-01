"""
CanonForge CLI: Anti-Deadend Engine, Workspace Discovery & Dashboard
--------------------------------------------------------------------------------
Provides zero-error discovery, contextual dashboard on bare invocation,
and typo suggestion for misentered subcommands.
"""

import os
import sys
import re
import difflib
from pathlib import Path
from typing import Dict, List, Any, Optional
from canonforge.cli.groups import style

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

def find_workspace_root(start_dir: Optional[Path] = None) -> Path:
    """Dynamically discover workspace root containing universes or universe.yaml."""
    curr = (start_dir or Path.cwd()).resolve()
    for parent in [curr, *curr.parents]:
        if (parent / "universe.yaml").is_file():
            return parent.parent
        try:
            if any(p.is_dir() and (p / "universe.yaml").is_file() for p in parent.iterdir() if not p.name.startswith(".")):
                return parent
        except (PermissionError, FileNotFoundError):
            continue
    return curr

def find_enclosing_universe(start_dir: Optional[Path] = None) -> Optional[Path]:
    """Check if current directory or any ancestor is a universe directory."""
    curr = (start_dir or Path.cwd()).resolve()
    for candidate in [curr, *curr.parents]:
        if (candidate / "universe.yaml").is_file():
            return candidate
    return None

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
    recent_chapters: List[Dict[str, Any]] = []

    if ms_dir.is_dir():
        series_count = len(list(ms_dir.glob("*/series.yaml")))
        book_count = len(list(ms_dir.glob("*/*/toc.yaml")))

        all_chapters = sorted(list(ms_dir.glob("*/*/chapters/*.md")), key=lambda p: p.stat().st_mtime, reverse=True)
        chapter_count = len(all_chapters)
        for ch in all_chapters:
            try:
                words = len(ch.read_text(encoding="utf-8").split())
                total_words += words
                if len(recent_chapters) < 3:
                    recent_chapters.append({"path": ch, "name": ch.stem, "words": words})
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
        "total_words": total_words,
        "recent_chapters": recent_chapters
    }

def discover_universes(workspace_root: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Scan root directories for universe.yaml manifests."""
    root = workspace_root or find_workspace_root()
    universes = []

    if (root / "universe.yaml").is_file():
        u = _load_universe_meta(root)
        if u:
            universes.append(u)
        return universes

    try:
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
    except (PermissionError, FileNotFoundError):
        pass

    return universes

def render_dashboard():
    """Anti-Deadend Engine: Render contextual workspace/universe dashboard on bare cf."""
    enclosing = find_enclosing_universe()
    if enclosing:
        # Inside a universe: show universe-level telemetry
        meta = _load_universe_meta(enclosing)
        if not meta:
            print(f"🌌 Universe directory detected at: {enclosing.name}")
            return

        genre_str = ", ".join(meta["genre"]) if isinstance(meta["genre"], list) else str(meta["genre"])
        print("\n" + style("=" * 72, "cyan"))
        print(f"🌌 {style(meta['name'], 'bold')} [{style(meta['id'], 'yellow')}]")
        print(f"   Genre: {genre_str} | Sensory Profile: {meta['sensory_profile']}")
        print(style("-" * 72, "gray"))
        print(f"   Volume : {style(str(meta['series_count']), 'bold')} series | {style(str(meta['book_count']), 'bold')} books | {style(str(meta['chapter_count']), 'bold')} chapters | {style(f'{meta['total_words']:,}', 'green')} words")

        if meta["recent_chapters"]:
            print(f"\n   {style('Recent Chapters:', 'bold')}")
            for rc in meta["recent_chapters"]:
                print(f"   • {rc['name']} ({rc['words']:,} words)")

        print(style("-" * 72, "gray"))
        print(f"💡 {style('Suggested Next Actions:', 'bold')}")
        print(f"   {style('cf prep', 'bold'):<24} Prepare authoring brief for active draft")
        print(f"   {style('cf new chapter', 'bold'):<24} Scaffold next chapter in active book")
        print(f"   {style('cf audit', 'bold'):<24} Run multi-engine prose & POV audit")
        print(f"   {style('cf review', 'bold'):<24} Generate literary scorecard (/10)")
        print(f"   {style('cf export', 'bold'):<24} Export manuscript to EPUB and HTML")
        print(style("=" * 72, "cyan") + "\n")
        return

    # Outside universe: show workspace-level discovery
    root = find_workspace_root()
    universes = discover_universes(root)
    print("\n" + style("=" * 72, "cyan"))
    print(f"🚀 {style('CANONFORGE NOVEL WORKSPACE', 'bold')}")
    print(f"   Root: {root}")
    print(style("-" * 72, "gray"))

    if universes:
        print(f"   Discovered {style(str(len(universes)), 'bold')} universes:")
        for u in universes:
            print(f"   • 🌌 {style(u['name'], 'bold')} [{u['id']}]: {u['book_count']} books | {u['chapter_count']} ch ({u['total_words']:,} w)")
    else:
        print("   No universes discovered yet.")

    print(style("-" * 72, "gray"))
    print(f"💡 {style('Suggested Next Actions:', 'bold')}")
    print(f"   {style('cf list', 'bold'):<24} List all universes and detailed manifests")
    print(f"   {style('cf stats', 'bold'):<24} Display workspace telemetry")
    print(f"   {style('cf new universe', 'bold'):<24} Scaffold a new fiction universe")
    print(f"   {style('cf verify', 'bold'):<24} Run verification suite across universes")
    print(style("=" * 72, "cyan") + "\n")

def suggest_similar_command(unknown_cmd: str, valid_cmds: List[str]):
    """Intelligent typo suggester using difflib distance."""
    matches = difflib.get_close_matches(unknown_cmd, valid_cmds, n=2, cutoff=0.45)
    print(f"\n{style('❌ Unknown command:', 'yellow')} '{unknown_cmd}'")
    if matches:
        suggestions = " or ".join([f"'{style('cf ' + m, 'bold')}'" for m in matches])
        print(f"💡 Did you mean: {suggestions}?")
    print(f"\nRun '{style('cf --help', 'bold')}' to see all available commands.\n")

def cmd_list(args):
    """List all registered universes."""
    root = find_workspace_root()
    universes = discover_universes(root)

    print("\n" + "=" * 80)
    print("CANONFORGE: MULTI-UNIVERSE WORKSPACE DISCOVERY")
    print(f"Workspace Root: {root}")
    print("=" * 80)

    if not universes:
        print("  (No valid universes found. Run 'cf new universe <name>' to create one.)\n")
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

def cmd_stats(args):
    """Display comprehensive workspace prose telemetry."""
    universes = discover_universes()
    total_series = sum(u["series_count"] for u in universes)
    total_books = sum(u["book_count"] for u in universes)
    total_chapters = sum(u["chapter_count"] for u in universes)
    total_words = sum(u["total_words"] for u in universes)

    print("\n" + "=" * 70)
    print("CANONFORGE: MULTI-UNIVERSE PROSE STATISTICS")
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

def cmd_verify(args):
    """Run verification suites across one or all universes."""
    universes = discover_universes()
    target_id = args.universe.lower() if getattr(args, "universe", None) else None

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
        from canonforge.universe_cli import verify_universe
        passed = verify_universe(u["dir"])
        if not passed:
            overall_pass = False

    if overall_pass:
        print("\n🎉 ALL UNIVERSES VERIFIED SUCCESSFULLY!\n")
    else:
        print("\n💥 ONE OR MORE UNIVERSES FAILED VERIFICATION.\n")
        sys.exit(1)
