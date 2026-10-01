"""
CanonForge CLI: Unified Command Router & Main Entrypoint
--------------------------------------------------------------------------------
Dispatches commands across PROJECT, AUTHORING, AUDITING, WORLDBUILDING,
PUBLISHING, and AGENT functional pillars.
"""

import sys
import argparse
from pathlib import Path

from canonforge.cli.groups import print_grouped_help, CAPABILITY_GROUPS
from canonforge.cli.dashboard import (
    render_dashboard,
    suggest_similar_command,
    cmd_list,
    cmd_stats,
    cmd_verify,
)
from canonforge.cli.new_cmd import (
    new_universe,
    new_series,
    new_book,
    new_chapter,
    new_character,
    new_asset,
)
from canonforge.cli.audit_cmd import cmd_audit, cmd_review
from canonforge.cli.skill_cmd import cmd_skill_export, cmd_skill_show

def _dispatch_impact(args):
    from canonforge.engines import impact
    u_root = Path(args.universe).resolve() if getattr(args, "universe", None) else None
    res = impact.run_impact_analysis(
        universe_root=u_root,
        query=getattr(args, "query", ""),
        keywords=getattr(args, "keywords", []),
        character=getattr(args, "character", None),
        milestone=getattr(args, "milestone", None),
        series_filter=getattr(args, "series", None),
        book_filter=getattr(args, "book", None),
    )
    impact.render_impact_report(res, output_format=getattr(args, "format", "text"))

def _dispatch_consistency(args):
    from canonforge.engines import consistency
    u_root = Path(args.universe).resolve() if getattr(args, "universe", None) else None
    res = consistency.run_consistency_audit(
        universe_root=u_root,
        chapter_file=getattr(args, "chapter", None) or None,
        book_filter=getattr(args, "book", None),
        series_filter=getattr(args, "series", None),
        strict=getattr(args, "strict", False),
        output_format=getattr(args, "format", "text")
    )
    if not res.get("success", False):
        sys.exit(1)

