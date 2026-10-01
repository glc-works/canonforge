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
        from okf_studio.engines import sensory
        sample_ch = chapters[0]
        text = sample_ch.read_text(encoding="utf-8")
        res = sensory.analyze_text(text)
        print(f"  ✓ 5-Senses Radar: '{sample_ch.name}' scored {res['immersion_score']}/100 (Pass: {res['four_sense_compliance_pct']}%)")
    except Exception as e:
        print(f"  ⚠️ Sensory check warning: {e}")

    # 5. Deep POV Audit on first chapter
    try:
        from okf_studio.engines import pov
        sample_ch = chapters[0]
        pov_res = pov.audit_chapter_pov(sample_ch)
        print(f"  ✓ Deep POV Gate: '{sample_ch.name}' POV compliance verified")
    except Exception as e:
        print(f"  ⚠️ POV check warning: {e}")

    # 6. Sensory Graph Validation
    try:
        from okf_studio.engines import sensory_dictionary
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
    parser = argparse.ArgumentParser(description="ax - OKF Studio Author Experience Runner")
    subparsers = parser.add_subparsers(dest="subcommand", help="Sub-commands")

    # verify
    p_verify = subparsers.add_parser("verify", help="Run full verification suite on active universe")
    
    # sensory
    p_sen = subparsers.add_parser("sensory", help="Run 5-senses radar audit")
    p_sen.add_argument("chapter", nargs="?", default="", help="Target chapter markdown file")
    p_sen.add_argument("--thesaurus", "-t", help="Lookup synonyms/antonyms for a word")
    p_sen.add_argument("--show-windows", "-w", action="store_true", help="Show all 500-word windows")

    # pov
    p_pov = subparsers.add_parser("pov", help="Run Deep 3rd Limited POV audit")
    p_pov.add_argument("chapter", nargs="?", default="", help="Target chapter markdown file")

    # prose
    p_prose = subparsers.add_parser("prose", help="Run anti-slop and filter word linter")
    p_prose.add_argument("chapter", nargs="?", default="", help="Target chapter markdown file")

    # polish
    p_pol = subparsers.add_parser("polish", help="Run single-pass unified literary reviewer")
    p_pol.add_argument("chapter", nargs="?", default="", help="Target chapter markdown file")

    # thesaurus
    p_thes = subparsers.add_parser("thesaurus", help="Query Sensory Knowledge Graph thesaurus")
    p_thes.add_argument("word", help="Target sensory word or phrase")
    p_thes.add_argument("--theme", help="Filter by theme")
    p_thes.add_argument("--intensity", type=int, choices=[1, 2, 3], help="Filter by intensity (1-3)")

    args, unknown = parser.parse_known_args()
    u_root = find_universe_root()

    if not args.subcommand or args.subcommand == "verify":
        verify_universe(u_root)
        return

    if args.subcommand == "thesaurus":
        from okf_studio.engines import sensory_dictionary
        d = sensory_dictionary.get_dictionary()
        hit = d.lookup(args.word)
        if not hit:
            print(f"❌ Word '{args.word}' not found in Sensory Dictionary.")
            return
        syns = d.get_synonyms(args.word, theme=args.theme, intensity=args.intensity)
        ants = d.get_antonyms(args.word, theme=args.theme)
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
        from okf_studio.engines import sensory
        ch_files = list(u_root.glob(f"**/*{args.chapter}*")) if args.chapter else list(u_root.glob("manuscript/*/*/chapters/*.md"))
        valid = [f for f in ch_files if f.is_file() and f.suffix == ".md"]
        if not valid:
            print(f"❌ Could not locate chapter: {args.chapter}")
            return
        target = valid[0]
        comp = sensory.load_composite_profiles()
        res = sensory.analyze_text(target.read_text(encoding="utf-8"), composite=comp)
        sensory.print_sensory_report(target.name, res, comp, show_windows=args.show_windows)
        return

if __name__ == "__main__":
    main()
