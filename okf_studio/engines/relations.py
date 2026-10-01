#!/usr/bin/env python3
"""
character_relations.py

Convergence Studio: Character Relationship Graph Engine & Continuity Auditor.
Single Source of Truth: `wiki/database/relationships.json` & SQLite `data/game_world.db`.

Dual-Anchor Timeline Features:
1. Universal Chronological Resolution: Anno Oryn (AO) world-time for off-screen, backstory, and parallel stories.
2. In-Story Chapter Slices: book & chapter interval resolution for active manuscript scenes.
3. Shortest-path discovery between any two characters (BFS Graph Traversal).
4. Cross-relation ensemble matrix for chapter casts.
5. Chapter continuity audit: verifies active emotional/relational dynamics for co-occurring characters.
6. Mermaid.js network export.
7. Local SQLite synchronization and relational view generation.

Usage:
    ./ax relations "Vaelin"
    ./ax relations "Vaelin" --chapter 18 --book 4
    ./ax relations "Vaelin" --chapter 21 --book 4
    ./ax relations "Bartok" --year 1052
    ./ax relations "Bartok" --year 1056
    ./ax relations path "Vaelin" "Viktor Kray"
    ./ax relations matrix "Vaelin" "Corin" "Lyra" "Althea" "Seren"
    ./ax relations audit manuscript/the-sun-sanctum-champion/chapters/ch23-the-winter-solstice-ball.md
    ./ax relations --mermaid
    ./ax relations --sync-db
"""

import sys
import os
import re
import json
import sqlite3
import argparse
import difflib
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Set
from collections import deque

SCRIPT_DIR = Path(__file__).resolve().parent
CONVERGENCE_DIR = SCRIPT_DIR.parent
DATA_DIR = CONVERGENCE_DIR / "data"
WIKI_DIR = CONVERGENCE_DIR / "wiki"
RELATIONSHIPS_FILE = WIKI_DIR / "database" / "relationships.json"
DB_PATH = DATA_DIR / "game_world.db"

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False


# ==============================================================================
# DATA LOADING & NORMALIZATION
# ==============================================================================

def load_relationships_data() -> Dict[str, Any]:
    """Load canonical relationships from SSOT JSON file with fallback."""
    if not RELATIONSHIPS_FILE.exists():
        return {"relationships": []}
    try:
        return json.loads(RELATIONSHIPS_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"⚠️  [Relationship Engine] Error reading {RELATIONSHIPS_FILE.name}: {e}", file=sys.stderr)
        return {"relationships": []}


def get_all_characters(data: Dict[str, Any]) -> Set[str]:
    """Extract set of all unique canonical character names in relationship registry."""
    names = set()
    for rel in data.get("relationships", []):
        if rel.get("source"):
            names.add(rel["source"].strip())
        if rel.get("target"):
            names.add(rel["target"].strip())
    return names


def resolve_character_name(query: str, all_names: Set[str]) -> Optional[str]:
    """Fuzzy resolve character query to canonical name (case-insensitive substring & fuzzy match)."""
    q_clean = query.strip().lower()
    
    # 1. Exact match (case-insensitive)
    for name in all_names:
        if name.lower() == q_clean:
            return name
            
    # 2. Substring match (e.g. 'Vaelin' matches 'Vaelin the Pale Weaver')
    matches = [name for name in all_names if q_clean in name.lower()]
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        # Prefer shortest or exact prefix
        matches.sort(key=lambda x: (not x.lower().startswith(q_clean), len(x)))
        return matches[0]
        
    # 3. Fuzzy ratio match
    close = difflib.get_close_matches(query, list(all_names), n=1, cutoff=0.6)
    if close:
        return close[0]
        
    return None


# ==============================================================================
# DUAL-ANCHOR TIMELINE RESOLVER
# ==============================================================================

def resolve_active_relationship(
    rel: Dict[str, Any],
    ao_year: Optional[int] = None,
    book: Optional[int] = None,
    chapter: Optional[int] = None,
    story: Optional[str] = None,
    phase: Optional[str] = None,
    scene: Optional[int] = None
) -> Dict[str, Any]:
    """Resolve active relationship state using Dual-Anchor Timeline resolution with Intra-Chapter support."""
    timeline = rel.get("timeline", [])
    if not timeline:
        return {
            "relation_type": rel.get("relation_type", "neutral"),
            "sub_type": rel.get("sub_type", ""),
            "sentiment": rel.get("sentiment", 0.0),
            "dynamic_state": rel.get("dynamic_state", ""),
            "narrative_rule": "",
            "resolved_via": "baseline",
            "intra_slices": []
        }

    def _pack(s: Dict[str, Any], via: str, matching_all: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "relation_type": s.get("relation_type", rel.get("relation_type")),
            "sub_type": s.get("sub_type", rel.get("sub_type")),
            "sentiment": s.get("sentiment", rel.get("sentiment", 0.0)),
            "dynamic_state": s.get("trigger_event", rel.get("dynamic_state", "")),
            "narrative_rule": s.get("narrative_rule", ""),
            "resolved_via": via,
            "intra_slices": matching_all
        }

    # 1. Chapter-level exact match (if book & chapter provided)
    if book is not None and chapter is not None:
        matching = []
        for s in timeline:
            if s.get("book") == book:
                from_ch = s.get("from_ch", 1)
                to_ch = s.get("to_ch") or 9999
                if from_ch <= chapter <= to_ch:
                    matching.append(s)
        
        if matching:
            # Check if specific phase or scene requested
            if phase is not None:
                p_lower = phase.lower()
                for s in matching:
                    if s.get("phase", "").lower() == p_lower:
                        return _pack(s, f"Book {book} Ch {chapter} [{p_lower}]", matching)
            if scene is not None:
                for s in matching:
                    if s.get("scene") == scene:
                        return _pack(s, f"Book {book} Ch {chapter} [Scene {scene}]", matching)
            
            # Default: If multiple intra-chapter slices exist, return the active / climax slice
            # but preserve all slices in intra_slices
            target_slice = matching[-1]
            from_ch = target_slice.get("from_ch", 1)
            to_ch = target_slice.get("to_ch") or 9999
            via_desc = f"Book {book} Ch {from_ch}–{to_ch if to_ch != 9999 else '+'}"
            if len(matching) > 1:
                via_desc += f" ({len(matching)} intra-chapter phases)"
            return _pack(target_slice, via_desc, matching)

    # 2. Chronological Anno Oryn Year match (if ao_year provided)
    if ao_year is not None:
        matching_year = []
        for s in timeline:
            start = s.get("ao_year_start")
            end = s.get("ao_year_end") or 9999
            if start is not None and start <= ao_year <= end:
                matching_year.append(s)
        if matching_year:
            if phase is not None:
                p_lower = phase.lower()
                for s in matching_year:
                    if s.get("phase", "").lower() == p_lower:
                        return _pack(s, f"{ao_year} AO [{p_lower}]", matching_year)
            chosen = matching_year[-1]
            start = chosen.get("ao_year_start")
            end = chosen.get("ao_year_end") or 9999
            return _pack(chosen, f"{start}–{end if end != 9999 else 'present'} AO", matching_year)

    # 3. Story-specific fallback
    if story is not None:
        story_slices = [s for s in timeline if s.get("story") == story]
        if story_slices:
            return _pack(story_slices[-1], f"Story: {story}", story_slices)

    # 4. Fallback: latest timeline slice
    latest = timeline[-1]
    return _pack(latest, "latest_milestone", [latest])


