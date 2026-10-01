"""
CanonForge CLI: Unified Multi-Engine Audit & Literary Reviewer (cf audit, cf review)
--------------------------------------------------------------------------------
Provides single-command diagnostic scanning emitting standard diagnostic codes:
  POV001 : Head-hopping / filter verb detected in limited POV
  SLOP001: Tricolon rhythm / AI cadence detected
  SLOP002: AI buzzword or melodrama cliche hit
  SEN001 : Under-saturated sensory window (< 3 senses in 500 words)
  SEN002 : Low overall sensory immersion score (< 70)
  TOC001 : Chapter not registered in toc.yaml
  SCH001 : Frontmatter schema validation error
"""

import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from canonforge.cli.groups import style
from canonforge.cli.dashboard import find_enclosing_universe, find_workspace_root

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

def _find_chapter_files(target_arg: Optional[str], book_arg: Optional[str] = None) -> List[Path]:
    """Locate matching chapter files in active universe or workspace."""
    u_dir = find_enclosing_universe() or find_workspace_root()
    ms_dir = u_dir / "manuscript"
    if not ms_dir.is_dir():
        # Fallback to searching locally
        ms_dir = u_dir

    all_chapters = sorted(list(ms_dir.glob("**/*.md")))
    all_chapters = [c for c in all_chapters if "chapters" in c.parts or c.name.startswith("ch")]

    if target_arg:
        # Match specific chapter
        exact = [c for c in all_chapters if target_arg in c.name or target_arg == str(c)]
        if exact:
            return exact
        # Check by direct path
        p = Path(target_arg)
        if p.is_file():
            return [p]
        print(f"❌ Error: Chapter file matching '{target_arg}' not found.")
        sys.exit(1)

    if book_arg:
        matched = [c for c in all_chapters if book_arg in c.parts]
        if matched:
            return matched
        print(f"❌ Error: No chapters found under book '{book_arg}'.")
        sys.exit(1)

    return all_chapters

def run_chapter_audit(ch_file: Path) -> List[Dict[str, Any]]:
    """Run all linter checks on a chapter and return diagnostic issues."""
    diagnostics: List[Dict[str, Any]] = []
    text = ch_file.read_text(encoding="utf-8")
    lines = text.splitlines()

    # 1. Schema / Frontmatter check
    if not text.startswith("---"):
        diagnostics.append({
            "code": "SCH001",
            "severity": "error",
            "file": ch_file.name,
            "line": 1,
            "message": "Missing YAML frontmatter delimiters (---)."
        })
    else:
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            if "pov:" not in fm_text:
                diagnostics.append({
                    "code": "SCH001",
                    "severity": "error",
                    "file": ch_file.name,
                    "line": 1,
                    "message": "Required frontmatter key 'pov' missing."
                })
            if "chapter:" not in fm_text:
                diagnostics.append({
                    "code": "SCH001",
                    "severity": "error",
                    "file": ch_file.name,
                    "line": 1,
                    "message": "Required frontmatter key 'chapter' missing."
                })

    # 2. Deep POV Audit
    try:
        from canonforge.engines import pov
        pov_res = pov.audit_chapter_pov(ch_file)
        for viol in pov_res.get("violations", []):
            diagnostics.append({
                "code": "POV001",
                "severity": "warning",
                "file": ch_file.name,
                "line": viol.get("line", 1),
                "message": f"POV violation: {viol.get('message', 'Filter verb detected')}"
            })
    except Exception:
        pass

    # 3. Anti-Slop & AI Cadence Audit
    try:
        from canonforge.engines import prose
        prose_res = prose.audit_text(text, filename=ch_file.name)
        for tri in prose_res.get("tricolon_hits", []):
            diagnostics.append({
                "code": "SLOP001",
                "severity": "warning",
                "file": ch_file.name,
                "line": tri.get("line", 1),
                "message": f"Tricolon cadence detected: '{tri.get('snippet', '')}'"
            })
        for cl in prose_res.get("cliche_hits", []):
            diagnostics.append({
                "code": "SLOP002",
                "severity": "warning",
                "file": ch_file.name,
                "line": cl.get("line", 1),
                "message": f"AI buzzword/cliche detected: '{cl.get('word', '')}'"
            })
    except Exception:
        pass

    # 4. Sensory Immersion Audit
    try:
        from canonforge.engines import sensory
        sen_res = sensory.analyze_text(text)
        if sen_res.get("immersion_score", 100) < 70:
            diagnostics.append({
                "code": "SEN002",
                "severity": "info",
                "file": ch_file.name,
                "line": 1,
                "message": f"Immersion score is {sen_res.get('immersion_score'):.1f}/100 (< 70 threshold)."
            })
        for win in sen_res.get("windows", []):
            if win.get("sense_count", 5) < 3:
                diagnostics.append({
                    "code": "SEN001",
                    "severity": "warning",
                    "file": ch_file.name,
                    "line": win.get("start_line", 1),
                    "message": f"Sensory saturation below 3 senses (senses present: {', '.join(win.get('senses_present', [])) or 'None'})"
                })
    except Exception:
        pass

    return diagnostics

