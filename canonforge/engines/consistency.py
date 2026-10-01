"""
consistency.py

Authoritative Consistency & Plot Point Metadata Drift Linter for CanonForge Studio.
--------------------------------------------------------------------------------
Detects decoupling between chapter frontmatter (plot_points, characters) and actual
prose text to prevent narrative drift across books and series.

Diagnostic Codes:
  PLOT001 : Metadata Drift (Plot point registered in frontmatter has zero textual evidence/keywords in prose)
  PLOT002 : Broken Causal DAG (Plot point depends_on an ID that does not exist or occurs in the future)
  PLOT003 : Duplicate Plot Point ID (Same plot point ID registered multiple times)
  PLOT004 : Character Alignment Mismatch (Plot point character not listed in frontmatter characters, or ghost character)
"""

import sys
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Set

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

from canonforge.core.manifest import find_universe_root
from canonforge.cli.groups import style

STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can't", "cannot", "could", "couldn't",
    "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during",
    "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i",
    "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's",
    "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself",
    "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought",
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she",
    "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves"
}

def load_character_alias_map(universe_root: Path) -> Dict[str, List[str]]:
    """Scan wiki/terms/characters for canonical IDs and aliases."""
    alias_map: Dict[str, List[str]] = {}
    candidate_dirs = [
        universe_root / "wiki" / "terms" / "characters",
        universe_root / "wiki" / "characters",
        universe_root / "lore" / "characters",
    ]
    for cdir in candidate_dirs:
        if not cdir.is_dir():
            continue
        for fpath in cdir.glob("*.md"):
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
                if not content.startswith("---"):
                    continue
                parts = content.split("---", 2)
                if len(parts) < 3:
                    continue
                if HAS_YAML:
                    fm = yaml.safe_load(parts[1]) or {}
                else:
                    continue
                
                cid = fm.get("id") or fpath.stem.lower()
                aliases = [fpath.stem.replace("-", " ")]
                title = fm.get("title")
                if title:
                    aliases.append(title)
                for a in fm.get("aliases", []):
                    if a and str(a) not in aliases:
                        aliases.append(str(a))
                
                # Normalize aliases
                clean_aliases = list(set([a.strip() for a in aliases if len(a.strip()) > 1]))
                alias_map[cid.lower()] = clean_aliases
                if title:
                    alias_map[title.lower()] = clean_aliases
                alias_map[fpath.stem.lower()] = clean_aliases
            except Exception:
                pass
    return alias_map

def extract_significant_keywords(text: str) -> List[str]:
    """Tokenize and filter substantive nouns/verbs from event/mechanic text."""
    # Convert underscores and punctuation to spaces
    clean_text = re.sub(r"[_\W]+", " ", text).lower()
    tokens = clean_text.split()
    return [t for t in tokens if len(t) > 3 and t not in STOPWORDS]

def parse_chapter_file(ch_path: Path) -> Tuple[Dict[str, Any], str, int]:
    """Extract frontmatter dict, prose body, and frontmatter line count."""
    try:
        content = ch_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {}, "", 0

    if not content.startswith("---"):
        return {}, content, 0

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content, 0

    fm_raw = parts[1]
    prose = parts[2]
    fm_lines = len(fm_raw.splitlines()) + 2

    fm = {}
    if HAS_YAML:
        try:
            fm = yaml.safe_load(fm_raw) or {}
        except Exception:
            fm = {}
    return fm, prose, fm_lines