def _get_all_valid_commands() -> list:
    cmds = []
    for group_cmds in CAPABILITY_GROUPS.values():
        for cmd_name, _ in group_cmds:
            cmds.append(cmd_name)
    # Add common aliases
    cmds.extend(["scaffold", "polish", "obsidian", "studio", "interactive", "consistency", "lint", "lint-consistency"])
    return sorted(list(set(cmds)))

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cf",
        description="CanonForge: Git-Native Literary Engineering Studio",
        add_help=False
    )
    parser.add_argument("-h", "--help", action="store_true", help="Show capability groupings")
    subparsers = parser.add_subparsers(dest="subcommand", help="Sub-commands")

    # 1. PROJECT
    p_list = subparsers.add_parser("list", help="List all registered universes")
    p_list.set_defaults(func=cmd_list)

    p_stats = subparsers.add_parser("stats", help="Display prose word count and chapter stats")
    p_stats.set_defaults(func=cmd_stats)

    p_verify = subparsers.add_parser("verify", help="Run multi-engine verification gates")
    p_verify.add_argument("universe", nargs="?", default=None, help="Optional universe to verify")
    p_verify.set_defaults(func=cmd_verify)

    # Scaffolding: cf new <target>
    p_new = subparsers.add_parser("new", help="Hierarchical scaffolding")
    new_sub = p_new.add_subparsers(dest="new_type", help="Scaffold target type")

    # cf new universe
    p_nu = new_sub.add_parser("universe", help="Scaffold a new universe")
    p_nu.add_argument("slug", help="Slug for the universe (e.g. aetheria)")
    p_nu.add_argument("--title", help="Display title")
    p_nu.add_argument("--genre", help="Genre (e.g. 'Epic Fantasy', 'Cyberpunk')")
    p_nu.add_argument("--sensory-profile", help="Default sensory profile")
    p_nu.set_defaults(func=new_universe)

    # cf new series
    p_ns = new_sub.add_parser("series", help="Scaffold a new series under a universe")
    p_ns.add_argument("slug", help="Slug for the series")
    p_ns.add_argument("--title", help="Display title")
    p_ns.add_argument("--universe", "-u", help="Target universe")
    p_ns.set_defaults(func=new_series)

    # cf new book
    p_nb = new_sub.add_parser("book", help="Scaffold a new book under a series")
    p_nb.add_argument("slug", help="Slug for the book")
    p_nb.add_argument("--title", help="Display title")
    p_nb.add_argument("--series", "-s", help="Target series")
    p_nb.add_argument("--universe", "-u", help="Target universe")
    p_nb.set_defaults(func=new_book)

    # cf new chapter
    p_nc = new_sub.add_parser("chapter", help="Scaffold a new chapter")
    p_nc.add_argument("--title", "-t", help="Chapter title")
    p_nc.add_argument("--book", "-b", help="Book directory or slug")
    p_nc.add_argument("--act", "-a", type=int, default=1, help="Act number")
    p_nc.add_argument("--pov", "-p", default="Protagonist", help="POV character")
    p_nc.add_argument("--setting", help="Setting description")
    p_nc.add_argument("--universe", "-u", help="Target universe")
    p_nc.set_defaults(func=new_chapter)

    # cf new character
    p_nch = new_sub.add_parser("character", help="Scaffold a new character profile")
    p_nch.add_argument("name", help="Character name")
    p_nch.add_argument("--faction", "-f", default="Independent", help="Faction")
    p_nch.add_argument("--role", "-r", default="Protagonist", help="Narrative role")
    p_nch.add_argument("--pov", action="store_true", default=True, help="Can hold POV")
    p_nch.add_argument("--universe", "-u", help="Target universe")
    p_nch.set_defaults(func=new_character)

    # cf new asset
    p_na = new_sub.add_parser("asset", help="Scaffold a new visual asset (map, concept, character art)")
    p_na.add_argument("name", help="Asset display name or slug")
    p_na.add_argument("--type", "-t", choices=["map", "concept", "character", "item", "place", "artwork"], default="concept", help="Asset category")
    p_na.add_argument("--file", "-f", help="Source image file to import")
    p_na.add_argument("--prompt", "-p", help="Generation prompt used")
    p_na.add_argument("--model", "-m", default="FLUX / Midjourney", help="Model used")
    p_na.add_argument("--lore", "-l", help="Wiki entity name/slug to link")
    p_na.add_argument("--notes", help="Usage notes")
    p_na.add_argument("--universe", "-u", help="Target universe")
    p_na.set_defaults(func=new_asset)

    # init alias to new universe
    p_init = subparsers.add_parser("init", aliases=["scaffold"], help="Initialize a new universe")
    p_init.add_argument("slug", help="Slug for the universe")
    p_init.add_argument("--title", help="Display title")
    p_init.add_argument("--genre", help="Genre")
    p_init.add_argument("--sensory-profile", help="Default sensory profile")
    p_init.set_defaults(func=new_universe)

    # 2. AUDITING
    p_audit = subparsers.add_parser("audit", help="Run multi-engine diagnostic audit")
    p_audit.add_argument("chapter", nargs="?", default="", help="Optional chapter markdown file")
    p_audit.add_argument("--book", "-b", help="Audit all chapters in specified book")
    p_audit.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p_audit.set_defaults(func=cmd_audit)

    p_review = subparsers.add_parser("review", help="Generate literary scorecard (/10)")
    p_review.add_argument("chapter", nargs="?", default="", help="Target chapter markdown file")
    p_review.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p_review.set_defaults(func=cmd_review)

    # Authoring & Linguistic Quality
    from canonforge.cli.authoring import cmd_thesaurus, cmd_sensory, cmd_pov, cmd_prose, cmd_polish

    p_thes = subparsers.add_parser("thesaurus", help="Query Sensory Knowledge Graph thesaurus")
    p_thes.add_argument("word", nargs="?", default="", help="Target sensory word or phrase")
    p_thes.add_argument("--theme", help="Filter by theme")
    p_thes.add_argument("--intensity", type=int, choices=[1, 2, 3], help="Filter by intensity (1-3)")
    p_thes.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p_thes.set_defaults(func=cmd_thesaurus)

    p_sen = subparsers.add_parser("sensory", help="Run 5-senses radar audit")
    p_sen.add_argument("chapter", nargs="?", default="", help="Target chapter markdown file")
    p_sen.add_argument("--show-windows", "-w", action="store_true", help="Show all 500-word windows")
    p_sen.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p_sen.set_defaults(func=cmd_sensory)

    p_pov = subparsers.add_parser("pov", help="Run Deep 3rd Limited POV audit")
    p_pov.add_argument("chapter", nargs="?", default="", help="Target chapter markdown file")
    p_pov.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p_pov.set_defaults(func=cmd_pov)

    p_prose = subparsers.add_parser("prose", help="Run anti-slop and filter word linter")
    p_prose.add_argument("chapter", nargs="?", default="", help="Target chapter markdown file")
    p_prose.add_argument("--verbose", "-v", action="store_true", help="Show all hits")
    p_prose.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p_prose.set_defaults(func=cmd_prose)

    p_pol = subparsers.add_parser("polish", help="Run single-pass unified literary reviewer")
    p_pol.add_argument("chapter", nargs="?", default="", help="Target chapter markdown file")
    p_pol.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p_pol.set_defaults(func=cmd_polish)

    # Narrative Impact Analyzer
    p_impact = subparsers.add_parser("impact", help="Analyze narrative blast radius and plot causality across all books")
    p_impact.add_argument("query", nargs="?", default="", help="Keyword, phrase, or plot point term")
    p_impact.add_argument("--keywords", "-k", nargs="*", default=[], help="Additional keywords to trace")
    p_impact.add_argument("--character", "-c", help="Target character name or ID to trace")
    p_impact.add_argument("--milestone", "-m", help="Target milestone ID to trace")
    p_impact.add_argument("--series", "-s", help="Filter to specific series slug")
    p_impact.add_argument("--book", "-b", help="Filter to specific book slug")
    p_impact.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p_impact.add_argument("--universe", "-u", help="Path to universe root")
    p_impact.set_defaults(func=_dispatch_impact)

    # Plot Consistency & Metadata Drift Linter
    p_cons = subparsers.add_parser("consistency", aliases=["lint", "lint-consistency"], help="Audit plot point metadata drift, ghost characters, and causal DAG")
    p_cons.add_argument("chapter", nargs="?", default="", help="Optional chapter file or pattern to audit")
    p_cons.add_argument("--book", "-b", help="Filter by book directory (e.g. book-01)")
    p_cons.add_argument("--series", "-s", help="Filter by series slug (e.g. sun-sanctum)")
    p_cons.add_argument("--strict", action="store_true", help="Fail on warnings as well as errors")
    p_cons.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    p_cons.add_argument("--universe", "-u", help="Path to universe root")
    p_cons.set_defaults(func=_dispatch_consistency)

    # 3. AGENT
    p_skill = subparsers.add_parser("skill", help="Export agent skills and governance rules")
    skill_sub = p_skill.add_subparsers(dest="skill_action", help="Skill action")

    p_sk_exp = skill_sub.add_parser("export", help="Export agent rules (.cursorrules, CLAUDE.md, SKILL.md)")
    p_sk_exp.add_argument("--target", choices=["cursor", "claude", "gemini", "agents", "all"], default="all")
    p_sk_exp.add_argument("--out-dir", "-o", help="Target directory for export")
    p_sk_exp.set_defaults(func=cmd_skill_export)

    p_sk_show = skill_sub.add_parser("show", help="Display active agent rules")
    p_sk_show.set_defaults(func=cmd_skill_show)

    return parser

