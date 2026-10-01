"""
CRUD operations and timeline slice mutations
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from canonforge.engines.relations.timeline import (
    load_relationships_data, save_relationships_data,
    resolve_character_name, get_all_characters, RELATIONSHIPS_FILE
)

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
        print(f"  💡 Run `./cf relations path \"{name_a}\" \"{name_b}\"` to trace the intermediate graph walk.")
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
            print("   Use `./cf relations update` to modify active parameters.")
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

