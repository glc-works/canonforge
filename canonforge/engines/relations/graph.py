import difflib
from collections import deque
from typing import Dict, List, Set, Any, Optional, Tuple

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

from canonforge.engines.relations.timeline import resolve_active_relationship, resolve_character_name, get_all_characters

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
    print(f"  🕸️  CANONFORGE RELATIONSHIP DOSSIER: {canonical.upper()}")
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


