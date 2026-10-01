"""
Interactive Studio TUI Engine
--------------------------------------------------------------------------------
Provides a universal, dynamic interactive numbered dashboard for any novel
universe without hardcoded IP. Automatically infers active draft book, recent
chapters, protagonists, settings, monsters, and dialogue assets from manifests
and filesystem metadata, with optional studio_presets overrides in universe.yaml.
"""

import sys
import os
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def find_universe_root(start_dir: Optional[Path] = None) -> Path:
    """Ascend directories to locate the enclosing universe.yaml manifest."""
    curr = (start_dir or Path.cwd()).resolve()
    for parent in [curr, *curr.parents]:
        if (parent / "universe.yaml").is_file():
            return parent
    return curr


def parse_simple_yaml(text: str) -> Dict[str, Any]:
    """Lightweight YAML parser fallback when pyyaml is not available."""
    data: Dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            data[k.strip()] = v.strip().strip('"').strip("'")
    return data


def detect_universe_context(universe_dir: Path) -> Dict[str, Any]:
    """Dynamically infer universe metadata, active draft book, and defaults."""
    u_manifest = universe_dir / "universe.yaml"
    meta: Dict[str, Any] = {}
    if u_manifest.is_file():
        try:
            raw_text = u_manifest.read_text(encoding="utf-8")
            if HAS_YAML:
                meta = yaml.safe_load(raw_text) or {}
            else:
                meta = parse_simple_yaml(raw_text)
        except Exception:
            pass

    display_name = meta.get("display_name", universe_dir.name)
    presets = meta.get("studio_presets", {})
    if not isinstance(presets, dict):
        presets = {}

    # Scan manuscript for most recently modified chapter & active book
    active_book = presets.get("default_book", "")
    active_chapter = ""
    default_origin = presets.get("default_origin", "")
    default_player = presets.get("default_player", "")

    chapters = list(universe_dir.glob("manuscript/*/*/chapters/*.md"))
    if not chapters:
        chapters = list(universe_dir.glob("manuscript/*/*.md"))

    if chapters:
        # Sort by mtime descending
        chapters.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        latest_ch = chapters[0]
        active_chapter = latest_ch.stem

        if not active_book:
            # Infer book slug from chapter's parent hierarchy
            # Path: .../manuscript/<series>/<book>/chapters/ch01.md
            parts = latest_ch.parts
            if "chapters" in parts:
                idx = parts.index("chapters")
                if idx > 0:
                    active_book = parts[idx - 1]
            if not active_book:
                active_book = latest_ch.parent.name

        # Parse chapter frontmatter for setting / pov if not preset
        if not default_origin or not default_player:
            try:
                content = latest_ch.read_text(encoding="utf-8", errors="ignore")
                if content.startswith("---"):
                    fm_end = content.find("---", 3)
                    if fm_end != -1:
                        fm_text = content[3:fm_end]
                        fm_data = yaml.safe_load(fm_text) if HAS_YAML else parse_simple_yaml(fm_text)
                        if isinstance(fm_data, dict):
                            if not default_origin and fm_data.get("setting"):
                                default_origin = str(fm_data["setting"]).split(",")[0].strip()
                            if not default_player and fm_data.get("pov"):
                                default_player = str(fm_data["pov"]).strip()
            except Exception:
                pass

    # Protagonist fallback from series_catalog or wiki
    if not default_player:
        series_cat = meta.get("series_catalog", [])
        if isinstance(series_cat, list) and series_cat:
            first_s = series_cat[0]
            if isinstance(first_s, dict) and first_s.get("protagonists"):
                prots = first_s["protagonists"]
                if isinstance(prots, list) and prots:
                    default_player = str(prots[0])

    if not default_player:
        char_files = list(universe_dir.glob("wiki/terms/characters/*.md")) + list(universe_dir.glob("wiki/characters/*.md"))
        if char_files:
            default_player = char_files[0].stem

    # Default monster
    default_monster = presets.get("default_monster", "")
    if not default_monster:
        mon_files = list(universe_dir.glob("wiki/terms/monsters/*.md")) + list(universe_dir.glob("wiki/bestiary/*.md"))
        if mon_files:
            default_monster = mon_files[0].stem

    # Default destination
    default_dest = presets.get("default_destination", "")
    if not default_dest:
        place_files = list(universe_dir.glob("wiki/terms/places/*.md")) + list(universe_dir.glob("wiki/places/*.md"))
        if place_files:
            default_dest = place_files[0].stem.replace("-", " ").title()

    # Default Ink file
    default_ink = presets.get("default_ink_file", "")
    if not default_ink:
        ink_files = list(universe_dir.glob("dialogue/*.ink"))
        if ink_files:
            default_ink = str(ink_files[0].relative_to(universe_dir))

    return {
        "display_name": display_name,
        "active_book": active_book or "book-01",
        "active_chapter": active_chapter,
        "default_origin": default_origin or "Capital",
        "default_destination": default_dest or "Frontier",
        "default_player": default_player or "char_hero",
        "default_monster": default_monster or "mon_beast",
        "default_ink_file": default_ink or "dialogue/main.ink",
    }


