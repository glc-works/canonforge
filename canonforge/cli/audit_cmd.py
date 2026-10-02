"""
CanonForge CLI: Unified Multi-Engine Audit & Literary Reviewer (cf audit, cf review)
--------------------------------------------------------------------------------
Provides intuitive, writer-friendly diagnostic scanning with inline prose snippets
and concrete editorial suggestions across POV, AI Cadence, Sensory, and Plot gates.
"""

import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from canonforge.cli.groups import style
from canonforge.cli.dashboard import find_enclosing_universe, find_workspace_root
from canonforge.core.resolver import resolve_chapter, get_all_chapters, get_active_draft


def _find_chapter_files(
    target_arg: Optional[str] = None,
    book_arg: Optional[str] = None,
    audit_all: bool = False
) -> List[Path]:
    """Locate matching chapter files using smart shorthand or active draft."""
    u_dir = find_enclosing_universe() or find_workspace_root()

    if target_arg:
        resolved = resolve_chapter(target_arg, universe_dir=u_dir, book_filter=book_arg)
        if resolved:
            return [resolved]
        print(f"❌ Error: Chapter matching '{target_arg}' not found.")
        sys.exit(1)

    if book_arg:
        chapters = get_all_chapters(u_dir, book_filter=book_arg)
        if chapters:
            return chapters
        print(f"❌ Error: No chapters found under book '{book_arg}'.")
        sys.exit(1)

    if audit_all:
        return get_all_chapters(u_dir)

    # Default to active draft if no argument given
    active = get_active_draft(u_dir)
    return [active] if active else get_all_chapters(u_dir)


def run_chapter_audit(ch_file: Path) -> List[Dict[str, Any]]:
    """Run all linter checks on a chapter and return diagnostic issues with snippets and suggestions."""
    diagnostics: List[Dict[str, Any]] = []
    text = ch_file.read_text(encoding="utf-8")
    lines = text.splitlines()

    def get_line_snippet(line_no: int) -> str:
        if 1 <= line_no <= len(lines):
            return lines[line_no - 1].strip()
        return ""

    # 1. Schema / Frontmatter check
    if not text.startswith("---"):
        diagnostics.append({
            "code": "SCH001",
            "severity": "error",
            "file": ch_file.name,
            "line": 1,
            "snippet": lines[0] if lines else "",
            "message": "Missing YAML frontmatter delimiters (---).",
            "suggestion": "Add YAML frontmatter with chapter title, act number, and primary POV."
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
                    "snippet": "---",
                    "message": "Required frontmatter key 'pov' missing.",
                    "suggestion": "Declare 'pov: CharacterName' in chapter frontmatter."
                })
            if "chapter:" not in fm_text:
                diagnostics.append({
                    "code": "SCH001",
                    "severity": "error",
                    "file": ch_file.name,
                    "line": 1,
                    "snippet": "---",
                    "message": "Required frontmatter key 'chapter' missing.",
                    "suggestion": "Declare 'chapter: <number>' in chapter frontmatter."
                })

    # 2. Deep POV Audit
    try:
        from canonforge.engines import pov
        pov_res = pov.audit_chapter_pov(ch_file)
        for viol in pov_res.get("violations", []):
            line_no = viol.get("line", 1)
            diagnostics.append({
                "code": "POV001",
                "severity": "warning",
                "file": ch_file.name,
                "line": line_no,
                "snippet": viol.get("text", get_line_snippet(line_no)),
                "message": f"POV violation: {viol.get('intruder', 'Non-POV')} interiority detected in {viol.get('pov', 'Primary')}'s POV.",
                "suggestion": viol.get("advice", "Externalize emotion: describe involuntary physical reactions instead of direct interiority.")
            })
    except Exception:
        pass

    # 3. Anti-Slop & AI Cadence Audit
    try:
        from canonforge.engines import prose
        prose_res = prose.audit_text(text, filename=ch_file.name)
        for tri in prose_res.get("tricolon_hits", []):
            line_no = tri.get("line", 1)
            diagnostics.append({
                "code": "SLOP001",
                "severity": "warning",
                "file": ch_file.name,
                "line": line_no,
                "snippet": tri.get("context", get_line_snippet(line_no)),
                "message": f"Tricolon cadence detected: '{tri.get('snippet', '')}'",
                "suggestion": "Break symmetrical three-part sentence into varied sentence lengths."
            })
        for cl in prose_res.get("cliche_hits", []):
            line_no = cl.get("line", 1)
            matched_term = cl.get("matched") or cl.get("label") or "cliche"
            diagnostics.append({
                "code": "SLOP002",
                "severity": "warning",
                "file": ch_file.name,
                "line": line_no,
                "snippet": cl.get("context", get_line_snippet(line_no)),
                "message": f"AI buzzword / melodrama cliché detected: '{matched_term}'",
                "suggestion": cl.get("explanation", "Replace generic melodrama cliché with concrete tactile physical detail.")
            })
        for fl in prose_res.get("filter_hits", []):
            line_no = fl.get("line", 1)
            diagnostics.append({
                "code": "POV002",
                "severity": "info",
                "file": ch_file.name,
                "line": line_no,
                "snippet": fl.get("context", get_line_snippet(line_no)),
                "message": f"Filter verb detected: '{fl.get('matched', '')}' ({fl.get('label', '')})",
                "suggestion": fl.get("tip", "Replace filtered observation with direct sensory prose.")
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
                "snippet": "",
                "message": f"Immersion score is {sen_res.get('immersion_score'):.1f}/100 (< 70 threshold).",
                "suggestion": "Incorporate taste, smell, and tactile temperature into quieter narrative transitions."
            })
        for win in sen_res.get("windows", []):
            if win.get("sense_count", 5) < 3:
                line_no = win.get("start_line", 1)
                diagnostics.append({
                    "code": "SEN001",
                    "severity": "warning",
                    "file": ch_file.name,
                    "line": line_no,
                    "snippet": get_line_snippet(line_no),
                    "message": f"Sensory saturation below 3 senses in 500-word window (senses: {', '.join(win.get('senses_present', [])) or 'None'})",
                    "suggestion": "Add missing sensory anchors (temperature, smell of wood/slate, tactile friction) to ground the scene."
                })
    except Exception:
        pass

    # 5. Plot Consistency & Drift Audit
    try:
        from canonforge.engines import consistency
        from canonforge.core.manifest import find_universe_root
        u_root = find_universe_root()
        alias_map = consistency.load_character_alias_map(u_root)
        c_diags = consistency.audit_chapter_consistency(ch_file, alias_map=alias_map)
        for cd in c_diags:
            line_no = cd.get("line", 1)
            cd["snippet"] = get_line_snippet(line_no)
            cd["suggestion"] = "Verify character presence against chapter outline and frontmatter cast."
        diagnostics.extend(c_diags)
    except Exception:
        pass

    # 6. Obsidian Wikilink & Entity Alias Integrity Audit
    try:
        from canonforge.core.entities import validate_chapter_wikilinks
        link_diags = validate_chapter_wikilinks(ch_file)
        diagnostics.extend(link_diags)
    except Exception:
        pass

    return diagnostics


