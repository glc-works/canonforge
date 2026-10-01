"""
Instant scene brief synthesis engine.
"""
import re
import time
from pathlib import Path
from typing import Dict, Any, Optional

from canonforge.core.manifest import find_universe_root

UNIVERSE_DIR = find_universe_root()
MANUSCRIPT_DIR = UNIVERSE_DIR / "manuscript"

from canonforge.engines.prep.locator import find_chapter_target, parse_frontmatter
from canonforge.engines.prep.palettes import extract_previous_chapter_hook, get_setting_sensory_palette

try:
    from canonforge.engines import relations as cr
    HAS_CR = True
except ImportError:
    try:
        import character_relations as cr
        HAS_CR = True
    except ImportError:
        HAS_CR = False

try:
    from canonforge.engines import continuity as cp
    HAS_CP = True
except ImportError:
    try:
        import character_profile as cp
        HAS_CP = True
    except ImportError:
        HAS_CP = False

def generate_scene_brief(
    target_query: Optional[str] = None,
    book_filter: Optional[str] = None,
    chapter_query: Optional[str] = None,
    phase: Optional[str] = None
) -> Dict[str, Any]:
    """Compile exhaustive, zero-hallucination Scene Brief."""
    start_t = time.perf_counter()
    
    chapter_path = find_chapter_target(target_query, book_filter=book_filter, chapter_query=chapter_query)
    if not chapter_path or not chapter_path.exists():
        return {
            "error": f"Target chapter '{target_query or 'active'}' could not be located in manuscript directory."
        }
        
    text = chapter_path.read_text(encoding="utf-8")
    meta = parse_frontmatter(text)
    
    # Extract numerical chapter and book
    title = meta.get("title", chapter_path.stem.replace("-", " ").title())
    book_slug = meta.get("book", chapter_path.parent.parent.name)
    act = meta.get("act", 1)
    
    ch_num = meta.get("chapter")
    if ch_num is None:
        m = re.search(r"ch(\d+)", chapter_path.name)
        ch_num = int(m.group(1)) if m else 1
        
    scene_num = meta.get("scene", 1)
    pov = meta.get("pov_character") or meta.get("pov") or "3rd Person Limited"
    setting = meta.get("setting", "Unspecified Setting")
    timeline_str = meta.get("timeline_anchor") or meta.get("timeline") or "Year 1"
    
    # Parse timeline year and Book number for relational resolution
    ao_year = None
    y_m = re.search(r"\b(\d{1,4})\b", timeline_str)
    if y_m:
        ao_year = int(y_m.group(1))
        
    book_num = 1
    if "book-2" in str(chapter_path) or "book 2" in str(book_slug).lower() or "iron-pilgrimage" in str(book_slug):
        book_num = 2
    elif "book-3" in str(chapter_path) or "disciple" in str(book_slug):
        book_num = 3
    elif "book-4" in str(chapter_path) or "champion" in str(book_slug):
        book_num = 4
    elif "adept" in str(book_slug):
        book_num = 2
    elif "apprentice" in str(book_slug):
        book_num = 1

    # Characters Present
    chars_present = meta.get("characters_present") or meta.get("characters") or []
    if isinstance(chars_present, str):
        chars_present = [c.strip() for c in chars_present.split(",")]
        
    # Key Conflicts
    conflicts = meta.get("key_conflicts", [])
    if isinstance(conflicts, str):
        conflicts = [conflicts]

    # 1. Continuity Bridge (Previous Chapter Hook)
    bridge = extract_previous_chapter_hook(chapter_path, ch_num)
    
    # 2. Relational Dynamics & Writing Rules for Cast
    rel_matrix = []
    if HAS_CR and len(chars_present) >= 2:
        rel_data = cr.load_relationships_data()
        for i in range(len(chars_present)):
            for j in range(i + 1, len(chars_present)):
                c1 = chars_present[i]
                c2 = chars_present[j]
                
                # Check direct relationship
                all_names = cr.get_all_characters(rel_data)
                name_1 = cr.resolve_character_name(c1, all_names) or c1
                name_2 = cr.resolve_character_name(c2, all_names) or c2
                
                matched_rel = None
                for r in rel_data.get("relationships", []):
                    if (r["source"] == name_1 and r["target"] == name_2) or \
                       (r["source"] == name_2 and r["target"] == name_1):
                        matched_rel = r
                        break
                        
                if matched_rel:
                    active = cr.resolve_active_relationship(
                        matched_rel,
                        ao_year=ao_year,
                        book=book_num,
                        chapter=ch_num,
                        phase=phase
                    )
                    rel_matrix.append({
                        "pair": f"{name_1} ↔ {name_2}",
                        "relation_type": active.get("relation_type", "neutral").upper(),
                        "sub_type": active.get("sub_type", "").replace("_", " ").title(),
                        "sentiment": active.get("sentiment", 0.0),
                        "dynamic_state": active.get("dynamic_state", ""),
                        "narrative_rule": active.get("narrative_rule", ""),
                        "intra_slices": active.get("intra_slices", [])
                    })

    # 3. Biometric Invariants & Key Physical Markers
    invariants = []
    if HAS_CP:
        for char_name in chars_present:
            loader = getattr(cp, "load_character_from_wiki", None)
            wiki_data = loader(char_name) if loader else None
            char_title = wiki_data.get("title", char_name) if wiki_data else char_name
            
            # Lookup in KNOWN_INVARIANTS
            inv = None
            clean_t = re.sub(r"[^a-z0-9]", "", char_title.lower())
            for k, val in cp.KNOWN_INVARIANTS.items():
                clean_k = re.sub(r"[^a-z0-9]", "", k.lower())
                if clean_k in clean_t or clean_t in clean_k:
                    inv = val
                    break
            
            if inv:
                invariants.append({
                    "name": char_title,
                    "eye_color": inv.get("eye_color", "Standard"),
                    "hair_color": inv.get("hair_color", "Standard"),
                    "signature_mark": inv.get("signature_mark", "None recorded"),
                    "weapon": inv.get("signature_weapon", "Standard equipment"),
                    "animus": inv.get("bound_animus", "None"),
                    "forbidden": inv.get("forbidden_traits", [])
                })
            elif wiki_data:
                invariants.append({
                    "name": char_title,
                    "eye_color": wiki_data.get("eye_color", "Standard"),
                    "hair_color": wiki_data.get("hair_color", "Standard"),
                    "signature_mark": wiki_data.get("signature_mark", "Standard"),
                    "weapon": wiki_data.get("signature_weapon", "Standard"),
                    "animus": "None",
                    "forbidden": []
                })

    # 4. Setting Sensory Palette
    sensory_palette = get_setting_sensory_palette(setting)

    elapsed_ms = round((time.perf_counter() - start_t) * 1000.0, 2)

    return {
        "file_path": str(chapter_path.resolve()),
        "file_name": chapter_path.name,
        "title": title,
        "book": book_slug,
        "act": act,
        "chapter": ch_num,
        "scene": scene_num,
        "pov": pov,
        "setting": setting,
        "timeline_anchor": timeline_str,
        "ao_year": ao_year,
        "characters_present": chars_present,
        "key_conflicts": conflicts,
        "continuity_bridge": bridge,
        "relational_dynamics": rel_matrix,
        "biometric_invariants": invariants,
        "sensory_palette": sensory_palette,
        "retrieval_ms": elapsed_ms
    }


# ==============================================================================
# REPORTING & PROMPT FORMATTING
# ==============================================================================