def render_menu(context: Dict[str, Any]):
    """Render the master interactive studio menu."""
    title = f"{context['display_name'].upper()} STUDIO: MASTER DEVELOPER DASHBOARD"
    line = "=" * max(70, len(title) + 4)
    print("\n" + line)
    print(f"  {title}")
    print(line)
    print("  [1]  🚀 Master Novel Pipeline (Audit -> Compile -> E-Book -> DB Sync)")
    print("  [2]  📚 E-Book & Reader Exporter (Batch HTML & EPUB 3.0 generation)")
    print("  [3]  🔍 Continuity & Canon Leak Auditor (Physical invariants & SSOT)")
    print("  [4]  ✍️  Prose Purity & Anti-Slop Linter (Filter words, AI cliches, cadence)")
    print("  [5]  👃 5-Senses Radar & Immersion Heatmap (Enforce Four-Sense Rule)")
    print("  [6]  🗺️  Spatial Travel & Logistics Planner (Route, hours, supplies)")
    print("  [7]  🎭 Interactive Ink Dialogue Player (Play in terminal or export HTML)")
    print("  [8]  ⚔️  Deterministic RPG Combat Simulator (PvE Battle & PvP Duels)")
    print("  [9]  🗄️  RPG Game Database Engine (v_character_combat_stats, loot, BOM)")
    print("  [10] 🧪 Master CI/CD Test Suite (All verification & integrity gates)")
    print("  [11] 🔍 Entity & Lore SSOT Search (Characters, Monsters, Places, Items)")
    print("  [12] 📖 Chapter Cast & Relic Inspector (Who is present, items, monsters)")
    print("  [13] 📝 Update Entity / Bio / Attributes / Tags (Auto-Sync to DB)")
    print("  [14] 📋 Scene Prep & Authoring Brief (Bridge, Cast Rules, Sensory Palette)")
    print("  [15] ✨ Unified Polish Suite & Scorecard (Anti-slop, 5-senses, Canon Guard)")
    print("  [16] 👤 Character Profile & Dossier (Biometrics, Social, Game Stats, Footprint)")
    print("  [17] 📊 Visual Canvas & Timeline (Multi-swimlane Obsidian canvas generation)")
    print("  [18] 📑 Chapter Appearance & Citation Index (Active presence vs mentions)")
    print("  [0]  🚪 Exit Studio")
    print("-" * len(line))