def main():
    # If no arguments provided: render anti-deadend dashboard!
    if len(sys.argv) == 1:
        render_dashboard()
        return

    # If --help or -h passed at root: show grouped capability explorer
    if len(sys.argv) == 2 and sys.argv[1] in ("-h", "--help"):
        print_grouped_help()
        return

    # If --version or -V passed at root: show version
    if len(sys.argv) == 2 and sys.argv[1] in ("-V", "--version"):
        from canonforge import __version__
        print(f"canonforge {__version__}")
        return

    first_arg = sys.argv[1]

    # Obsidian integration command
    if first_arg == "obsidian":
        from canonforge.engines import obsidian
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        obsidian.main()
        return

    # Scan Unregistered Entities & Auto-Scaffold
    if first_arg == "scan":
        from canonforge.engines import scanner
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        scanner.main()
        return

    # Semantic Entity Wikilinker
    if first_arg == "link":
        from canonforge.engines import linker
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        linker.main()
        return

    # Git Pre-Commit Hook Manager
    if first_arg == "hook":
        from canonforge.engines import hooks
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        hooks.main()
        return

    # Search / Lore Query command
    if first_arg == "search":
        from canonforge.engines import search
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        search.main()
        return

    # Update Entity Dossier command
    if first_arg == "update":
        from canonforge.engines import updater
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        updater.main()
        return

    # Play Dialogue (alias to dialogue)
    if first_arg == "play":
        from canonforge.engines import dialogue
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        dialogue.main()
        return

    # Export / Publishing command (chapter, book, series)
    if first_arg == "export":
        from canonforge.engines.exporter import cli as exp_cli
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        exp_cli.main()
        return

    # Character Intelligence Dossier & Profiler
    if first_arg == "profile":
        from canonforge.engines import profile
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        profile.main()
        return

    # Visual Obsidian Canvas Generator
    if first_arg == "canvas":
        from canonforge.engines import canvas
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        canvas.main()
        return

    # Chapter Appearance & Mention Citation Indexer
    if first_arg == "appearances":
        from canonforge.engines import appearances
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        appearances.main()
        return

    # Universal Interactive Studio TUI
    if first_arg in ("studio", "interactive"):
        from canonforge.engines import interactive
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        interactive.main()
        return

    # Narrative Impact command
    if first_arg == "impact":
        from canonforge.engines import impact
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        impact.main()
        return

    # Global Rename command
    if first_arg == "rename":
        from canonforge.engines import rename
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        rename.main()
        return

    # Plot Consistency & Drift Linter command
    if first_arg in ("consistency", "lint", "lint-consistency"):
        from canonforge.engines import consistency
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        consistency.main()
        return

    # Direct engine delegations
    if first_arg == "combat":
        from canonforge.engines.combat import cli as combat_cli
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        combat_cli.main()
        return

    if first_arg == "travel":
        from canonforge.engines import travel
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        travel.main()
        return

    if first_arg == "prep":
        from canonforge.engines.prep import cli as prep_cli
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        prep_cli.main()
        return

    if first_arg in ("dialogue", "play"):
        from canonforge.engines import dialogue
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        dialogue.main()
        return

    if first_arg == "continuity":
        from canonforge.engines import continuity
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        continuity.main()
        return

    if first_arg == "timeline":
        from canonforge.engines import timeline
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        timeline.main()
        return

    if first_arg == "secrets":
        from canonforge.engines import secrets
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        secrets.main()
        return

    if first_arg == "relations":
        from canonforge.engines.relations import cli as rel_cli
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        rel_cli.main()
        return

    if first_arg in ("db", "lore"):
        from canonforge.engines import sync_db
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        sync_db.main()
        return

    if first_arg == "compile":
        from canonforge.engines.compiler import cli as comp_cli
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        comp_cli.main()
        return

    if first_arg == "metrics":
        from canonforge.engines.metrics import cli as metrics_cli
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        metrics_cli.main()
        return

    # Check for unknown command typo
    valid_cmds = _get_all_valid_commands()
    if not first_arg.startswith("-") and first_arg not in valid_cmds:
        suggest_similar_command(first_arg, valid_cmds)
        sys.exit(1)

    parser = build_parser()
    args, unknown = parser.parse_known_args()

    if getattr(args, "func", None):
        args.func(args)
    elif args.subcommand == "new" and not getattr(args, "new_type", None):
        print("\nUsage: cf new <universe|series|book|chapter|character> [options]")
        print("Run 'cf new --help' or 'cf new chapter --help' for details.\n")
    elif args.subcommand == "skill" and not getattr(args, "skill_action", None):
        print("\nUsage: cf skill <export|show> [options]")
        print("Run 'cf skill export --help' for details.\n")
    else:
        render_dashboard()

if __name__ == "__main__":
    main()