def _render_rich_editorial_card(ch_name: str, diags: List[Dict[str, Any]]) -> str:
    """Render a human-friendly editorial review card with snippets and actionable tips."""
    output = []
    output.append("\n" + style("╔" + "═" * 78 + "╗", "cyan"))
    output.append(f"{style('║', 'cyan')}  {style('CANONFORGE EDITORIAL INSPECTION:', 'bold')} {ch_name:<41} {style('║', 'cyan')}")
    output.append(style("╚" + "═" * 78 + "╝", "cyan"))

    if not diags:
        output.append(f"\n  {style('🎉 100% CLEAN!', 'green')} No POV leaks, slop cadences, or schema defects detected.\n")
        return "\n".join(output)

    output.append(f"\nFound {len(diags)} actionable editorial improvement point(s):\n")

    for idx, d in enumerate(diags, start=1):
        sev = d["severity"].upper()
        badge_color = "yellow" if sev in ("WARNING", "ERROR") else "cyan"
        badge = style(f"[{d['code']}] {sev}", badge_color)
        loc = style(f"Line {d['line']}", "bold")

        output.append(f"  {style(f'#{idx}', 'gray')} {badge} at {loc}:")
        output.append(f"     {d['message']}")

        if d.get("snippet"):
            snip = d["snippet"]
            if len(snip) > 90:
                snip = snip[:87] + "..."
            output.append(f"     {style('│', 'gray')} {style(snip, 'gray')}")

        if d.get("suggestion"):
            output.append(f"     {style('💡 Suggestion:', 'bold')} {d['suggestion']}")
        output.append("")

    return "\n".join(output)