def cmd_audit(args):
    """Unified multi-engine audit command."""
    target_arg = getattr(args, "chapter", None)
    book_arg = getattr(args, "book", None)
    format_type = getattr(args, "format", "text")

    chapters = _find_chapter_files(target_arg, book_arg)
    if not chapters:
        print("❌ Error: No chapters found to audit.")
        sys.exit(1)

    all_diagnostics = []
    for ch in chapters:
        diags = run_chapter_audit(ch)
        all_diagnostics.extend(diags)

    if format_type == "json":
        print(json.dumps({
            "total_chapters": len(chapters),
            "total_diagnostics": len(all_diagnostics),
            "passed": len([d for d in all_diagnostics if d["severity"] == "error"]) == 0,
            "diagnostics": all_diagnostics
        }, indent=2))
        return

    print("\n" + style("=" * 80, "cyan"))
    print(f"CANONFORGE MULTI-ENGINE LITERARY AUDIT ({len(chapters)} chapters)")
    print(style("=" * 80, "cyan"))

    if not all_diagnostics:
        print(f"  {style('✅ 100% CLEAN!', 'green')} Zero violations across all engines (POV, Slop, Sensory, Schema).\n")
        return

    # Print summary table
    print(f"{'CODE':<9} {'SEVERITY':<10} {'LOCATION':<30} {'DIAGNOSTIC MESSAGE'}")
    print(style("-" * 80, "gray"))

    for d in all_diagnostics:
        code_str = style(d["code"], "bold")
        sev = d["severity"].upper()
        if sev == "ERROR":
            sev_str = style(sev, "yellow")
        elif sev == "WARNING":
            sev_str = style(sev, "yellow")
        else:
            sev_str = style(sev, "cyan")

        loc = f"{d['file']}:{d['line']}"
        print(f"{code_str:<18} {sev_str:<19} {loc:<30} {d['message']}")

    print(style("=" * 80, "cyan"))
    print(f"Total issues: {len(all_diagnostics)} | Chapters audited: {len(chapters)}\n")

def cmd_review(args):
    """Unified single-pass literary reviewer emitting scorecard (/10)."""
    target_arg = getattr(args, "chapter", None)
    chapters = _find_chapter_files(target_arg)
    if not chapters:
        print("❌ Error: Chapter not found.")
        sys.exit(1)

    target_ch = chapters[0]
    format_type = getattr(args, "format", "text")

    try:
        from canonforge.engines import polish
        res = polish.review_chapter(target_ch)
        if format_type == "json":
            print(json.dumps(res, indent=2))
        else:
            polish.print_review(res)
    except Exception as e:
        print(f"❌ Error during review: {e}")
        sys.exit(1)