def _dispatch(choice: str, ctx: Dict[str, Any], u_dir: Path):
    """Dispatch user menu selection to the appropriate CanonForge engine."""
    saved_argv = list(sys.argv)
    saved_cwd = os.getcwd()
    try:
        os.chdir(str(u_dir))
        if choice == "1":
            from canonforge.engines.compiler import cli as comp_cli
            book = input(f"Enter book slug (default: {ctx['active_book']}) > ").strip() or ctx["active_book"]
            sys.argv = ["compiler", "--book", book]
            comp_cli.main()

        elif choice == "2":
            from canonforge.engines.exporter import cli as exp_cli
            sub = input(f"Export [1] Active Book ({ctx['active_book']}), [2] All Books > ").strip()
            sys.argv = ["export", "--all"] if sub == "2" else ["export", ctx["active_book"]]
            exp_cli.main()

        elif choice == "3":
            from canonforge.engines import continuity
            sys.argv = ["continuity", "--all"]
            continuity.main()

        elif choice == "4":
            from canonforge.engines import prose
            tgt = input("Enter chapter filename or book slug (or press Enter for all) > ").strip()
            sys.argv = ["prose", tgt] if tgt else ["prose", "--all-books"]
            prose.main()

        elif choice == "5":
            from canonforge.engines.sensory import radar as sen_radar
            tgt = input("Enter chapter filename or book slug (or press Enter for all) > ").strip()
            sys.argv = ["sensory", tgt] if tgt else ["sensory", "--all-books"]
            sen_radar.main()

        elif choice == "6":
            from canonforge.engines import travel
            orig = input(f"Origin location (default: {ctx['default_origin']}) > ").strip() or ctx["default_origin"]
            dest = input(f"Destination location (default: {ctx['default_destination']}) > ").strip() or ctx["default_destination"]
            mode = input("Transport mode [foot/mount/crawler/glider] (default: mount) > ").strip() or "mount"
            sys.argv = ["travel", "--from", orig, "--to", dest, "--mode", mode]
            travel.main()

        elif choice == "7":
            from canonforge.engines import dialogue
            sub_p = input("[1] Play in Terminal, [2] Export HTML Player > ").strip()
            f_ink = input(f"Ink file (default: {ctx['default_ink_file']}) > ").strip() or ctx["default_ink_file"]
            sys.argv = ["dialogue", "--file", f_ink, "--export-html"] if sub_p == "2" else ["dialogue", "--file", f_ink]
            dialogue.main()

        elif choice == "8":
            from canonforge.engines.combat import cli as combat_cli
            sub_cb = input("[1] Quick PvE, [2] Interactive Combat, [3] PvP Duel, [4] List Combatants > ").strip()
            if sub_cb == "2":
                p = input(f"Player ID (default: {ctx['default_player']}) > ").strip() or ctx["default_player"]
                m = input(f"Monster ID (default: {ctx['default_monster']}) > ").strip() or ctx["default_monster"]
                sys.argv = ["combat", "--player", p, "--monster", m, "--interactive"]
            elif sub_cb == "3":
                p1 = input(f"Player 1 ID (default: {ctx['default_player']}) > ").strip() or ctx["default_player"]
                p2 = input("Player 2 ID > ").strip()
                sys.argv = ["combat", "--player", p1, "--enemy-char", p2]
            elif sub_cb == "4":
                sys.argv = ["combat", "--list"]
            else:
                p = input(f"Player ID (default: {ctx['default_player']}) > ").strip() or ctx["default_player"]
                m = input(f"Monster ID (default: {ctx['default_monster']}) > ").strip() or ctx["default_monster"]
                sys.argv = ["combat", "--player", p, "--monster", m]
            combat_cli.main()

        elif choice == "9":
            from canonforge.engines import init_db, sync_db
            sub_d = input("[1] Sample Stats & Loot, [2] Custom SQL Query, [3] Reseed DB > ").strip()
            if sub_d == "2":
                q = input("SQL Query > ").strip()
                if q:
                    sys.argv = ["init_db", "--query", q]
                    init_db.main()
            elif sub_d == "3":
                sys.argv = ["init_db", "--seed"]
                init_db.main()
            else:
                sys.argv = ["init_db", "--sample"]
                init_db.main()

        elif choice == "10":
            from canonforge.engines.verifier import verify_universe
            verify_universe(u_dir)

        elif choice == "11":
            from canonforge.engines import search
            q = input("Search query (character, place, monster, item) > ").strip()
            if q:
                det = input("Show full detail? (y/N) > ").strip().lower() == "y"
                sys.argv = ["search", q, "-d"] if det else ["search", q]
            else:
                sys.argv = ["search", "--interactive"]
            search.main()

        elif choice == "12":
            from canonforge.engines import search
            ch = input(f"Chapter number or slug (default: {ctx['active_chapter'] or '1'}) > ").strip() or (ctx["active_chapter"] or "1")
            bk = input(f"Book slug (default: {ctx['active_book']}) > ").strip() or ctx["active_book"]
            sys.argv = ["search", "--chapter", ch, "--book", bk]
            search.main()

        elif choice == "13":
            from canonforge.engines import updater
            sys.argv = ["updater", "--interactive"]
            updater.main()

        elif choice == "14":
            from canonforge.engines.prep import cli as prep_cli
            tgt = input("Enter chapter filename, slug, or number (or press Enter for newest) > ").strip()
            p_mode = input("Generate LLM writing prompt? (y/N) > ").strip().lower() == "y"
            args = [tgt] if tgt else []
            if p_mode:
                args.append("--prompt")
            sys.argv = ["prep", *args]
            prep_cli.main()

        elif choice == "15":
            from canonforge.engines import polish
            tgt = input("Enter chapter filename, slug, or number (or press Enter for newest) > ").strip()
            sys.argv = ["polish", tgt] if tgt else ["polish"]
            polish.main()

        elif choice == "16":
            from canonforge.engines import profile
            target = input(f"Character name or slug (default: {ctx['default_player']}) > ").strip() or ctx["default_player"]
            sys.argv = ["profile", target]
            profile.main()

        elif choice == "17":
            from canonforge.engines import canvas
            sys.argv = ["canvas"]
            canvas.main()

        elif choice == "18":
            from canonforge.engines import appearances
            target = input(f"Character name or slug (default: {ctx['default_player']}) > ").strip() or ctx["default_player"]
            sys.argv = ["appearances", target]
            appearances.main()

    except SystemExit:
        pass
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
    except Exception as e:
        print(f"\n❌ Error executing action [{choice}]: {e}")
    finally:
        sys.argv = saved_argv
        os.chdir(saved_cwd)


def run_interactive_studio(universe_dir: Optional[Path] = None):
    """Launch the interactive studio TUI loop."""
    u_dir = (universe_dir or find_universe_root()).resolve()
    context = detect_universe_context(u_dir)

    while True:
        render_menu(context)
        try:
            choice = input("Select an action [0-18] > ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting Studio. Farewell!\n")
            break

        if choice in ("0", "q", "exit", "quit"):
            print(f"\nExiting {context['display_name']} Studio. Farewell!\n")
            break

        if choice in [str(i) for i in range(1, 19)]:
            _dispatch(choice, context, u_dir)
        else:
            print("Invalid selection. Try again.")


def main():
    parser = argparse.ArgumentParser(description="CanonForge Universal Interactive Studio TUI")
    parser.add_argument("--dir", "-d", help="Universe directory root")
    args = parser.parse_args()

    target_dir = Path(args.dir).resolve() if args.dir else find_universe_root()
    run_interactive_studio(target_dir)


if __name__ == "__main__":
    main()