def audit_chapter_consistency(
    ch_path: Path,
    alias_map: Dict[str, List[str]],
    all_points_registry: Optional[Dict[str, Dict[str, Any]]] = None,
    current_chronology_index: int = 0,
    point_chronology_indices: Optional[Dict[str, int]] = None,
) -> List[Dict[str, Any]]:
    """Audit single chapter for metadata drift, causal links, and character presence."""
    diagnostics = []
    fm, prose, fm_lines = parse_chapter_file(ch_path)
    if not fm:
        return diagnostics

    prose_lower = prose.lower()
    plot_points = fm.get("plot_points", [])
    fm_characters = fm.get("characters", [])
    if isinstance(fm_characters, list):
        fm_char_names = [str(c).lower() for c in fm_characters]
    else:
        fm_char_names = []

    # 1. Audit Plot Points
    if isinstance(plot_points, list):
        for idx, pp in enumerate(plot_points):
            if not isinstance(pp, dict):
                continue
            pp_id = pp.get("id", f"pp_line_{idx+1}")
            char_field = pp.get("character")
            event_field = pp.get("event", "")
            milestone_field = pp.get("milestone", "")
            mechanic_field = pp.get("mechanic", "")
            state_change_field = pp.get("state_change", "")
            depends_on = pp.get("depends_on", [])

            # Check character presence in prose
            if char_field:
                char_key = str(char_field).lower()
                # Resolve aliases
                aliases = alias_map.get(char_key, [])
                if not aliases:
                    # Fallback tokenization: char_vaelin_pale_weaver -> [vaelin, pale, weaver]
                    clean_name = re.sub(r"^char_", "", char_key).replace("_", " ")
                    aliases = [clean_name, *clean_name.split()]
                
                char_found = any(a.lower() in prose_lower for a in aliases if len(a) > 2)
                if not char_found:
                    diagnostics.append({
                        "code": "PLOT001",
                        "severity": "warning",
                        "file": ch_path.name,
                        "line": 1,
                        "point_id": pp_id,
                        "message": f"Character '{char_field}' in plot point '{pp_id}' is not mentioned in chapter prose."
                    })

                # Check character in frontmatter characters list (PLOT004)
                matched_fm_char = False
                for fmc in fm_char_names:
                    if char_key in fmc or any(a.lower() in fmc for a in aliases):
                        matched_fm_char = True
                        break
                if not matched_fm_char:
                    diagnostics.append({
                        "code": "PLOT004",
                        "severity": "info",
                        "file": ch_path.name,
                        "line": 1,
                        "point_id": pp_id,
                        "message": f"Plot point '{pp_id}' references character '{char_field}', but they are missing from frontmatter 'characters:' list."
                    })

            # Check event/milestone keyword drift (PLOT001)
            combined_desc = f"{event_field} {milestone_field} {mechanic_field} {state_change_field}"
            keywords = extract_significant_keywords(combined_desc)
            if keywords:
                # Count keyword occurrences in prose
                hits = [kw for kw in keywords if re.search(r"\b" + re.escape(kw) + r"\w*", prose_lower)]
                match_ratio = len(hits) / len(keywords)
                # If zero substantive keywords found at all in the prose
                if len(hits) == 0:
                    diagnostics.append({
                        "code": "PLOT001",
                        "severity": "error",
                        "file": ch_path.name,
                        "line": 1,
                        "point_id": pp_id,
                        "message": f"Metadata Drift: Plot point '{pp_id}' claims '{event_field}', but none of its key tokens {keywords[:4]} exist in the prose!"
                    })

            # Check Causal DAG Dependencies (PLOT002)
            if isinstance(depends_on, list) and depends_on:
                for dep_id in depends_on:
                    if all_points_registry is not None:
                        if dep_id not in all_points_registry:
                            diagnostics.append({
                                "code": "PLOT002",
                                "severity": "error",
                                "file": ch_path.name,
                                "line": 1,
                                "point_id": pp_id,
                                "message": f"Broken Causal DAG: Plot point '{pp_id}' depends_on '{dep_id}', but '{dep_id}' is never defined in any chapter!"
                            })
                        elif point_chronology_indices and dep_id in point_chronology_indices:
                            dep_idx = point_chronology_indices[dep_id]
                            if dep_idx > current_chronology_index:
                                target_ch = all_points_registry[dep_id]["chapter_file"]
                                diagnostics.append({
                                    "code": "PLOT002",
                                    "severity": "error",
                                    "file": ch_path.name,
                                    "line": 1,
                                    "point_id": pp_id,
                                    "message": f"Temporal Inversion: Plot point '{pp_id}' depends_on '{dep_id}' which only occurs later in '{target_ch}'!"
                                })

    # 2. Check Ghost Characters (PLOT004)
    for cname in fm_characters:
        c_str = str(cname)
        c_aliases = list(alias_map.get(c_str.lower(), [c_str]))
        # Also include sub-tokens and words inside or outside parentheses
        sub_tokens = re.findall(r"\b[A-Za-z0-9_-]+\b", c_str)
        c_aliases.extend(sub_tokens)
        for st in sub_tokens:
            if "-" in st:
                c_aliases.extend(st.split("-"))
        found_in_prose = any(a.lower() in prose_lower for a in set(c_aliases) if len(a) > 2)
        if not found_in_prose:
            diagnostics.append({
                "code": "PLOT004",
                "severity": "warning",
                "file": ch_path.name,
                "line": 1,
                "character": c_str,
                "message": f"Ghost Character: Frontmatter lists '{c_str}', but character is never mentioned or present in prose."
            })

    return diagnostics