def cmd_audit(args):
    """Unified multi-engine audit command."""
    target_arg = getattr(args, "chapter", None)
    book_arg = getattr(args, "book", None)
    audit_all = getattr(args, "all", False)
    format_type = getattr(args, "format", "text")
    export_path = getattr(args, "export", None)
    verbose = getattr(args, "verbose", False)

    chapters = _find_chapter_files(target_arg, book_arg=book_arg, audit_all=audit_all)
    if not chapters:
        print("❌ Error: No chapters found to audit.")
        sys.exit(1)

    all_diagnostics = []
    chapter_results = {}
    for ch in chapters:
        diags = run_chapter_audit(ch)
        all_diagnostics.extend(diags)
        chapter_results[ch.name] = diags

    if format_type == "json":
        print(json.dumps({
            "total_chapters": len(chapters),
            "total_diagnostics": len(all_diagnostics),
            "passed": len([d for d in all_diagnostics if d["severity"] == "error"]) == 0,
            "diagnostics": all_diagnostics
        }, indent=2))
        return

    # Single chapter inspection: Rich Editorial Card
    if len(chapters) == 1:
        ch_name = chapters[0].name
        report_str = _render_rich_editorial_card(ch_name, all_diagnostics)
        print(report_str)

        if export_path:
            p_out = Path(export_path)
            clean_text = re.sub(r"\033\[[0-9;]*m", "", report_str)
            p_out.write_text(clean_text, encoding="utf-8")
            print(f"📄 Editorial report exported to: {p_out.resolve()}\n")
        return

    # Multi-chapter inspection: Summary Table
    print("\n" + style("=" * 80, "cyan"))
    print(f"CANONFORGE MULTI-ENGINE LITERARY AUDIT ({len(chapters)} chapters)")
    print(style("=" * 80, "cyan"))

    if not all_diagnostics:
        print(f"  {style('✅ 100% CLEAN!', 'green')} Zero violations across all chapters.\n")
        return

    print(f"{'CODE':<9} {'SEVERITY':<10} {'LOCATION':<32} {'DIAGNOSTIC MESSAGE'}")
    print(style("-" * 80, "gray"))

    for d in all_diagnostics:
        code_str = style(d["code"], "bold")
        sev = d["severity"].upper()
        sev_str = style(sev, "yellow" if sev in ("ERROR", "WARNING") else "cyan")
        loc = f"{d['file']}:{d['line']}"
        print(f"{code_str:<18} {sev_str:<19} {loc:<32} {d['message']}")

    print(style("=" * 80, "cyan"))
    print(f"Total issues: {len(all_diagnostics)} | Chapters audited: {len(chapters)}")
    print(f"💡 Tip: Run 'cf audit <chapter>' to view inline prose snippets and rewrite tips.\n")

    if export_path:
        p_out = Path(export_path)
        lines = [f"# CanonForge Audit Report ({len(chapters)} chapters)\n"]
        for d in all_diagnostics:
            lines.append(f"- **[{d['code']}] {d['severity'].upper()}** `{d['file']}:{d['line']}`: {d['message']}")
            if d.get("snippet"):
                lines.append(f"  > _{d['snippet']}_")
            if d.get("suggestion"):
                lines.append(f"  - 💡 *Suggestion*: {d['suggestion']}")
        p_out.write_text("\n".join(lines), encoding="utf-8")
        print(f"📄 Multi-chapter report exported to: {p_out.resolve()}\n")


def cmd_review(args):
    """Unified single-pass literary reviewer emitting scorecard (/10)."""
    target_arg = getattr(args, "chapter", None)
    chapters = _find_chapter_files(target_arg)
    if not chapters:
        print("❌ Error: Chapter not found.")
        sys.exit(1)

    target_ch = chapters[0]
    format_type = getattr(args, "format", "text")
    export_path = getattr(args, "export", None)

    try:
        from canonforge.engines import polish
        res = polish.review_chapter(target_ch)
        if format_type == "json":
            print(json.dumps(res, indent=2))
            return

        polish.print_review(res)

        if export_path:
            p_out = Path(export_path)
            lines = [
                f"# Literary Review Scorecard: {res.get('chapter', target_ch.name)}",
                f"**Overall Score:** {res.get('overall_score', 0)} / 10\n",
                "## Criteria Breakdown",
            ]
            for crit, score in res.get("breakdown", {}).items():
                lines.append(f"- **{crit.title()}**: {score}/10")
            lines.append("\n## Key Editorial Takeaways")
            for t in res.get("takeaways", []):
                lines.append(f"- {t}")
            p_out.write_text("\n".join(lines), encoding="utf-8")
            print(f"📄 Scorecard exported to: {p_out.resolve()}\n")

    except Exception as e:
        print(f"❌ Error during review: {e}")
        sys.exit(1)
