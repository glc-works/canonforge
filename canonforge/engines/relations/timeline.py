"""
Relationship Engine Submodule
"""
import sys
import os
import re
import json
import difflib
import sqlite3
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple

from canonforge.core.manifest import find_universe_root

UNIVERSE_DIR = find_universe_root()
RELATIONSHIPS_FILE = UNIVERSE_DIR / "wiki" / "database" / "relationships.json"
DB_PATH = UNIVERSE_DIR / "data" / "game_world.db"
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
            
    # 2. Substring match (e.g. 'Hero' matches 'Hero the Brave')
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

    # 2. Chronological Calendar Year match (if timeline_year provided)
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


def save_relationships_data(data: Dict[str, Any]) -> bool:
    """Save canonical relationships dictionary back to SSOT JSON file."""
    try:
        data["total_relationships"] = len(data.get("relationships", []))
        RELATIONSHIPS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return True
    except Exception as e:
        print(f"❌ Failed to save relationships file: {e}", file=sys.stderr)
        return False