def run_consistency_audit(
    universe_root: Optional[Path] = None,
    chapter_file: Optional[str] = None,
    book_filter: Optional[str] = None,
    series_filter: Optional[str] = None,
    strict: bool = False,
    output_format: str = "text"
) -> Dict[str, Any]:
    """Run full universe consistency audit and report results."""
    u_root = universe_root or find_universe_root()
    ms_dir = u_root / "manuscript"
    if not ms_dir.is_dir():
        print(f"❌ Error: Manuscript directory not found at {ms_dir}")
        return {"success": False, "diagnostics": []}

    alias_map = load_character_alias_map(u_root)

    # 1. Discover all chapters in reading order
    ordered_chapters: List[Tuple[str, str, Path]] = []
    
    # Check reading order from universe.yaml if available
    u_yaml_path = u_root / "universe.yaml"
    reading_order = []
    if u_yaml_path.is_file() and HAS_YAML:
        try:
            u_meta = yaml.safe_load(u_yaml_path.read_text(encoding="utf-8")) or {}
            reading_order = u_meta.get("reading_order_recommended", [])
        except Exception:
            pass

    # Collect series
    series_dirs = sorted([d for d in ms_dir.iterdir() if d.is_dir() and not d.name.startswith((".", "_"))])
    if series_filter:
        series_dirs = [d for d in series_dirs if series_filter in d.name]

    for s_dir in series_dirs:
        book_dirs = sorted([b for b in s_dir.iterdir() if b.is_dir() and b.name.startswith("book-")])
        if book_filter:
            book_dirs = [b for b in book_dirs if book_filter in b.name]
        
        for b_dir in book_dirs:
            ch_dir = b_dir / "chapters"
            if not ch_dir.is_dir():
                continue
            
            # Check toc.yaml for ordering
            toc_yaml = b_dir / "toc.yaml"
            toc_order = []
            if toc_yaml.is_file() and HAS_YAML:
                try:
                    t_data = yaml.safe_load(toc_yaml.read_text(encoding="utf-8")) or {}
                    for act in t_data.get("acts", []):
                        for ch_name in act.get("chapters", []):
                            if isinstance(ch_name, str):
                                toc_order.append(ch_name)
                            elif isinstance(ch_name, dict) and "file" in ch_name:
                                toc_order.append(ch_name["file"])
                except Exception:
                    pass
            
            if toc_order:
                for ch_fname in toc_order:
                    fpath = ch_dir / ch_fname
                    if fpath.is_file():
                        ordered_chapters.append((s_dir.name, b_dir.name, fpath))
            else:
                for fpath in sorted(ch_dir.glob("*.md")):
                    ordered_chapters.append((s_dir.name, b_dir.name, fpath))

    # 2. Build universe plot points registry & check for duplicate IDs (PLOT003)
    all_points_registry: Dict[str, Dict[str, Any]] = {}
    point_chronology_indices: Dict[str, int] = {}
    duplicate_diagnostics = []

    for chron_idx, (series_slug, book_slug, ch_path) in enumerate(ordered_chapters):
        fm, _, _ = parse_chapter_file(ch_path)
        pps = fm.get("plot_points", [])
        if isinstance(pps, list):
            for pp in pps:
                if not isinstance(pp, dict):
                    continue
                pp_id = pp.get("id")
                if not pp_id:
                    continue
                if pp_id in all_points_registry:
                    first_hit = all_points_registry[pp_id]
                    duplicate_diagnostics.append({
                        "code": "PLOT003",
                        "severity": "error",
                        "file": ch_path.name,
                        "line": 1,
                        "point_id": pp_id,
                        "message": f"Duplicate plot point ID '{pp_id}'! Already defined in {first_hit['series']}/{first_hit['book']}/{first_hit['chapter_file']}."
                    })
                else:
                    all_points_registry[pp_id] = {
                        "series": series_slug,
                        "book": book_slug,
                        "chapter_file": ch_path.name,
                        "data": pp
                    }
                    point_chronology_indices[pp_id] = chron_idx

    # Filter to specific chapter if requested
    target_chapters = ordered_chapters
    if chapter_file:
        target_chapters = [(s, b, p) for s, b, p in ordered_chapters if chapter_file in p.name or chapter_file == str(p)]

    # 3. Execute chapter consistency audits
    all_diagnostics = list(duplicate_diagnostics)
    total_chapters_scanned = len(target_chapters)
    total_points_validated = 0

    for chron_idx, (series_slug, book_slug, ch_path) in enumerate(target_chapters):
        fm, _, _ = parse_chapter_file(ch_path)
        pps = fm.get("plot_points", [])
        if isinstance(pps, list):
            total_points_validated += len(pps)

        ch_diags = audit_chapter_consistency(
            ch_path,
            alias_map=alias_map,
            all_points_registry=all_points_registry,
            current_chronology_index=chron_idx,
            point_chronology_indices=point_chronology_indices
        )
        for d in ch_diags:
            d["series"] = series_slug
            d["book"] = book_slug
            all_diagnostics.append(d)

    # 4. Format Output
    errors = [d for d in all_diagnostics if d.get("severity") == "error"]
    warnings = [d for d in all_diagnostics if d.get("severity") == "warning"]
    infos = [d for d in all_diagnostics if d.get("severity") == "info"]

    if output_format == "json":
        has_failures = len(errors) > 0 or (strict and len(warnings) > 0)
        result = {
            "success": not has_failures,
            "universe": u_root.name,
            "total_chapters_scanned": total_chapters_scanned,
            "total_points_validated": total_points_validated,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "info_count": len(infos),
            "diagnostics": all_diagnostics
        }
        print(json.dumps(result, indent=2))
        return result

    # Terminal Pretty Report
    print("\n" + "=" * 80)
    print(f" 🛡️  CANONFORGE PLOT CONSISTENCY & METADATA DRIFT AUDIT")
    print("=" * 80)
    print(f" Universe:            {style(u_root.name, 'bold')}")
    print(f" Scanned Chapters:    {total_chapters_scanned}")
    print(f" Validated Points:    {total_points_validated}")
    print(f" Total Diagnostics:   Errors: {len(errors)} | Warnings: {len(warnings)} | Info: {len(infos)}")
    print("-" * 80)

    if not all_diagnostics:
        print(style(" 🎉 100% CONSISTENCY PASS: Zero metadata drift or broken causal links detected!\n", "green"))
    else:
        table_rows = []
        for d in all_diagnostics:
            sev_badge = style("ERR", "red") if d["severity"] == "error" else (style("WARN", "yellow") if d["severity"] == "warning" else style("INFO", "cyan"))
            loc = f"{d.get('book', '')}/{d['file']}"
            table_rows.append([
                sev_badge,
                d["code"],
                loc,
                d.get("point_id", d.get("character", "-")),
                d["message"]
            ])
        
        headers = ["Sev", "Code", "Location", "Subject", "Diagnostic Finding"]
        if HAS_TABULATE:
            print(tabulate(table_rows, headers=headers, tablefmt="psql"))
        else:
            for r in table_rows:
                print(f"[{r[0]}] {r[1]} @ {r[2]} ({r[3]}): {r[4]}")
        print()

    has_failures = len(errors) > 0 or (strict and len(warnings) > 0)
    return {
        "success": not has_failures,
        "diagnostics": all_diagnostics,
        "total_points": total_points_validated
    }

def main():
    parser = argparse.ArgumentParser(description="CanonForge Plot Consistency & Metadata Drift Linter")
    parser.add_argument("chapter", nargs="?", default="", help="Optional chapter file or pattern to audit")
    parser.add_argument("--book", "-b", help="Filter by book directory (e.g. book-01)")
    parser.add_argument("--series", "-s", help="Filter by series slug (e.g. sun-sanctum)")
    parser.add_argument("--strict", action="store_true", help="Fail on warnings as well as errors")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--universe", "-u", help="Path to universe root")

    args = parser.parse_args()
    u_root = Path(args.universe).resolve() if args.universe else find_universe_root()

    res = run_consistency_audit(
        universe_root=u_root,
        chapter_file=args.chapter or None,
        book_filter=args.book,
        series_filter=args.series,
        strict=args.strict,
        output_format=args.format
    )

    if not res.get("success", False):
        sys.exit(1)

if __name__ == "__main__":
    main()