# ==============================================================================
# GRAPH ENGINE & QUERIES
# ==============================================================================

def build_adjacency_graph(
    data: Dict[str, Any],
    ao_year: Optional[int] = None,
    book: Optional[int] = None,
    chapter: Optional[int] = None,
    story: Optional[str] = None,
    phase: Optional[str] = None,
    scene: Optional[int] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """Build directed/undirected adjacency list resolved to a specific timeline anchor."""
    graph: Dict[str, List[Dict[str, Any]]] = {}
    
    for rel in data.get("relationships", []):
        src = rel.get("source")
        tgt = rel.get("target")
        if not src or not tgt:
            continue
            
        graph.setdefault(src, [])
        graph.setdefault(tgt, [])
        
        # Resolve active timeline state
        active = resolve_active_relationship(rel, ao_year=ao_year, book=book, chapter=chapter, story=story, phase=phase, scene=scene)
        
        # Outbound edge
        graph[src].append({
            "target": tgt,
            "relation_type": active["relation_type"],
            "sub_type": active["sub_type"],
            "sentiment": active["sentiment"],
            "symmetry": rel.get("symmetry", "directed"),
            "direction": "outbound",
            "active_phase": active.get("resolved_via", "All"),
            "dynamic_state": active.get("dynamic_state", ""),
            "narrative_rule": active.get("narrative_rule", ""),
            "notes": rel.get("notes", "")
        })
        
        # Reverse edge
        is_symmetric = rel.get("symmetry") == "symmetric"
        reverse_sub = rel.get("reverse_sub_type") or active["sub_type"]
        graph[tgt].append({
            "target": src,
            "relation_type": active["relation_type"],
            "sub_type": reverse_sub,
            "sentiment": active["sentiment"],
            "symmetry": rel.get("symmetry", "directed"),
            "direction": "mutual" if is_symmetric else "inbound",
            "active_phase": active.get("resolved_via", "All"),
            "dynamic_state": active.get("dynamic_state", ""),
            "narrative_rule": active.get("narrative_rule", ""),
            "notes": rel.get("notes", "")
        })
        
    return graph


def inspect_character_relations(
    char_name: str,
    data: Dict[str, Any],
    ao_year: Optional[int] = None,
    book: Optional[int] = None,
    chapter: Optional[int] = None,
    story: Optional[str] = None,
    phase: Optional[str] = None,
    scene: Optional[int] = None
) -> bool:
    """Inspect and format all relationships for a single character at a specific timeline anchor."""
    all_names = get_all_characters(data)
    canonical = resolve_character_name(char_name, all_names)
    
    if not canonical:
        print(f"\n❌ Character '{char_name}' not found in relationship database.")
        close = difflib.get_close_matches(char_name, list(all_names), n=3, cutoff=0.4)
        if close:
            print(f"💡 Did you mean: {', '.join(close)}?")
        return False
        
    graph = build_adjacency_graph(data, ao_year=ao_year, book=book, chapter=chapter, story=story, phase=phase, scene=scene)
    edges = graph.get(canonical, [])
    
    anchor_desc = "Latest / Baseline State"
    if book and chapter:
        anchor_desc = f"Book {book}, Chapter {chapter}"
    elif ao_year:
        anchor_desc = f"World Chronology: {ao_year} AO"
        
    print("\n" + "=" * 85)
    print(f"  🕸️  CONVERGENCE RELATIONSHIP DOSSIER: {canonical.upper()}")
    print(f"      Anchor: {anchor_desc}")
    print("=" * 85)
    
    if not edges:
        print(f"  No recorded relationships found for {canonical}.\n")
        return True
        
    # Calculate statistics
    total_connections = len(edges)
    avg_sentiment = sum(e["sentiment"] for e in edges) / total_connections if total_connections else 0.0
    
    sentiment_icon = "🟢 Loyal/Positive" if avg_sentiment > 0.3 else ("🔴 Hostile/Negative" if avg_sentiment < -0.3 else "🟡 Mixed/Neutral")
    print(f"• Total Direct Connections : {total_connections}")
    print(f"• Net Emotional Affinity   : {avg_sentiment:+.2f} ({sentiment_icon})")
    print("-" * 85)
    
    categories = {
        "kinship": "👨‍👩‍👧‍👦 Kinship & Bloodline",
        "bond": "✨ Soul-Bond & Animi",
        "comrade": "🛡️ Comrades & Allies",
        "romance": "💖 Romance & Courtship",
        "mentorship": "📜 Mentorship & Guidance",
        "rivalry": "⚔️ Rivalry & Nemeses",
        "tension": "⚡ Friction & Jealousy",
        "deception": "🎭 Deception & Conspiracy",
        "alliance": "🤝 Strategic Alliances"
    }
    
    order_keys = list(categories.keys())
    edges.sort(key=lambda x: (
        order_keys.index(x["relation_type"]) if x["relation_type"] in order_keys else 99,
        -x["sentiment"]
    ))
    
    table_rows = []
    for e in edges:
        cat_label = categories.get(e["relation_type"], e["relation_type"].capitalize())
        sub_label = e["sub_type"].replace("_", " ").title()
        
        sent = e["sentiment"]
        if sent >= 0.8:
            sent_str = f"🟢 +{sent:.2f}"
        elif sent > 0.0:
            sent_str = f"🌱 +{sent:.2f}"
        elif sent == 0.0:
            sent_str = f"⚪  0.00"
        elif sent > -0.6:
            sent_str = f"🟠 {sent:.2f}"
        else:
            sent_str = f"🔴 {sent:.2f}"
            
        direction_icon = "↔️" if e["symmetry"] == "symmetric" else ("➡️" if e["direction"] == "outbound" else "⬅️")
        
        dyn = e["dynamic_state"] or "-"
        if len(dyn) > 42:
            dyn = dyn[:39] + "..."
            
        table_rows.append([
            f"{direction_icon} {e['target']}",
            cat_label,
            sub_label,
            sent_str,
            e["active_phase"],
            dyn
        ])
        
    headers = ["Connected Entity", "Dimension", "Sub-Type", "Affinity", "Resolved Anchor", "Dynamic Event / Subtext"]
    if HAS_TABULATE:
        print(tabulate(table_rows, headers=headers, tablefmt="rounded_grid"))
    else:
        print(f"{'Entity':<24} | {'Dimension':<18} | {'Sub-Type':<18} | {'Affinity':<10} | {'Anchor':<16}")
        print("-" * 95)
        for r in table_rows:
            print(f"{r[0]:<24} | {r[1]:<18} | {r[2]:<18} | {r[3]:<10} | {r[4]:<16}")
            
    print("=" * 85 + "\n")
    return True


def find_relationship_path(char_a: str, char_b: str, data: Dict[str, Any], ao_year: Optional[int] = None) -> bool:
    """Find the shortest connection path between two characters using BFS at a given era."""
    all_names = get_all_characters(data)
    name_a = resolve_character_name(char_a, all_names)
    name_b = resolve_character_name(char_b, all_names)
    
    if not name_a:
        print(f"❌ Character '{char_a}' not found.")
        return False
    if not name_b:
        print(f"❌ Character '{char_b}' not found.")
        return False
        
    if name_a == name_b:
        print(f"\nℹ️  '{name_a}' is the same character (0 degrees of separation).\n")
        return True
        
    graph = build_adjacency_graph(data, ao_year=ao_year)
    
    queue = deque([(name_a, [])])
    visited = {name_a}
    
    found_path = None
    while queue:
        curr, path = queue.popleft()
        if curr == name_b:
            found_path = path
            break
            
        for edge in graph.get(curr, []):
            nxt = edge["target"]
            if nxt not in visited:
                visited.add(nxt)
                queue.append((nxt, path + [(curr, edge, nxt)]))
                
    print("\n" + "=" * 75)
    print(f"  🧭 RELATIONSHIP PATHFINDER: {name_a} ➔ {name_b}")
    if ao_year:
        print(f"      Chronological Anchor: {ao_year} AO")
    print("=" * 75)
    
    if not found_path:
        print(f"  ❌ No relationship path exists between '{name_a}' and '{name_b}'.")
        print("  These characters belong to disconnected social networks.")
        print("=" * 75 + "\n")
        return False
        
    print(f"  ✓ Connected by {len(found_path)} degree(s) of separation:\n")
    for i, (src, edge, tgt) in enumerate(found_path, 1):
        rel_type = edge["relation_type"].upper()
        sub = edge["sub_type"].replace("_", " ")
        sent = edge["sentiment"]
        sent_sign = f"+{sent:.2f}" if sent >= 0 else f"{sent:.2f}"
        
        arrow = "<--->" if edge["symmetry"] == "symmetric" else "--->"
        print(f"  [{i}] {src}")
        print(f"      {arrow} [{rel_type}: {sub} | affinity: {sent_sign} | anchor: {edge['active_phase']}]")
        if edge.get("dynamic_state"):
            print(f"      💬 Subtext: \"{edge['dynamic_state']}\"")
        if edge.get("narrative_rule"):
            print(f"      📌 Writing Rule: {edge['narrative_rule']}")
        print(f"      {arrow} {tgt}")
        if i < len(found_path):
            print()
            
    print("=" * 75 + "\n")
    return True


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

def export_mermaid_diagram(data: Dict[str, Any], ao_year: Optional[int] = None) -> str:
    """Generate clean Mermaid diagram string of the relationship network."""
    lines = ["graph TD", "    %% Convergence Canonical Relationship Graph", ""]
    
    lines.append("    classDef kinship fill:#e8f8f5,stroke:#1abc9c,stroke-width:2px,color:#16a085;")
    lines.append("    classDef comrade fill:#eaf2f8,stroke:#2980b9,stroke-width:2px,color:#2471a3;")
    lines.append("    classDef romance fill:#fdf2e9,stroke:#e67e22,stroke-width:2px,color:#d35400;")
    lines.append("    classDef rivalry fill:#fdedec,stroke:#c0392b,stroke-width:2px,color:#922b21;")
    lines.append("    classDef tension fill:#fcf3cf,stroke:#f39c12,stroke-width:2px,color:#b7950b;")
    lines.append("    classDef mentor fill:#f4ecf7,stroke:#8e44ad,stroke-width:2px,color:#6c3483;")
    lines.append("")
    
    def sanitize_id(name: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_]", "_", name)
        
    seen_edges = set()
    for rel in data.get("relationships", []):
        src = rel["source"]
        tgt = rel["target"]
        edge_key = tuple(sorted([src, tgt]))
        
        is_sym = rel.get("symmetry") == "symmetric"
        if is_sym and edge_key in seen_edges:
            continue
        seen_edges.add(edge_key)
        
        active = resolve_active_relationship(rel, ao_year=ao_year)
        id_src = sanitize_id(src)
        id_tgt = sanitize_id(tgt)
        label = active["sub_type"].replace("_", " ")
        
        arrow = "---" if is_sym else "-->"
        lines.append(f'    {id_src}["{src}"] {arrow}|"{label}"| {id_tgt}["{tgt}"]')
        
    return "\n".join(lines)


# ==============================================================================
# SQLITE SEEDING & SYNC
# ==============================================================================

def sync_relationships_to_db(data: Dict[str, Any]) -> bool:
    """Seed relationship records into SQLite character_relations table."""
    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}. Run `./ax db` or `./ax update` first.")
        return False
        
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Ensure schema is up to date
    cur.execute("DROP TABLE IF EXISTS character_relations;")
    cur.execute("""
    CREATE TABLE character_relations (
        relation_id TEXT PRIMARY KEY,
        source_char TEXT NOT NULL,
        target_char TEXT NOT NULL,
        relation_type TEXT NOT NULL,
        sub_type TEXT,
        sentiment REAL DEFAULT 0.0,
        symmetry TEXT DEFAULT 'directed',
        active_phase TEXT DEFAULT 'All',
        dynamic_state TEXT,
        timeline_json TEXT,
        notes TEXT
    );
    """)
    
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rel_source ON character_relations(source_char);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rel_target ON character_relations(target_char);")
    
    cur.execute("DELETE FROM character_relations;")
    inserted = 0
    for rel in data.get("relationships", []):
        cur.execute("""
            INSERT OR REPLACE INTO character_relations 
            (relation_id, source_char, target_char, relation_type, sub_type, sentiment, symmetry, active_phase, dynamic_state, timeline_json, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rel.get("id"),
            rel.get("source"),
            rel.get("target"),
            rel.get("relation_type"),
            rel.get("sub_type"),
            rel.get("sentiment", 0.0),
            rel.get("symmetry", "directed"),
            rel.get("active_phase", "All"),
            rel.get("dynamic_state", ""),
            json.dumps(rel.get("timeline", [])),
            rel.get("notes", "")
        ))
        inserted += 1
        
    conn.commit()
    conn.close()
    print(f"  ✓ Synchronized {inserted} character relationships into SQLite table 'character_relations'.")
    return True


# ==============================================================================
# RELATIONSHIP CRUD & TOPOLOGY SEPARATION
# ==============================================================================

def check_relationship_exists(
    char_a_query: str,
    char_b_query: str,
    data: Dict[str, Any],
    ao_year: Optional[int] = None,
    book: Optional[int] = None,
    chapter: Optional[int] = None,
    story: Optional[str] = None,
    phase: Optional[str] = None,
    scene: Optional[int] = None
) -> bool:
    """Check and cleanly separate whether a relationship exists (topology) vs what it is (typology & state) at a specific time anchor."""
    all_names = get_all_characters(data)
    name_a = resolve_character_name(char_a_query, all_names) or char_a_query.strip()
    name_b = resolve_character_name(char_b_query, all_names) or char_b_query.strip()
    
    if name_a not in all_names or name_b not in all_names:
        print(f"⚠️  One or both characters not found in relationship database:")
        if name_a not in all_names:
            print(f"   • '{char_a_query}' -> unresolved")
        if name_b not in all_names:
            print(f"   • '{char_b_query}' -> unresolved")
        return False
        
    # Build temporal header
    anchor_desc = "Latest / Baseline State"
    if book and chapter:
        anchor_desc = f"Manuscript Anchor: Book {book} Chapter {chapter}"
        if phase:
            anchor_desc += f" [{phase.upper()}]"
        if scene:
            anchor_desc += f" (Scene {scene})"
    elif ao_year:
        anchor_desc = f"World Chronology Anchor: {ao_year} AO"
        if phase:
            anchor_desc += f" [{phase.upper()}]"
    elif story:
        anchor_desc = f"Story Anchor: {story}"

    print("\n" + "=" * 80)
    print(f"  🕸️  RELATIONSHIP TOPOLOGY & ARCHITECTURAL SEPARATION")
    print(f"      Node A : {name_a}")
    print(f"      Node B : {name_b}")
    print(f"      Period : {anchor_desc}")
    print("=" * 80)
    
    # 1. LAYER 1: TOPOLOGY & ADJACENCY (DOES A RELATIONSHIP EXIST?)
    direct_rel = None
    direction = None
    for rel in data.get("relationships", []):
        src = rel.get("source")
        tgt = rel.get("target")
        sym = rel.get("symmetry", "directed")
        if src == name_a and tgt == name_b:
            direct_rel = rel
            direction = "A ➔ B"
            break
        elif src == name_b and tgt == name_a:
            direct_rel = rel
            direction = "B ➔ A" if sym == "directed" else "A ↔ B"
            break
            
    # Calculate BFS degrees of separation
    graph = build_adjacency_graph(data, ao_year=ao_year, book=book, chapter=chapter, story=story, phase=phase, scene=scene)
    dist = -1
    if name_a == name_b:
        dist = 0
    else:
        visited = {name_a}
        queue = deque([(name_a, 0)])
        while queue:
            curr, d = queue.popleft()
            if curr == name_b:
                dist = d
                break
            for edge in graph.get(curr, []):
                nxt = edge["target"]
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append((nxt, d + 1))
                    
    print("\n1️⃣  LAYER 1: GRAPH TOPOLOGY (EXISTENCE & CONNECTIVITY)")
    if direct_rel:
        print(f"  • Direct Adjacency       : ✅ YES (1 degree of separation)")
        print(f"  • Edge Orientation       : {direction} ({direct_rel.get('symmetry', 'directed').capitalize()})")
    elif dist > 0:
        print(f"  • Direct Adjacency       : ❌ NO (Indirectly connected)")
        print(f"  • Degrees of Separation  : 🌐 {dist} hop(s) via intermediate characters")
        print(f"  💡 Run `./ax relations path \"{name_a}\" \"{name_b}\"` to trace the intermediate graph walk.")
    else:
        print(f"  • Direct Adjacency       : ❌ NO (Disconnected)")
        print(f"  • Graph Separation       : ∞ (No relational path found in registry)")
        print("=" * 80 + "\n")
        return False

    # 2. LAYER 2: ONTOLOGICAL TYPOLOGY (WHAT IS THE RELATIONSHIP STRUCTURALLY IN THIS PERIOD?)
    if direct_rel:
        # Resolve active dynamic state for THIS EXACT TIME PERIOD
        active = resolve_active_relationship(direct_rel, ao_year=ao_year, book=book, chapter=chapter, story=story, phase=phase, scene=scene)
        sent = active["sentiment"]
        sent_str = f"+{sent:.2f}" if sent >= 0 else f"{sent:.2f}"
        color = "🟢" if sent >= 0.5 else ("🌱" if sent >= 0.0 else ("🟠" if sent >= -0.5 else "🔴"))
        
        print(f"\n2️⃣  LAYER 2: ONTOLOGICAL TYPOLOGY (STRUCTURAL NATURE IN {anchor_desc.upper()})")
        print(f"  • Active Domain          : {active.get('relation_type', direct_rel.get('relation_type')).upper()}")
        print(f"  • Active Sub-Type        : {active.get('sub_type', direct_rel.get('sub_type', '')).replace('_', ' ').title()}")
        if direct_rel.get("symmetry") == "directed" and direct_rel.get("reverse_sub_type"):
            print(f"  • Reciprocal Role        : {direct_rel.get('reverse_sub_type', '').replace('_', ' ').title()}")
        print(f"  • Structural Symmetry    : {direct_rel.get('symmetry', 'directed').capitalize()}")
        print(f"  • Permanent Lore Notes   : {direct_rel.get('notes', 'None recorded.')}")

        # 3. LAYER 3: DYNAMIC TIMELINE STATE (WHAT IS IT DOING RIGHT NOW IN THIS PERIOD?)
        print(f"\n3️⃣  LAYER 3: DYNAMIC TIMELINE STATE (ACTIVE TENSION & NARRATIVE SLICE)")
        print(f"  • Emotional Affinity     : {color} {sent_str} (scale: -1.0 to +1.0)")
        print(f"  • Active Dynamic State   : {active.get('dynamic_state', direct_rel.get('dynamic_state', ''))}")
        if active.get("narrative_rule"):
            print(f"  • Active Writing Rule    : ✍️  {active['narrative_rule']}")
        print(f"  • Resolved Milestone     : {active.get('resolved_via', 'baseline')}")
        
        # Check for Intra-Chapter Turning Points
        intra = active.get("intra_slices", [])
        if len(intra) > 1 and not phase and not scene:
            print(f"\n  ⚡ INTRA-CHAPTER TURNING POINT DETECTED ({len(intra)} distinct phases in Book {book} Ch {chapter}):")
            for idx, s in enumerate(intra, 1):
                p_label = s.get("phase", f"phase_{idx}").upper()
                sc_label = f" (Scene {s['scene']})" if s.get("scene") else ""
                s_sent = s.get("sentiment", 0.0)
                s_col = "🟢" if s_sent >= 0.5 else ("🌱" if s_sent >= 0.0 else ("🟠" if s_sent >= -0.5 else "🔴"))
                print(f"     {s_col} [{p_label}{sc_label}] {s.get('relation_type', '').upper()} / {s.get('sub_type', '').replace('_', ' ').title()} (Affinity: {s_sent:+.2f})")
                print(f"        💬 Trigger/State : {s.get('trigger_event', '')}")
                if s.get("narrative_rule"):
                    print(f"        ✍️ Narrative Rule: {s['narrative_rule']}")
            print(f"  💡 Use `--phase pre` or `--phase post` to pin to a specific phase of this turning point.")

        timeline = direct_rel.get("timeline", [])
        print(f"\n  • Full Timeline Trajectory ({len(timeline)} recorded milestone slices):")
        for idx, s in enumerate(timeline, 1):
            t_type = s.get("anchor_type", "chronological")
            if t_type == "chapter":
                t_label = f"Book {s.get('book')} Ch {s.get('from_ch')}–{s.get('to_ch') or '+'}"
            else:
                t_label = f"{s.get('ao_year_start')}–{s.get('ao_year_end') or 'present'} AO"
            if s.get("phase"):
                t_label += f" [{s.get('phase')}]"
            s_sent = s.get("sentiment", 0.0)
            s_color = "🟢" if s_sent >= 0.5 else ("🌱" if s_sent >= 0.0 else ("🟠" if s_sent >= -0.5 else "🔴"))
            is_active_slice = (active.get("resolved_via") in (t_label, s.get("trigger_event", ""))) or (t_label in active.get("resolved_via", ""))
            marker = "👉 [ACTIVE]" if is_active_slice else "  "
            print(f"   {marker} [{idx}] {t_label:<25} | {s_color} {s_sent:>+5.2f} | {s.get('relation_type', '').upper()} ({s.get('sub_type', '').replace('_', ' ')}): {s.get('trigger_event', '')}")
            if s.get("narrative_rule"):
                print(f"                         ✍️  Rule: {s['narrative_rule']}")
            
    print("=" * 80 + "\n")
    return True


def save_relationships_data(data: Dict[str, Any]) -> bool:
    """Save canonical relationships dictionary back to SSOT JSON file."""
    try:
        data["total_relationships"] = len(data.get("relationships", []))
        RELATIONSHIPS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return True
    except Exception as e:
        print(f"❌ Failed to save relationships file: {e}", file=sys.stderr)
        return False


def add_relationship(
    source_query: str,
    target_query: str,
    relation_type: str,
    sub_type: str = "",
    sentiment: float = 0.0,
    symmetry: str = "directed",
    dynamic_state: str = "",
    notes: str = "",
    data: Optional[Dict[str, Any]] = None,
    save_to_disk: bool = True
) -> bool:
    """Add a new canonical character relationship and auto-sync to SQLite."""
    if data is None:
        data = load_relationships_data()
        
    all_names = get_all_characters(data)
    src_resolved = resolve_character_name(source_query, all_names) or source_query.strip()
    tgt_resolved = resolve_character_name(target_query, all_names) or target_query.strip()
    
    if src_resolved == tgt_resolved:
        print("❌ Cannot create a relationship between a character and themselves.")
        return False
        
    # Check if edge already exists
    for rel in data.get("relationships", []):
        if (rel["source"] == src_resolved and rel["target"] == tgt_resolved) or \
           (rel.get("symmetry") == "symmetric" and rel["source"] == tgt_resolved and rel["target"] == src_resolved):
            print(f"⚠️  Relationship already exists between '{src_resolved}' and '{tgt_resolved}' (ID: {rel['id']}).")
            print("   Use `./ax relations update` to modify active parameters.")
            return False
            
    # Generate slug ID
    def slugify(text: str) -> str:
        s = text.lower().replace("the", "").replace("of", "")
        s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
        parts = s.split("_")
        return parts[0] if parts else "rel"
        
    rel_id = f"rel_{slugify(src_resolved)}_{slugify(tgt_resolved)}"
    # Check for ID collisions
    existing_ids = {r["id"] for r in data.get("relationships", [])}
    if rel_id in existing_ids:
        rel_id = f"{rel_id}_{len(existing_ids)+1}"
        
    new_rel = {
        "id": rel_id,
        "source": src_resolved,
        "target": tgt_resolved,
        "relation_type": relation_type.lower(),
        "sub_type": sub_type.lower().replace(" ", "_") if sub_type else "associated",
        "sentiment": max(-1.0, min(1.0, float(sentiment))),
        "symmetry": "symmetric" if symmetry.lower() in ("symmetric", "sym", "mutual") else "directed",
        "active_phase": "All",
        "dynamic_state": dynamic_state or "Formed in canon.",
        "notes": notes,
        "timeline": []
    }
    
    data.setdefault("relationships", []).append(new_rel)
    if save_to_disk:
        if save_relationships_data(data):
            sync_relationships_to_db(data)
            print(f"  ✓ Added relationship '{new_rel['id']}': {src_resolved} ➔ {tgt_resolved} [{relation_type}] (Affinity: {sentiment:+.2f})")
            return True
        return False
    return True


def update_relationship(
    source_query: str,
    target_query: str,
    sentiment: Optional[float] = None,
    dynamic_state: Optional[str] = None,
    relation_type: Optional[str] = None,
    sub_type: Optional[str] = None,
    notes: Optional[str] = None,
    rule: Optional[str] = None,
    ao_year: Optional[int] = None,
    book: Optional[int] = None,
    chapter: Optional[int] = None,
    phase: Optional[str] = None,
    scene: Optional[int] = None,
    story: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    save_to_disk: bool = True
) -> bool:
    """Update active dynamic state, sentiment, or a specific timeframe milestone of an existing relationship."""
    if data is None:
        data = load_relationships_data()
        
    all_names = get_all_characters(data)
    src_resolved = resolve_character_name(source_query, all_names) or source_query.strip()
    tgt_resolved = resolve_character_name(target_query, all_names) or target_query.strip()
    
    matched = None
    for rel in data.get("relationships", []):
        if (rel["source"] == src_resolved and rel["target"] == tgt_resolved) or \
           (rel["source"] == tgt_resolved and rel["target"] == src_resolved):
            matched = rel
            break
            
    if not matched:
        print(f"❌ No existing relationship found between '{src_resolved}' and '{tgt_resolved}'.")
        return False

    is_temporal_update = any(x is not None for x in (ao_year, book, chapter, phase, scene, story))

    if is_temporal_update:
        # Search for existing milestone slice in timeline
        target_slice = None
        for s in matched.get("timeline", []):
            if book is not None and chapter is not None:
                if s.get("book") == book and (s.get("from_ch", 1) <= chapter <= (s.get("to_ch") or 9999)):
                    if phase is not None and s.get("phase", "").lower() != phase.lower():
                        continue
                    if scene is not None and s.get("scene") != scene:
                        continue
                    target_slice = s
                    break
            elif ao_year is not None:
                start = s.get("ao_year_start")
                end = s.get("ao_year_end") or 9999
                if start is not None and start <= ao_year <= end:
                    if phase is not None and s.get("phase", "").lower() != phase.lower():
                        continue
                    target_slice = s
                    break
            elif story is not None and s.get("story") == story:
                target_slice = s
                break

        if target_slice is not None:
            # Modify existing slice
            if sentiment is not None:
                target_slice["sentiment"] = max(-1.0, min(1.0, float(sentiment)))
            if dynamic_state is not None:
                target_slice["trigger_event"] = dynamic_state
            if relation_type is not None:
                target_slice["relation_type"] = relation_type.lower()
            if sub_type is not None:
                target_slice["sub_type"] = sub_type.lower().replace(" ", "_")
            if rule is not None:
                target_slice["narrative_rule"] = rule
            if phase is not None:
                target_slice["phase"] = phase.lower()
            if scene is not None:
                target_slice["scene"] = scene
            action_desc = f"Updated timeframe milestone slice [{target_slice.get('trigger_event', '')}]"
        else:
            # Create new milestone slice
            anchor_type = "chapter" if (book or chapter) else "chronological"
            new_slice = {
                "anchor_type": anchor_type,
                "ao_year_start": ao_year,
                "ao_year_end": ao_year,
                "story": story,
                "book": book,
                "from_ch": chapter or 1,
                "to_ch": chapter,
                "phase": phase.lower() if phase else None,
                "scene": scene,
                "relation_type": (relation_type.lower() if relation_type else matched.get("relation_type", "alliance")),
                "sub_type": (sub_type.lower().replace(" ", "_") if sub_type else matched.get("sub_type", "")),
                "sentiment": (max(-1.0, min(1.0, float(sentiment))) if sentiment is not None else matched.get("sentiment", 0.0)),
                "trigger_event": dynamic_state or "Milestone reached",
                "narrative_rule": rule or ""
            }
            new_slice = {k: v for k, v in new_slice.items() if v is not None}
            matched.setdefault("timeline", []).append(new_slice)
            target_slice = new_slice
            action_desc = f"Created new timeframe milestone slice [{new_slice.get('trigger_event', '')}]"
    else:
        # Global Baseline Update
        if sentiment is not None:
            matched["sentiment"] = max(-1.0, min(1.0, float(sentiment)))
        if dynamic_state is not None:
            matched["dynamic_state"] = dynamic_state
        if relation_type is not None:
            matched["relation_type"] = relation_type.lower()
        if sub_type is not None:
            matched["sub_type"] = sub_type.lower().replace(" ", "_")
        if notes is not None:
            matched["notes"] = notes
        action_desc = "Updated global baseline state"

    if save_to_disk:
        if save_relationships_data(data):
            sync_relationships_to_db(data)
            print(f"  ✓ {action_desc} for '{matched['id']}': {src_resolved} ↔ {tgt_resolved}")
            if is_temporal_update and target_slice:
                time_lbl = f"Book {book} Ch {chapter}" if (book and chapter) else (f"{ao_year} AO" if ao_year else "Timeframe")
                phase_lbl = f" [{phase}]" if phase else ""
                print(f"    Target Timeframe: {time_lbl}{phase_lbl}")
                print(f"    Type: {target_slice.get('relation_type')} / {target_slice.get('sub_type')} | Affinity: {target_slice.get('sentiment', 0.0):+.2f}")
                print(f"    State/Trigger: {target_slice.get('trigger_event', '')}")
                if target_slice.get("narrative_rule"):
                    print(f"    ✍️  Rule: {target_slice['narrative_rule']}")
            else:
                print(f"    Type: {matched['relation_type']} | Affinity: {matched['sentiment']:+.2f} | State: {matched['dynamic_state']}")
            return True
        return False
    return True


def add_timeline_slice(
    source_query: str,
    target_query: str,
    slice_data: Dict[str, Any],
    data: Optional[Dict[str, Any]] = None,
    save_to_disk: bool = True
) -> bool:
    """Append a discrete chronological or chapter milestone slice to an existing relationship."""
    if data is None:
        data = load_relationships_data()
        
    all_names = get_all_characters(data)
    src_resolved = resolve_character_name(source_query, all_names) or source_query.strip()
    tgt_resolved = resolve_character_name(target_query, all_names) or target_query.strip()
    
    matched = None
    for rel in data.get("relationships", []):
        if (rel["source"] == src_resolved and rel["target"] == tgt_resolved) or \
           (rel["source"] == tgt_resolved and rel["target"] == src_resolved):
            matched = rel
            break
            
    if not matched:
        print(f"❌ No existing relationship found between '{src_resolved}' and '{tgt_resolved}'.")
        return False
        
    matched.setdefault("timeline", []).append(slice_data)
    if save_to_disk:
        if save_relationships_data(data):
            sync_relationships_to_db(data)
            print(f"  ✓ Added milestone slice to '{matched['id']}': {slice_data.get('trigger_event', 'Milestone')}")
            return True
        return False
    return True


# ==============================================================================
# CLI RUNNER
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Convergence Character Relationship Graph & Dual-Anchor Continuity Engine")
    parser.add_argument("target", nargs="?", help="Character name or action (path, matrix, audit, exists, add, update, timeline)")
    parser.add_argument("extra", nargs="*", help="Secondary character names or target file")
    parser.add_argument("--year", "-y", type=int, help="Historical Anno Oryn year (e.g. 1050, 1055, 1059, 1064, 1065)")
    parser.add_argument("--book", "-b", type=int, help="Book number (e.g. 1, 2, 3, 4)")
    parser.add_argument("--chapter", "-c", type=int, help="Chapter number (e.g. 18, 23, 26)")
    parser.add_argument("--story", help="Story slug (e.g. the-sun-sanctum-champion, the-stone-child)")
    parser.add_argument("--type", "-t", help="Relationship type (kinship, alliance, comrade, romance, rivalry, tension, mentorship, bond, feud)")
    parser.add_argument("--sub-type", help="Specific relationship sub-type (e.g. devoted_siblings, smuggler_contract)")
    parser.add_argument("--sentiment", type=float, help="Affinity score from -1.0 (mortal enemy) to +1.0 (devoted/loyal)")
    parser.add_argument("--symmetry", choices=["directed", "symmetric"], default="directed", help="Symmetry mode")
    parser.add_argument("--state", help="Active dynamic tension or status")
    parser.add_argument("--notes", help="Permanent canonical background notes")
    parser.add_argument("--event", help="Trigger event for milestone slice")
    parser.add_argument("--rule", help="Strict narrative writing rule for author/LLM")
    parser.add_argument("--phase", help="Intra-chapter phase (e.g. pre, post, opening, climax)")
    parser.add_argument("--scene", type=int, help="Specific scene number within chapter")
    parser.add_argument("--mermaid", "-m", action="store_true", help="Export Mermaid.js diagram")
    parser.add_argument("--sync-db", "-s", action="store_true", help="Sync relationships into SQLite database")
    
    args = parser.parse_args()
    data = load_relationships_data()
    
    if args.sync_db:
        sync_relationships_to_db(data)
        return
        
    if args.mermaid:
        mmd = export_mermaid_diagram(data, ao_year=args.year)
        print(mmd)
        return
        
    if not args.target:
        all_chars = get_all_characters(data)
        print("\n" + "=" * 75)
        print("  CONVERGENCE CHARACTER RELATIONSHIP DUAL-ANCHOR ENGINE")
        print("=" * 75)
        print(f"• Total Canonical Relationships : {len(data.get('relationships', []))}")
        print(f"• Registered Characters in Graph: {len(all_chars)}")
        print("\nInspection Commands:")
        print("  ./ax relations <character>             : Inspect baseline / latest state")
        print("  ./ax relations <char> --chapter 18 -b 4: Inspect state at Book 4 Chapter 18")
        print("  ./ax relations <char> --year 1055      : Inspect state at 1055 AO (Historical)")
        print("  ./ax relations exists <char_a> <char_b>: Topology existence vs typology separation")
        print("  ./ax relations exists <c1> <c2> -b 1 -c 9: Check turning points within a chapter")
        print("  ./ax relations path <char_a> <char_b>  : Find shortest relational path")
        print("  ./ax relations matrix <c1> <c2> <c3>   : Show ensemble cross-matrix")
        print("  ./ax relations audit <chapter.md>      : Audit chapter interpersonal dynamics")
        print("\nAuthoring & CRUD Commands:")
        print("  ./ax relations add <c1> <c2> --type alliance --sentiment 0.8 --state \"Pact formed\"")
        print("  ./ax relations update <c1> <c2> --sentiment -0.5 --state \"Betrayal revealed\"")
        print("  ./ax relations update <c1> <c2> -b 1 -c 9 --phase post --sentiment -1.0")
        print("  ./ax relations timeline <c1> <c2> -b 4 -c 20 --sentiment 0.9 --rule \"Reconciled\"")
        print("  ./ax relations --mermaid               : Print Mermaid diagram")
        print("  ./ax relations --sync-db               : Sync into SQLite DB")
        print("=" * 75 + "\n")
        return
        
    cmd = args.target.lower()
    
    if cmd == "exists":
        if len(args.extra) < 2:
            print("❌ Exists command requires two character names: `./ax relations exists <char_a> <char_b>`")
            return
        check_relationship_exists(
            args.extra[0],
            args.extra[1],
            data,
            ao_year=args.year,
            book=args.book,
            chapter=args.chapter,
            story=args.story,
            phase=args.phase,
            scene=args.scene
        )
    elif cmd == "add":
        if len(args.extra) < 2:
            print("❌ Add command requires two character names: `./ax relations add <char_a> <char_b> --type <type>`")
            return
        if not args.type:
            print("❌ Add command requires `--type <type>` (e.g. kinship, alliance, mentorship, feud, romance, tension).")
            return
        add_relationship(
            args.extra[0],
            args.extra[1],
            relation_type=args.type,
            sub_type=args.sub_type or "",
            sentiment=args.sentiment if args.sentiment is not None else 0.0,
            symmetry=args.symmetry,
            dynamic_state=args.state or "",
            notes=args.notes or "",
            data=data
        )
    elif cmd == "update":
        if len(args.extra) < 2:
            print("❌ Update command requires two character names: `./ax relations update <char_a> <char_b>`")
            return
        update_relationship(
            args.extra[0],
            args.extra[1],
            sentiment=args.sentiment,
            dynamic_state=args.state,
            relation_type=args.type,
            sub_type=args.sub_type,
            notes=args.notes,
            rule=args.rule,
            ao_year=args.year,
            book=args.book,
            chapter=args.chapter,
            phase=args.phase,
            scene=args.scene,
            story=args.story,
            data=data
        )
    elif cmd == "timeline":
        if len(args.extra) < 2:
            print("❌ Timeline command requires two character names: `./ax relations timeline <char_a> <char_b>`")
            return
        anchor_type = "chapter" if (args.book or args.chapter) else "chronological"
        slice_data = {
            "anchor_type": anchor_type,
            "ao_year_start": args.year,
            "ao_year_end": args.year,
            "story": args.story,
            "book": args.book,
            "from_ch": args.chapter or 1,
            "to_ch": args.chapter,
            "phase": args.phase.lower() if args.phase else None,
            "scene": args.scene,
            "relation_type": args.type or "alliance",
            "sub_type": args.sub_type or "",
            "sentiment": args.sentiment if args.sentiment is not None else 0.0,
            "trigger_event": args.event or args.state or "Milestone reached",
            "narrative_rule": args.rule or ""
        }
        slice_data = {k: v for k, v in slice_data.items() if v is not None}
        add_timeline_slice(args.extra[0], args.extra[1], slice_data, data=data)
    elif cmd == "path":
        if len(args.extra) < 2:
            print("❌ Path command requires two character names: `./ax relations path <char_a> <char_b>`")
            return
        find_relationship_path(args.extra[0], args.extra[1], data, ao_year=args.year)
    elif cmd == "matrix":
        if not args.extra:
            print("❌ Matrix command requires at least two character names: `./ax relations matrix <c1> <c2> ...`")
            return
        build_cast_matrix(args.extra, data, ao_year=args.year)
    elif cmd == "audit":
        if not args.extra:
            print("❌ Audit command requires a chapter file: `./ax relations audit <chapter.md>`")
            return
        audit_chapter_relations(Path(args.extra[0]), data)
    else:
        # Default: inspect character with optional time anchor
        inspect_character_relations(
            args.target,
            data,
            ao_year=args.year,
            book=args.book,
            chapter=args.chapter,
            story=args.story,
            phase=args.phase,
            scene=args.scene
        )

if __name__ == "__main__":
    main()

