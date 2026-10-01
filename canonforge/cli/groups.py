"""
CanonForge CLI: Capability Explorer & Grouped Help Formatter
--------------------------------------------------------------------------------
Groups all subcommands into logical functional pillars:
[PROJECT], [AUTHORING], [AUDITING], [WORLDBUILDING], [PUBLISHING], [AGENT].
"""

import os
import sys
from typing import Dict, List, Tuple

# Capability groupings for CanonForge
CAPABILITY_GROUPS: Dict[str, List[Tuple[str, str]]] = {
    "PROJECT": [
        ("list", "List all registered universes in workspace"),
        ("stats", "Display prose word count and volume statistics"),
        ("verify", "Run verification suite across universe(s)"),
        ("new", "Hierarchical scaffolding (universe, series, book, chapter, character)"),
        ("init", "Initialize a new universe (alias: scaffold)"),
    ],
    "AUTHORING": [
        ("prep", "Prepare authoring brief and drafting context pack"),
        ("dialogue", "Audit dialogue beats, subtext, and speech tags"),
        ("play", "Interactive Ink branching dialogue runner & HTML player"),
        ("thesaurus", "Lookup evocative sensory synonyms and antonyms"),
    ],
    "AUDITING": [
        ("audit", "Comprehensive multi-engine audit emitting diagnostic codes"),
        ("review", "Single-pass literary review and benchmark scorecard (/10)"),
        ("sensory", "5-senses radar audit and 4-sense window compliance"),
        ("pov", "Deep 3rd Limited POV audit (no head-hopping, physicalized emotion)"),
        ("prose", "Anti-slop and AI cadence linter (tricolons, filter words)"),
        ("continuity", "Character state, inventory, and trait continuity gate"),
        ("timeline", "Chronological progression and travel physics gate"),
        ("secrets", "Information disclosure and dramatic irony tracking gate"),
    ],
    "WORLDBUILDING": [
        ("scan", "Scan manuscript for unregistered entities & auto-scaffold"),
        ("link", "Automatically link entity mentions in manuscript to wiki"),
        ("search", "Universal search across wiki dossiers and local game database"),
        ("update", "Update entity attributes, status, and tags with safe diffs"),
        ("lore", "SSOT lore bible validator and entity extractor"),
        ("relations", "Character social graph and faction network validator"),
        ("db", "Game world database sync and SQL schema generator"),
        ("combat", "Tactical combat telemetry and battle mechanics evaluator"),
        ("travel", "Expedition logistics and spatial route planner"),
    ],
    "PUBLISHING": [
        ("compile", "Compile manuscript chapters into consolidated book volume"),
        ("export", "Export manuscript to production formats (EPUB, Shunn, MD)"),
    ],
    "AGENT": [
        ("skill", "Export agent rules and skills (Cursor, Claude, Antigravity)"),
        ("obsidian", "Install and configure CanonForge Studio Obsidian plugin"),
        ("hook", "Install and manage Git pre-commit integrity hook"),
    ],
}

def _supports_color() -> bool:
    """Check if color output is supported and not disabled."""
    if os.environ.get("NO_COLOR"):
        return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

def style(text: str, color: str) -> str:
    """Format text with ANSI escape codes if color is enabled."""
    if not _supports_color():
        return text
    codes = {
        "bold": "\033[1m",
        "cyan": "\033[36m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "gray": "\033[90m",
        "reset": "\033[0m",
    }
    return f"{codes.get(color, '')}{text}{codes['reset']}"

def print_grouped_help():
    """Print clean, grouped capability explorer for CanonForge CLI."""
    banner = f"""{style("╔════════════════════════════════════════════════════════════════════════════╗", "cyan")}
{style("║", "cyan")}  {style("CANONFORGE CLI (cf)", "bold")} - Git-Native Literary Engineering Studio         {style("║", "cyan")}
{style("╚════════════════════════════════════════════════════════════════════════════╝", "cyan")}
{style("Usage:", "bold")} cf <command> [options] [arguments]
       cf new <universe|series|book|chapter|character> ...
       cf audit [chapter] [--format json]
"""
    print(banner)

    for group_name, cmds in CAPABILITY_GROUPS.items():
        header = f"  {style(f'[{group_name}]', 'yellow')}"
        print(header)
        for cmd_name, desc in cmds:
            padded_cmd = f"    {style(cmd_name, 'bold'):<26}"
            print(f"{padded_cmd} {style(desc, 'gray')}")
        print()

    footer = f"""{style("Quick Tips:", "bold")}
  • Run {style("cf", "bold")} without arguments inside any universe to see active draft dashboard.
  • Run {style("cf new chapter --help", "bold")} to see chapter scaffolding options.
  • Run {style("cf audit", "bold")} to run full multi-engine diagnostics across manuscript.
  • Run {style("cf skill export", "bold")} to generate agent rules for Cursor, Claude, or Antigravity.
"""
    print(footer)
