"""
Cast interaction matrix & chapter continuity audit
"""
import re
from pathlib import Path
from typing import Dict, List, Set, Any, Optional

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

from canonforge.engines.relations.timeline import resolve_active_relationship, resolve_character_name, get_all_characters
from canonforge.engines.relations.graph import build_adjacency_graph

def build_cast_matrix(cast_names: List[str], data: Dict[str, Any], ao_year: Optional[int] = None) -> bool:
    """Build an NxN mutual relationship matrix for a list of characters at a given era."""
    all_names = get_all_characters(data)
    resolved_cast = []
    
    for c in cast_names:
        r = resolve_character_name(c, all_names)
        if r and r not in resolved_cast:
            resolved_cast.append(r)
        elif not r:
            print(f"⚠️  Skipping unrecognized character: '{c}'")
            
    if len(resolved_cast) < 2:
        print("❌ Please specify at least 2 valid character names to build a matrix.")
        return False
        
    graph = build_adjacency_graph(data, ao_year=ao_year)
    
    print("\n" + "=" * 80)
    print(f"  👥 CAST RELATIONSHIP MATRIX ({len(resolved_cast)} Characters)")
    if ao_year:
        print(f"      Chronological Anchor: {ao_year} AO")
    print("=" * 80)
    
    matrix_rows = []
    for src in resolved_cast:
        row = [src]
        for tgt in resolved_cast:
            if src == tgt:
                row.append("•")
            else:
                match = None
                for e in graph.get(src, []):
                    if e["target"] == tgt:
                        match = e
                        break
                if match:
                    sent = match["sentiment"]
                    icon = "🟢" if sent > 0.4 else ("🔴" if sent < -0.4 else "🟡")
                    row.append(f"{icon} {match['sub_type'].replace('_', ' ')[:10]}")
                else:
                    row.append("-")
        matrix_rows.append(row)
        
    headers = ["Character"] + [c.split()[0] for c in resolved_cast]
    if HAS_TABULATE:
        print(tabulate(matrix_rows, headers=headers, tablefmt="rounded_grid"))
    else:
        print(" | ".join(headers))
        for r in matrix_rows:
            print(" | ".join(str(x) for x in r))
            
    print("=" * 80 + "\n")
    return True


# ==============================================================================
# CHAPTER CONTINUITY AUDITOR
# ==============================================================================

def audit_chapter_relations(chapter_file: Path, data: Dict[str, Any]) -> bool:
    """Scan a chapter file and cross-reference character interaction dynamics using its specific chapter anchor."""
    if not chapter_file.exists():
        found = list(Path.cwd().glob(f"manuscript/**/{chapter_file.name}"))
        if found:
            chapter_file = found[0]
        else:
            print(f"❌ Chapter file not found: {chapter_file}")
            return False
        
    content = chapter_file.read_text(encoding="utf-8")
    all_names = get_all_characters(data)
    
    # 1. Parse frontmatter metadata
    fm_match = re.search(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    book_num = None
    ch_num = None
    timeline_str = ""
    present_characters = set()
    
    if fm_match:
        for line in fm_match.group(1).splitlines():
            line_str = line.strip()
            if line_str.startswith("chapter:"):
                try:
                    ch_num = int(line_str.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif line_str.startswith("book:"):
                b_str = line_str.split(":", 1)[1].strip().strip('"').strip("'")
                if "champion" in b_str:
                    book_num = 4
                elif "disciple" in b_str:
                    book_num = 3
                elif "adept" in b_str:
                    book_num = 2
                elif "apprentice" in b_str or "stone-child" in b_str:
                    book_num = 1
            elif line_str.startswith("timeline:"):
                timeline_str = line_str.split(":", 1)[1].strip().strip('"').strip("'")
            elif line_str.startswith("- "):
                candidate = line_str[2:].strip().strip('"').strip("'")
                res = resolve_character_name(candidate, all_names)
                if res:
                    present_characters.add(res)
                    
    # Also check text mentions for canonical characters
    for name in all_names:
        first_name = name.split()[0]
        if len(first_name) >= 4 and re.search(r"\b" + re.escape(first_name) + r"\b", content):
            present_characters.add(name)
        elif re.search(r"\b" + re.escape(name) + r"\b", content):
            present_characters.add(name)
            
    # Resolve graph to THIS EXACT CHAPTER / BOOK
    graph = build_adjacency_graph(data, book=book_num, chapter=ch_num)
    sorted_cast = sorted(list(present_characters))
    
    print("\n" + "=" * 80)
    print(f"  🔍 CHAPTER RELATIONSHIP CONTINUITY AUDIT: {chapter_file.name}")
    print(f"      Book: {book_num or 'Unknown'} | Chapter: {ch_num or 'Unknown'} | Timeline: {timeline_str or '1064–1065 AO'}")
    print("=" * 80)
    print(f"• Detected Cast ({len(sorted_cast)} entities): {', '.join(sorted_cast)}\n")
    
    if len(sorted_cast) < 2:
        print("  ℹ️  Fewer than 2 registered characters detected in this chapter. No interpersonal friction to audit.")
        print("=" * 80 + "\n")
        return True
        
    alerts = []
    audited_pairs = set()
    
    for i, c1 in enumerate(sorted_cast):
        for c2 in sorted_cast[i+1:]:
            pair_key = tuple(sorted([c1, c2]))
            if pair_key in audited_pairs:
                continue
            audited_pairs.add(pair_key)
            
            match_edge = None
            for e in graph.get(c1, []):
                if e["target"] == c2:
                    match_edge = e
                    break
                    
            if match_edge:
                rel_type = match_edge["relation_type"]
                dyn = match_edge.get("dynamic_state", "")
                sent = match_edge["sentiment"]
                rule = match_edge.get("narrative_rule", "")
                
                if rel_type in ("tension", "rivalry", "deception") or sent < -0.2:
                    alerts.append({
                        "pair": f"{c1} ⚔️ {c2}",
                        "type": rel_type.upper(),
                        "sub_type": match_edge["sub_type"],
                        "sentiment": sent,
                        "anchor": match_edge["active_phase"],
                        "dynamic": dyn or "High tension/friction recorded.",
                        "rule": rule
                    })
                elif match_edge.get("active_phase") != "All" or "strained" in dyn.lower() or "jealousy" in dyn.lower():
                    alerts.append({
                        "pair": f"{c1} ↔️ {c2}",
                        "type": "CHAPTER-SPECIFIC DYNAMIC",
                        "sub_type": match_edge["sub_type"],
                        "sentiment": sent,
                        "anchor": match_edge["active_phase"],
                        "dynamic": dyn,
                        "rule": rule
                    })
                    
    if not alerts:
        print("  ✅ All character pairings in this chapter reflect stable or harmonious baseline dynamics.")
    else:
        print(f"  ⚠️  {len(alerts)} ACTIVE DRAMATIC RELATIONSHIP DYNAMICS REQUIRING ATTENTION:\n")
        for idx, a in enumerate(alerts, 1):
            sent_str = f"+{a['sentiment']:.2f}" if a['sentiment'] >= 0 else f"{a['sentiment']:.2f}"
            print(f"  [{idx}] {a['pair']} ({a['type']} / {a['sub_type'].replace('_', ' ')} | Affinity: {sent_str} | Anchor: {a['anchor']})")
            print(f"      📌 Canonical Trigger: {a['dynamic']}")
            if a["rule"]:
                print(f"      ✍️ Writing Rule     : {a['rule']}")
            print()
            
    print("=" * 80 + "\n")
    return True


# ==============================================================================
# MERMAID EXPORT
# ==============================================================================

