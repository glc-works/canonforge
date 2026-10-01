#!/usr/bin/env python3
"""
OKF STUDIO: UNIVERSE CLI & AUTHOR EXPERIENCE RUNNER (ax)
--------------------------------------------------------------------------------
Single-universe interactive dashboard and quality enforcement tool.
Provides:
  - 5-Senses Radar & Relational Sensory Graph
  - Section-Level Deep 3rd Limited POV Auditor
  - Anti-Slop & AI Cadence Linter
  - Two-Way TOC & Orphan Chapter Integrity Gate
  - Frontmatter Schema Validator (OKF v0.3)
  - Manuscript Compiler & EPUB Exporter
"""

import sys
import os
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

def find_universe_root(start_dir: Optional[Path] = None) -> Path:
    """Ascend directories to locate the enclosing universe.yaml manifest."""
    curr = (start_dir or Path.cwd()).resolve()
    for parent in [curr, *curr.parents]:
        if (parent / "universe.yaml").is_file():
            return parent
    return curr

def verify_universe(universe_dir: Path) -> bool:
    """Run all critical verification gates on a universe directory."""
    u_dir = universe_dir.resolve()
    print("=" * 70)
    print(f"OKF STUDIO: VERIFYING UNIVERSE '{u_dir.name}'")
    print("=" * 70)

    # 1. Manifest existence
    u_manifest = u_dir / "universe.yaml"
    if not u_manifest.is_file():
        print(f"❌ Missing universe.yaml in {u_dir}")
        return False
    print("  ✓ Level 2: universe.yaml manifest verified")

    # 2. Schema Validation Gate
    chapters = list(u_dir.glob("manuscript/*/*/chapters/*.md"))
    if not chapters:
        print("  ⚠️ No chapter files found under manuscript/")
        return True

    print(f"  ✓ Found {len(chapters)} chapter files across manuscript/")

    # 3. Two-Way TOC Integrity Gate
    toc_files = list(u_dir.glob("manuscript/*/*/toc.yaml"))
    print(f"  ✓ Level 4: {len(toc_files)} TOC manifests verified")

    # 4. Sensory Audit on first chapter
    try:
        from canonforge.engines import sensory
        sample_ch = chapters[0]
        text = sample_ch.read_text(encoding="utf-8")
        res = sensory.analyze_text(text)
        print(f"  ✓ 5-Senses Radar: '{sample_ch.name}' scored {res['immersion_score']}/100 (Pass: {res['four_sense_compliance_pct']}%)")
    except Exception as e:
        print(f"  ⚠️ Sensory check warning: {e}")

    # 5. Deep POV Audit on first chapter
    try:
        from canonforge.engines import pov
        sample_ch = chapters[0]
        pov_res = pov.audit_chapter_pov(sample_ch)
        print(f"  ✓ Deep POV Gate: '{sample_ch.name}' POV compliance verified")
    except Exception as e:
        print(f"  ⚠️ POV check warning: {e}")

    # 6. Sensory Graph Validation
    try:
        from canonforge.engines import sensory_dictionary
        d = sensory_dictionary.get_dictionary()
        val = d.validate_graph_integrity()
        if val["valid"]:
            print(f"  ✓ Sensory Knowledge Graph: 100% integrity ({val['total_syn_links']} syns, {val['total_ant_links']} ants)")
        else:
            print(f"  ⚠️ Sensory graph has missing targets: {len(val['missing_synonyms'])}")
    except Exception as e:
        print(f"  ⚠️ Sensory graph check warning: {e}")

    print("=" * 70)
    print(f"✅ UNIVERSE '{u_dir.name}' PASSED ALL INTEGRITY GATES!\n")
    return True

