"""
impact.py - Narrative Blast Radius & Plot Point Causality Analyzer

Scans all books, chapters, frontmatter plot_points, character dossiers,
and outlines across a universe to evaluate the ripple effect of narrative changes.
"""

import sys
import os
import re
import argparse
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

try:
    import yaml
except ImportError:
    yaml = None

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

from canonforge.core.manifest import find_universe_root


def extract_frontmatter(content: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """Parse YAML frontmatter and body from markdown content."""
    if not content.startswith("---"):
        return None, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None, content
    fm_text = parts[1]
    body = parts[2]
    if yaml:
        try:
            data = yaml.safe_load(fm_text)
            if isinstance(data, dict):
                return data, body
        except Exception:
            pass
    return None, body


def scan_chapter_for_impact(
    file_path: Path,
    series_id: str,
    book_id: str,
    query_terms: List[str],
    character_filter: Optional[str] = None,
    milestone_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Scan a single chapter file for frontmatter plot points and text matches."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    from typing import Tuple
    frontmatter, body = extract_frontmatter(content)
    hits = []
    
    fm_chars = []
    if frontmatter and isinstance(frontmatter.get("characters"), list):
        fm_chars = [str(c).lower() for c in frontmatter["characters"]]

    # 1. Frontmatter plot_points check
    if frontmatter and "plot_points" in frontmatter and isinstance(frontmatter["plot_points"], list):
        for idx, pp in enumerate(frontmatter["plot_points"]):
            if not isinstance(pp, dict):
                continue
            pp_str = json.dumps(pp).lower()
            pp_char = str(pp.get("character", "")).lower()
            pp_ms = str(pp.get("milestone", "")).lower()
            pp_id = str(pp.get("id", "")).lower()

            matched = False
            # Check milestone filter
            if milestone_filter and (milestone_filter.lower() in pp_ms or milestone_filter.lower() in pp_id):
                matched = True
            # Check character filter
            elif character_filter and character_filter.lower() in pp_char:
                matched = True
            # Check general query terms
            elif any(q.lower() in pp_str for q in query_terms if q):
                matched = True

            if matched:
                hits.append({
                    "series": series_id,
                    "book": book_id,
                    "chapter_file": file_path.name,
                    "title": frontmatter.get("title", file_path.stem),
                    "act": frontmatter.get("act", 1),
                    "chapter_num": frontmatter.get("chapter", 0),
                    "line": 1,
                    "type": "FRONTMATTER_PLOT_POINT",
                    "severity": "HIGH",
                    "snippet": f"plot_point[{idx}]: {pp.get('event') or pp.get('milestone') or pp.get('id')}",
                    "details": pp
                })

    # 2. Text prose scanning (line by line)
    lines = content.splitlines()
    for line_idx, line in enumerate(lines, start=1):
        line_clean = line.strip()
        if not line_clean or line_clean.startswith("---") or line_clean.startswith("#"):
            continue

        line_lower = line_clean.lower()

        # Check for query terms match
        matched_terms = [q for q in query_terms if q and q.lower() in line_lower]
        if character_filter and character_filter.lower() in line_lower:
            matched_terms.append(character_filter)
        if milestone_filter and milestone_filter.lower() in line_lower:
            matched_terms.append(milestone_filter)

        if not matched_terms:
            continue

        # Classify as Dialogue or Narrative
        is_dialogue = '"' in line_clean or '“' in line_clean or '”' in line_clean
        severity = "MEDIUM" if is_dialogue else "LOW"

        # Truncate snippet
        snippet = line_clean
        if len(snippet) > 120:
            snippet = snippet[:117] + "..."

        hits.append({
            "series": series_id,
            "book": book_id,
            "chapter_file": file_path.name,
            "title": frontmatter.get("title", file_path.stem) if frontmatter else file_path.stem,
            "act": frontmatter.get("act", 1) if frontmatter else 1,
            "chapter_num": frontmatter.get("chapter", 0) if frontmatter else 0,
            "line": line_idx,
            "type": "DIALOGUE" if is_dialogue else "NARRATIVE",
            "severity": severity,
            "snippet": snippet,
            "matched_terms": list(set(matched_terms))
        })

    return hits


def scan_dossiers_for_impact(
    universe_root: Path,
    query_terms: List[str],
    character_filter: Optional[str] = None,
    milestone_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Scan wiki character profiles and dossiers for matching milestones or lore invariants."""
    wiki_dirs = [
        universe_root / "wiki" / "terms" / "characters",
        universe_root / "wiki" / "characters",
        universe_root / "lore" / "characters",
    ]
    hits = []

    for d in wiki_dirs:
        if not d.is_dir():
            continue
        for f in d.glob("*.md"):
            if f.name == "index.md":
                continue
            try:
                txt = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            fm, body = extract_frontmatter(txt)
            char_title = fm.get("title", f.stem) if fm else f.stem
            char_id = fm.get("id", "") if fm else ""

            if character_filter:
                if character_filter.lower() not in char_title.lower() and character_filter.lower() not in char_id.lower():
                    continue

            lines = txt.splitlines()
            for l_idx, line in enumerate(lines, start=1):
                l_lower = line.lower()
                matched = [q for q in query_terms if q and q.lower() in l_lower]
                if milestone_filter and milestone_filter.lower() in l_lower:
                    matched.append(milestone_filter)

                if matched:
                    # Invariants or milestones match is HIGH severity
                    is_invariant = "invariant" in l_lower or "milestone" in l_lower or "catalyst" in l_lower
                    sev = "HIGH" if is_invariant else "MEDIUM"
                    snippet = line.strip()
                    if len(snippet) > 120:
                        snippet = snippet[:117] + "..."

                    hits.append({
                        "series": "WIKI_SSOT",
                        "book": "Character Dossier",
                        "chapter_file": f.name,
                        "title": char_title,
                        "act": 0,
                        "chapter_num": 0,
                        "line": l_idx,
                        "type": "DOSSIER_INVARIANT" if is_invariant else "DOSSIER_LORE",
                        "severity": sev,
                        "snippet": snippet,
                        "matched_terms": list(set(matched))
                    })

    return hits


def run_impact_analysis(
    universe_root: Optional[Path] = None,
    query: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    character: Optional[str] = None,
    milestone: Optional[str] = None,
    series_filter: Optional[str] = None,
    book_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute complete cross-book impact analysis across the universe."""
    root = universe_root or find_universe_root()
    if not (root / "universe.yaml").is_file():
        return {"error": f"No universe.yaml found at {root}", "hits": []}

    query_terms = []
    if query:
        # Split commas or spaces
        parts = [p.strip() for p in re.split(r"[,;]+", query) if p.strip()]
        query_terms.extend(parts)
    if keywords:
        query_terms.extend([k.strip() for k in keywords if k.strip()])

    if not query_terms and not character and not milestone:
        return {"error": "Must provide query terms, --character, or --milestone", "hits": []}

    manuscript_dir = root / "manuscript"
    all_hits = []

    # 1. Discover all series
    series_dirs = [d for d in manuscript_dir.iterdir() if d.is_dir() and not d.name.startswith("_")]
    if series_filter:
        series_dirs = [d for d in series_dirs if d.name == series_filter or series_filter in d.name]

    for s_dir in sorted(series_dirs):
        series_id = s_dir.name
        # Discover books
        book_dirs = [d for d in s_dir.iterdir() if d.is_dir() and (d / "toc.yaml").is_file()]
        if book_filter:
            book_dirs = [d for d in book_dirs if d.name == book_filter or book_filter in d.name]

        for b_dir in sorted(book_dirs):
            book_id = b_dir.name
            chap_dir = b_dir / "chapters"
            if not chap_dir.is_dir():
                continue

            for chap_file in sorted(chap_dir.glob("*.md")):
                chap_hits = scan_chapter_for_impact(
                    file_path=chap_file,
                    series_id=series_id,
                    book_id=book_id,
                    query_terms=query_terms,
                    character_filter=character,
                    milestone_filter=milestone,
                )
                all_hits.extend(chap_hits)

    # 2. Scan Wiki Character Dossiers
    dossier_hits = scan_dossiers_for_impact(root, query_terms, character, milestone)
    all_hits.extend(dossier_hits)

    # Calculate statistics
    affected_books = set()
    affected_chapters = set()
    affected_dossiers = set()
    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

    for h in all_hits:
        sev = h.get("severity", "LOW")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1
        if h["series"] == "WIKI_SSOT":
            affected_dossiers.add(h["chapter_file"])
        else:
            affected_books.add(f"{h['series']}/{h['book']}")
            affected_chapters.add(f"{h['series']}/{h['book']}/{h['chapter_file']}")

    return {
        "universe": root.name,
        "query_terms": query_terms,
        "character": character,
        "milestone": milestone,
        "total_hits": len(all_hits),
        "total_books_affected": len(affected_books),
        "total_chapters_affected": len(affected_chapters),
        "total_dossiers_affected": len(affected_dossiers),
        "severity_summary": severity_counts,
        "affected_books": sorted(list(affected_books)),
        "hits": all_hits
    }


def render_impact_report(result: Dict[str, Any], output_format: str = "text") -> None:
    """Print structured impact report."""
    if "error" in result:
        print(f"\n❌ Error: {result['error']}\n")
        return

    if output_format == "json":
        print(json.dumps(result, indent=2))
        return

    print("\n" + "=" * 80)
    print(" 💥 CANONFORGE NARRATIVE BLAST RADIUS & PLOT IMPACT REPORT")
    print("=" * 80)
    print(f" Universe:            {result['universe']}")
    if result.get('query_terms'):
        print(f" Query Terms:         {', '.join(result['query_terms'])}")
    if result.get('character'):
        print(f" Target Character:    {result['character']}")
    if result.get('milestone'):
        print(f" Target Milestone:    {result['milestone']}")
    print("-" * 80)
    print(f" 📊 Impact Blast Radius:")
    print(f"    • Total Occurrences:        {result['total_hits']}")
    print(f"    • Books Affected:           {result['total_books_affected']}")
    print(f"    • Chapters Affected:        {result['total_chapters_affected']}")
    print(f"    • Character Dossiers:       {result['total_dossiers_affected']}")
    print(f"    • Severity Breakdown:       High: {result['severity_summary'].get('HIGH', 0)} | "
          f"Med: {result['severity_summary'].get('MEDIUM', 0)} | "
          f"Low: {result['severity_summary'].get('LOW', 0)}")
    print("=" * 80)

    if not result["hits"]:
        print("  🎉 Zero conflicting dependencies or references found! Clear to proceed.")
        print("=" * 80 + "\n")
        return

    # Group hits by Book / Scope
    table_rows = []
    for h in result["hits"]:
        location = f"{h['book']}/{h['chapter_file']}:{h['line']}"
        table_rows.append([
            h["severity"],
            h["type"],
            location,
            h["snippet"]
        ])

    if HAS_TABULATE:
        headers = ["Severity", "Type", "File Location", "Prose / Metadata Snippet"]
        print(tabulate(table_rows, headers=headers, tablefmt="github"))
    else:
        for row in table_rows:
            print(f"[{row[0]}] {row[1]} @ {row[2]}\n    -> {row[3]}\n")

    print("\n" + "=" * 80)
    print(" 🛠️  ACTIONABLE REWRITE CHECKLIST:")
    unique_files = sorted(list(set(
        f"{h['series']}/{h['book']}/{h['chapter_file']}" if h['series'] != "WIKI_SSOT" else f"wiki/{h['chapter_file']}"
        for h in result["hits"]
    )))
    for uf in unique_files:
        print(f"  [ ] {uf}")
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        prog="cf impact",
        description="Analyze narrative blast radius and causality across all books in the universe."
    )
    parser.add_argument("query", nargs="?", default="", help="Keyword, phrase, or plot point term")
    parser.add_argument("--keywords", "-k", nargs="*", default=[], help="Additional keywords to trace")
    parser.add_argument("--character", "-c", help="Target character name or ID to trace")
    parser.add_argument("--milestone", "-m", help="Target milestone ID to trace")
    parser.add_argument("--series", "-s", help="Filter to specific series slug")
    parser.add_argument("--book", "-b", help="Filter to specific book slug")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--universe", "-u", help="Path to universe root")

    args = parser.parse_args()

    u_root = Path(args.universe).resolve() if args.universe else find_universe_root()
    res = run_impact_analysis(
        universe_root=u_root,
        query=args.query,
        keywords=args.keywords,
        character=args.character,
        milestone=args.milestone,
        series_filter=args.series,
        book_filter=args.book,
    )

    render_impact_report(res, output_format=args.format)


if __name__ == "__main__":
    main()