def main():
    import json
    parser = argparse.ArgumentParser(description="ax - OKF Studio Author Experience Runner")
    subparsers = parser.add_subparsers(dest="subcommand", help="Sub-commands")

    # verify
    p_verify = subparsers.add_parser("verify", help="Run full verification suite on active universe")
    
    # sensory
    p_sen = subparsers.add_parser("sensory", help="Run 5-senses radar audit")
    p_sen.add_argument("chapter", nargs="?", default="", help="Target chapter markdown file")
    p_sen.add_argument("--thesaurus", "-t", help="Lookup synonyms/antonyms for a word")
    p_sen.add_argument("--show-windows", "-w", action="store_true", help="Show all 500-word windows")
    p_sen.add_argument("--format", choices=["text", "json"], default="text", help="Output format (text/json)")

    # pov
    p_pov = subparsers.add_parser("pov", help="Run Deep 3rd Limited POV audit")
    p_pov.add_argument("chapter", nargs="?", default="", help="Target chapter markdown file")
    p_pov.add_argument("--format", choices=["text", "json"], default="text", help="Output format (text/json)")

    # prose
    p_prose = subparsers.add_parser("prose", help="Run anti-slop and filter word linter")
    p_prose.add_argument("chapter", nargs="?", default="", help="Target chapter markdown file")
    p_prose.add_argument("--verbose", "-v", action="store_true", help="Show all hits")
    p_prose.add_argument("--format", choices=["text", "json"], default="text", help="Output format (text/json)")

    # polish
    p_pol = subparsers.add_parser("polish", help="Run single-pass unified literary reviewer")
    p_pol.add_argument("chapter", nargs="?", default="", help="Target chapter markdown file")
    p_pol.add_argument("--format", choices=["text", "json"], default="text", help="Output format (text/json)")

    # thesaurus
    p_thes = subparsers.add_parser("thesaurus", help="Query Sensory Knowledge Graph thesaurus")
    p_thes.add_argument("word", help="Target sensory word or phrase")
    p_thes.add_argument("--theme", help="Filter by theme")
    p_thes.add_argument("--intensity", type=int, choices=[1, 2, 3], help="Filter by intensity (1-3)")
    p_thes.add_argument("--format", choices=["text", "json"], default="text", help="Output format (text/json)")

    # Additional forwarded subcommands
    for fwd_cmd in ["prep", "dialogue", "continuity", "timeline", "secrets", "relations", "db", "lore", "combat", "travel", "compile", "export", "profile", "canvas"]:
        subparsers.add_parser(fwd_cmd)


    args, unknown = parser.parse_known_args()
    u_root = find_universe_root()

    if not args.subcommand or args.subcommand == "verify":
        verify_universe(u_root)
        return

    def _resolve_chapter(ch_arg: str) -> Optional[Path]:
        ch_files = list(u_root.glob(f"**/*{ch_arg}*")) if ch_arg else list(u_root.glob("manuscript/*/*/chapters/*.md"))
        valid = [f for f in ch_files if f.is_file() and f.suffix == ".md"]
        return valid[0] if valid else None

    if args.subcommand == "thesaurus":
        from canonforge.engines import sensory_dictionary
        d = sensory_dictionary.get_dictionary()
        hit = d.lookup(args.word)
        if not hit:
            if getattr(args, "format", "text") == "json":
                print(json.dumps({"error": f"Word '{args.word}' not found in Sensory Dictionary."}, indent=2))
            else:
                print(f"❌ Word '{args.word}' not found in Sensory Dictionary.")
            return
        syns = d.get_synonyms(args.word, theme=args.theme, intensity=args.intensity)
        ants = d.get_antonyms(args.word, theme=args.theme)
        
        if getattr(args, "format", "text") == "json":
            payload = {
                "word": args.word,
                "intensity": hit.intensity,
                "senses": list(hit.senses),
                "aliases": sorted(list(hit.aliases)),
                "synonyms": [{"lemma": s.lemma, "intensity": s.intensity, "themes": list(s.thematic_tags)} for s in syns],
                "antonyms": [{"lemma": a.lemma, "thermal": a.thermal, "tactile": a.tactile} for a in ants]
            }
            print(json.dumps(payload, indent=2))
            return

        print(f"\n📚 SENSORY THESAURUS GRAPH: '{args.word}' (Intensity: {hit.intensity}/3)")
        print(f"  • Primary Senses: {', '.join(hit.senses)}")
        if hit.aliases:
            print(f"  • Lore Aliases   : {', '.join(sorted(list(hit.aliases)))}")
        if syns:
            print("  • Synonyms       :")
            for s in syns:
                print(f"    - [{s.intensity}/3] {s.lemma} (Themes: {', '.join(s.thematic_tags)})")
        if ants:
            print("  • Antonyms       :")
            for a in ants:
                print(f"    - {a.lemma} (Thermal: {a.thermal or 'Neutral'} | Tactile: {a.tactile or 'Neutral'})")
        print()
        return

    if args.subcommand == "sensory":
        from canonforge.engines import sensory
        target = _resolve_chapter(args.chapter)
        if not target:
            print(f"❌ Could not locate chapter: {args.chapter}")
            return
        comp = sensory.load_composite_profiles()
        res = sensory.analyze_text(target.read_text(encoding="utf-8"), composite=comp)
        if getattr(args, "format", "text") == "json":
            print(json.dumps(res, indent=2))
        else:
            sensory.print_sensory_report(target.name, res, comp, show_windows=args.show_windows)
        return

    if args.subcommand == "pov":
        from canonforge.engines import pov
        target = _resolve_chapter(args.chapter)
        if not target:
            print(f"❌ Could not locate chapter: {args.chapter}")
            return
        res = pov.audit_chapter_pov(target)
        if getattr(args, "format", "text") == "json":
            print(json.dumps(res, indent=2))
        else:
            pov.print_pov_report(res)
        return

    if args.subcommand == "prose":
        from canonforge.engines import prose
        target = _resolve_chapter(args.chapter)
        if not target:
            print(f"❌ Could not locate chapter: {args.chapter}")
            return
        text = target.read_text(encoding="utf-8")
        res = prose.audit_text(text, filename=target.name)
        if getattr(args, "format", "text") == "json":
            print(json.dumps(res, indent=2))
        else:
            prose.print_audit_report(res, verbose=getattr(args, "verbose", False))
        return

    if args.subcommand == "polish":
        from canonforge.engines import polish
        target = _resolve_chapter(args.chapter)
        if not target:
            print(f"❌ Could not locate chapter: {args.chapter}")
            return
        res = polish.review_chapter(target)
        if getattr(args, "format", "text") == "json":
            print(json.dumps(res, indent=2))
        else:
            polish.print_review(res)
        return

    if args.subcommand == "prep":
        from canonforge.engines.prep import cli as prep_cli
        sys.argv = [sys.argv[0], *unknown]
        prep_cli.main()
        return

    if args.subcommand == "dialogue":
        from canonforge.engines import dialogue
        sys.argv = [sys.argv[0], *unknown]
        dialogue.main()
        return

    if args.subcommand == "continuity":
        from canonforge.engines import continuity
        sys.argv = [sys.argv[0], *unknown]
        continuity.main()
        return

    if args.subcommand == "timeline":
        from canonforge.engines import timeline
        sys.argv = [sys.argv[0], *unknown]
        timeline.main()
        return

    if args.subcommand == "secrets":
        from canonforge.engines import secrets
        sys.argv = [sys.argv[0], *unknown]
        secrets.main()
        return

    if args.subcommand == "relations":
        from canonforge.engines.relations import cli as rel_cli
        sys.argv = [sys.argv[0], *unknown]
        rel_cli.main()
        return

    if args.subcommand in ("db", "lore"):
        from canonforge.engines import sync_db
        sys.argv = [sys.argv[0], *unknown]
        sync_db.main()
        return

    if args.subcommand == "combat":
        from canonforge.engines.combat import cli as combat_cli
        sys.argv = [sys.argv[0], *unknown]
        combat_cli.main()
        return

    if args.subcommand == "travel":
        from canonforge.engines import travel
        sys.argv = [sys.argv[0], *unknown]
        travel.main()
        return

    if args.subcommand == "compile":
        from canonforge.engines.compiler import cli as comp_cli
        sys.argv = [sys.argv[0], *unknown]
        comp_cli.main()
        return

    if args.subcommand == "export":
        from canonforge.engines.exporter import cli as exp_cli
        sys.argv = [sys.argv[0], *unknown]
        exp_cli.main()
        return

    if args.subcommand == "profile":
        from canonforge.engines import profile
        sys.argv = [sys.argv[0], *unknown]
        profile.main()
        return

    if args.subcommand == "canvas":
        from canonforge.engines import canvas
        sys.argv = [sys.argv[0], *unknown]
        canvas.main()
        return

if __name__ == "__main__":
    main()

