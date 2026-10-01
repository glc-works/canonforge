#!/usr/bin/env python3
"""
scene_prep.py

Convergence Studio: Instant Scene & Authoring Brief Generator (OKF v0.3).
Synthesizes SSOT Lore, Previous Chapter Continuity Hooks, Active Relational Writing Rules,
Biometric Invariants, and Setting Sensory Palettes into an authoring cockpit in <0.02s.

Usage:
    ./ax prep
    ./ax prep ch09-the-cut.md
    ./ax prep "the-cut"
    ./ax prep ch11-the-salt-trunk-merchant.md
    ./ax prep ch20-the-highland-flame-wyrm.md
    ./ax prep --prompt ch09
    ./ax prep --json ch09
"""

import sys
import os
import re
import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Set

SCRIPT_DIR = Path(__file__).resolve().parent
CONVERGENCE_DIR = SCRIPT_DIR.parent
MANUSCRIPT_DIR = CONVERGENCE_DIR / "manuscript"
WIKI_DIR = CONVERGENCE_DIR / "wiki"
PLACES_DIR = WIKI_DIR / "terms" / "places"

# Import helper modules
try:
    import character_relations as cr
    HAS_CR = True
except ImportError:
    HAS_CR = False

try:
    import character_profile as cp
    HAS_CP = True
except ImportError:
    HAS_CP = False

try:
    import book_navigator as bn
    HAS_BN = True
except ImportError:
    HAS_BN = False


# ==============================================================================
# TARGET CHAPTER RESOLUTION
# ==============================================================================

def find_chapter_target(
    query: Optional[str] = None,
    book_filter: Optional[str] = None,
    chapter_query: Optional[str] = None,
    allow_interactive: bool = True
) -> Optional[Path]:
    """Find target chapter markdown file by exact path, book+chapter, or filename query."""
    if HAS_BN:
        # Check if query is a book or book_filter is provided
        target_1 = book_filter or query
        target_2 = chapter_query if (book_filter or (query and bn.resolve_book(query))) else None
        res = bn.resolve_interactive_or_cli(target_1, target_2, allow_interactive=allow_interactive)
        if res:
            return res[1]
    if not query:
        # Check git modified chapters first
        git_mod = get_git_modified_chapters()
        if git_mod:
            if book_filter:
                filtered = [f for f in git_mod if book_filter.lower() in str(f).lower()]
                if filtered:
                    return filtered[0]
            return git_mod[0]
            
        # Fallback to the latest active chapter
        all_chaps = list(MANUSCRIPT_DIR.rglob("*.md"))
        valid = [f for f in all_chaps if "chapters" in str(f) and not f.name.startswith("compiled") and not f.name.startswith(".")]
        if valid:
            valid.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return valid[0]
        return None

    # Check direct file path
    p = Path(query)
    if p.exists() and p.is_file():
        return p

    p_conv = CONVERGENCE_DIR / query
    if p_conv.exists() and p_conv.is_file():
        return p_conv

    # Substring / stem match across manuscript
    q_clean = query.lower().replace(".md", "").strip()
    all_chaps = list(MANUSCRIPT_DIR.rglob("*.md"))
    valid = [f for f in all_chaps if "chapters" in str(f) and not f.name.startswith("compiled") and not f.name.startswith(".")]
    
    # 1. Exact match on stem or filename
    exact = [f for f in valid if f.stem.lower() == q_clean or f.name.lower() == q_clean]
    if exact:
        if book_filter:
            b_exact = [f for f in exact if book_filter.lower() in str(f).lower()]
            if b_exact:
                return b_exact[0]
        return exact[0]

    # 2. Number prefix match (e.g. "ch09" -> ch09-*.md)
    m = re.search(r"\b(?:ch)?(\d+)\b", q_clean)
    if m:
        num = int(m.group(1))
        prefix = f"ch{num:02d}-"
        num_matches = [f for f in valid if f.name.startswith(prefix)]
        if num_matches:
            if book_filter:
                b_num = [f for f in num_matches if book_filter.lower() in str(f).lower()]
                if b_num:
                    return b_num[0]
            return num_matches[0]

    # 3. Substring match
    sub = [f for f in valid if q_clean in f.stem.lower()]
    if sub:
        if book_filter:
            b_sub = [f for f in sub if book_filter.lower() in str(f).lower()]
            if b_sub:
                return b_sub[0]
        return sub[0]

    return None


resolve_target_chapter = find_chapter_target


def get_git_modified_chapters() -> List[Path]:
    """Retrieve list of currently modified manuscript chapters from git."""
    import subprocess
    modified = []
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain", "manuscript/"],
            cwd=str(CONVERGENCE_DIR),
            capture_output=True,
            text=True
        )
        for line in res.stdout.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2:
                fpath = CONVERGENCE_DIR / parts[-1]
                if fpath.suffix == ".md" and "chapters" in str(fpath) and fpath.exists():
                    modified.append(fpath)
    except Exception:
        pass
    return modified


# ==============================================================================
# FRONTMATTER & METADATA EXTRACTION
# ==============================================================================

def parse_frontmatter(text: str) -> Dict[str, Any]:
    """Extract YAML frontmatter into a clean dictionary."""
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    
    yaml_raw = parts[1]
    meta: Dict[str, Any] = {}
    current_list_key = None
    
    for line in yaml_raw.splitlines():
        line_clean = line.strip()
        if not line_clean or line_clean.startswith("#"):
            continue
            
        if line_clean.startswith("- ") and current_list_key:
            val = line_clean[2:].strip().strip('"').strip("'")
            meta.setdefault(current_list_key, []).append(val)
            continue
            
        if ":" in line_clean:
            current_list_key = None
            key, val = line_clean.split(":", 1)
            key = key.strip()
            val = val.strip()
            
            if val == "":
                current_list_key = key
                meta[key] = []
            else:
                val_clean = val.strip('"').strip("'")
                if val_clean.isdigit():
                    meta[key] = int(val_clean)
                else:
                    meta[key] = val_clean
                    
    return meta


def extract_previous_chapter_hook(current_path: Path, current_ch_num: int) -> Optional[Dict[str, Any]]:
    """Locate Chapter N-1 in the same directory/book and extract its concluding 250 words."""
    if current_ch_num <= 1:
        return None
        
    parent_dir = current_path.parent
    prev_num = current_ch_num - 1
    
    # Find matching prev chapter file
    prev_prefix = f"ch{prev_num:02d}-"
    prev_file = None
    for f in parent_dir.glob("*.md"):
        if f.name.startswith(prev_prefix):
            prev_file = f
            break
            
    if not prev_file:
        # Try finding in parent_dir's siblings if structured by acts
        for f in parent_dir.parent.rglob("*.md"):
            if f.name.startswith(prev_prefix) and "chapters" in str(f):
                prev_file = f
                break
                
    if not prev_file or not prev_file.exists():
        return None
        
    try:
        raw = prev_file.read_text(encoding="utf-8")
        # Strip frontmatter
        body = raw.split("---", 2)[2].strip() if raw.startswith("---") and len(raw.split("---", 2)) >= 3 else raw
        # Clean markdown headers and formatting
        clean_paras = [p.strip() for p in body.split("\n\n") if p.strip() and not p.strip().startswith("#")]
        if not clean_paras:
            return None
            
        # Get last 2-3 paragraphs
        last_paras = clean_paras[-3:]
        hook_text = "\n\n".join(last_paras)
        words = hook_text.split()
        if len(words) > 280:
            hook_text = " ".join(words[-260:])
            
        return {
            "prev_file": prev_file.name,
            "prev_ch_num": prev_num,
            "hook_text": hook_text
        }
    except Exception:
        return None


# ==============================================================================
# SETTING & SENSORY PALETTE RESOLUTION
# ==============================================================================

def get_setting_sensory_palette(setting_name: str) -> Dict[str, Any]:
    """Retrieve canonical sensory signatures for the setting."""
    s_lower = setting_name.lower()
    
    # Canonical sensory palettes for known Convergence regions
    palettes = {
        "sub-six": {
            "atmosphere": "Subterranean industrial foundry & scrap warrens",
            "smells": ["Seal-tallow grease", "Spent anthracite coal", "Acid battery vinegar", "Solder flux"],
            "sounds": ["Hydraulic steam thrums", "Hissing pneumatic exhaust", "Rattling iron grates", "Drop-hammers"],
            "textures": ["Frazil ice slush", "Cold greasy iron", "Rough burlap", "Chilled slate"],
            "lighting": "Sodium animus tubes behind thick wire-mesh; flickering forge fires."
        },
        "high spire": {
            "atmosphere": "Hermetic aristocratic halls of House Vohr & Synod scriveners",
            "smells": ["Distilled rosewater", "Almond clock oil", "Old warrant parchment", "Wax seals"],
            "sounds": ["Whispering pendulum clockwork", "Muffled boot steps on heavy velvet", "Lead-glass wind hum"],
            "textures": ["Polished Carrara marble", "Chilled brass rails", "Heavy mourning silk"],
            "lighting": "Filtered daylight through leaded casements; pale sodium lanterns."
        },
        "willow": {
            "atmosphere": "Snowbound alpine clearing; frozen mountain watermill",
            "smells": ["Pine resin", "Peat smoke", "Sulfur tracking flares", "Frozen river leaf ice"],
            "sounds": ["Blizzard wind howl", "Cracking ice on waterwheel", "Sputtering heated blade hiss"],
            "textures": ["Biting sleet against skin", "Rough ash wood", "Heated katana radiating 800°C"],
            "lighting": "Blinding white blizzard; crimson tracking flare reflections on snow."
        },
        "rust strider": {
            "atmosphere": "Eight-legged crawler cargo wagon traversing the Shingle Coast",
            "smells": ["Cured herring", "Whale grease", "Donkey boiler smoke", "Chicory mud"],
            "sounds": ["Rhythmic clank of eight crawler legs", "Clicking merchant abacus", "Wind off shingle stones"],
            "textures": ["Damp warrant parchment", "Coarse potato sack", "Cold sea spray", "Vibrating deck floor"],
            "lighting": "Damp maritime gloom; swinging brass oil lantern over cargo trunks."
        },
        "high sanctum": {
            "atmosphere": "Ancient marble academy & cloister halls above the cloudline",
            "smells": ["Hot hearth rye bread", "Beeswax polish", "Fresh cedar shavings", "Ozone after aether spark"],
            "sounds": ["Chime of aerial tramway cables", "Fluttering spirit motes", "Distant student laughter", "Crackling hearth"],
            "textures": ["Warm wool cloaks", "Smooth white marble", "Furred animus warmth against collarbone"],
            "lighting": "Golden dawn above cloud deck; glowing hearth-fire amber."
        }
    }
    
    for key, pal in palettes.items():
        if key in s_lower:
            return pal
            
    # Default high-fantasy sensory palette
    return {
        "atmosphere": f"Atmosphere of {setting_name}",
        "smells": ["Cold stone dust", "Pine needles", "Damp wool", "Woodsmoke"],
        "sounds": ["Wind in the pines", "Muffled footsteps", "Distant stream"],
        "textures": ["Rough rock", "Cold air on knuckles", "Coarse fabric"],
        "lighting": "Natural daylight with long mountain shadows."
    }


# ==============================================================================
# BRIEF COMPILATION ENGINE
# ==============================================================================

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
    timeline_str = meta.get("timeline_anchor") or meta.get("timeline") or "Late Winter 1059 AO"
    
    # Parse Anno Oryn year and Book number for relational resolution
    ao_year = None
    y_m = re.search(r"\b(\d{4})\b", timeline_str)
    if y_m:
        ao_year = int(y_m.group(1))
    elif "year 5" in timeline_str.lower():
        ao_year = 1059
        
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
            wiki_data = cp.load_character_from_wiki(char_name)
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

def print_scene_brief(brief: Dict[str, Any]):
    """Render high-clarity terminal authoring cockpit."""
    if "error" in brief:
        print(f"\n❌ Error: {brief['error']}\n")
        return

    print("\n" + "=" * 80)
    print(f"  🎬 AUTHORX SCENE BRIEF: Book {brief['book']} | Ch {brief['chapter']:02d}: \"{brief['title']}\"")
    print(f"      File: {brief['file_name']} | Generated in ⚡ {brief['retrieval_ms']} ms")
    print("=" * 80)

    # 1. Coordinate & Setting
    print(f"\n📍 1. NARRATIVE COORDINATES:")
    print(f"  • Point of View (POV) : 👁️  {brief['pov']}")
    print(f"  • Primary Setting     : 🏰 {brief['setting']}")
    print(f"  • Timeline Anchor     : ⏳ {brief['timeline_anchor']}")
    print(f"  • Target Word Range   : 🎯 3,500 – 4,200 words (Depth Point Anchor)")

    # 2. Continuity Bridge
    print(f"\n🌉 2. CONTINUITY BRIDGE (PREVIOUS CHAPTER HOOK):")
    if brief.get("continuity_bridge"):
        b = brief["continuity_bridge"]
        print(f"  • From Preceding Chapter: {b['prev_file']} (Ch {b['prev_ch_num']:02d})")
        print(f"  • Concluding Physical State:")
        for line in b["hook_text"].splitlines()[-4:]:
            print(f"    > \"{line}\"")
    else:
        print("  • (Opening chapter of book or standalone sequence — fresh scene entry)")

    # 3. Active Interpersonal Relations & Writing Rules
    print(f"\n🤝 3. ACTIVE CAST RELATIONSHIPS & NARRATIVE WRITING RULES:")
    if brief.get("relational_dynamics"):
        for r in brief["relational_dynamics"]:
            sent = r["sentiment"]
            sent_str = f"+{sent:.2f}" if sent >= 0 else f"{sent:.2f}"
            color = "🟢" if sent >= 0.5 else ("🌱" if sent >= 0.0 else ("🟠" if sent >= -0.5 else "🔴"))
            print(f"  • {r['pair']} [{color} {sent_str} | {r['relation_type']}: {r['sub_type']}]")
            print(f"    💬 Active State : {r['dynamic_state']}")
            if r.get("narrative_rule"):
                print(f"    ✍️  WRITING RULE : {r['narrative_rule']}")
            if len(r.get("intra_slices", [])) > 1:
                print(f"    ⚡ INTRA-CHAPTER TURNING POINT: Contains {len(r['intra_slices'])} phases! Use `--phase pre` or `--phase post`.")
            print()
    else:
        print("  • Cast members operate on established solo / ambient dynamics.")

    # 4. Biometric Invariants & Key Physical Markers
    print(f"\n🧬 4. BIOMETRIC INVARIANTS & GEAR (UNBREAKABLE TRUTHS):")
    if brief.get("biometric_invariants"):
        for inv in brief["biometric_invariants"]:
            print(f"  • {inv['name']}:")
            print(f"    - Eyes & Hair : {inv['eye_color']} | {inv['hair_color']}")
            print(f"    - Scar / Mark : {inv['signature_mark']}")
            print(f"    - Gear / Relic: {inv['weapon']}")
            if inv['animus'] != "None":
                print(f"    - Animus Bond   : {inv['animus']}")
            if inv['forbidden']:
                print(f"    - 🚫 FORBIDDEN: {', '.join(inv['forbidden'])}")
    else:
        print("  • All character physical profiles conform to standard OKF records.")

    # 5. Sensory Palette of the Setting
    print(f"\n🌿 5. SETTING SENSORY PALETTE (DAN ABNETT BENCHMARK):")
    s = brief["sensory_palette"]
    print(f"  • Atmospheric Weight: {s['atmosphere']}")
    print(f"  • Scents (Smell)    : 👃 " + ", ".join(s['smells']))
    print(f"  • Acoustics (Sound) : 👂 " + ", ".join(s['sounds']))
    print(f"  • Textures (Touch)  : ✋ " + ", ".join(s['textures']))
    print(f"  • Light & Contrast  : 👁️  {s['lighting']}")

    # 6. Core Scene Objectives
    print(f"\n🎯 6. SCENE CONFLICT & DRAMATIC BEATS:")
    if brief.get("key_conflicts"):
        for c in brief["key_conflicts"]:
            print(f"  [!] {c}")
    else:
        print("  [!] Advance central narrative arc while grounding characters in physical tactile labor.")
        
    print(f"\n  Micro-Beat Pacing Plan:")
    print("  • Beat 1 (0–20%)  : Tactile Sensory Entrance (Physical labor, weather, smell)")
    print("  • Beat 2 (20–60%) : Complication & Dialogue Subtext (Tension, unspoken secrets)")
    print("  • Beat 3 (60–85%) : The Mechanical / Emotional Pivot (Action, reveal, or decision)")
    print("  • Beat 4 (85–100%): Domestic Hearth / Dread Cliffhanger (Bridge to next chapter)")
    print("=" * 80 + "\n")


def generate_llm_authoring_prompt(brief: Dict[str, Any]) -> str:
    """Format Scene Brief as a zero-slop system prompt for Claude / LLM generation."""
    lines = []
    lines.append(f"# SCENE AUTHORING DIRECTIVE: Book {brief['book']} Chapter {brief['chapter']:02d} - \"{brief['title']}\"")
    lines.append("")
    lines.append("## 1. SCENE CONSTRAINTS & COORDINATES")
    lines.append(f"- **POV Character**: {brief['pov']} (Deep 3rd-person limited; strictly NO head-hopping)")
    lines.append(f"- **Primary Setting**: {brief['setting']}")
    lines.append(f"- **Timeline Anchor**: {brief['timeline_anchor']}")
    lines.append(f"- **Word Target**: 3,500 – 4,000 words")
    lines.append("")
    
    if brief.get("continuity_bridge"):
        lines.append("## 2. PREVIOUS CHAPTER HOOK (CONTINUITY BRIDGE)")
        lines.append("You MUST seamlessly continue from this exact physical situation:")
        lines.append("```text")
        lines.append(brief['continuity_bridge']['hook_text'])
        lines.append("```")
        lines.append("")
        
    lines.append("## 3. STRICT INTERPERSONAL WRITING RULES")
    for r in brief.get("relational_dynamics", []):
        lines.append(f"- **{r['pair']}** ({r['relation_type']} / {r['sub_type']}, Affinity: {r['sentiment']:+.2f}):")
        lines.append(f"  - Dynamic: {r['dynamic_state']}")
        if r.get("narrative_rule"):
            lines.append(f"  - **RULE**: {r['narrative_rule']}")
    lines.append("")
    
    lines.append("## 4. BIOMETRIC INVARIANTS (NEVER HALLUCINATE OR CHANGE)")
    for inv in brief.get("biometric_invariants", []):
        lines.append(f"- **{inv['name']}**: Eyes: {inv['eye_color']} | Hair: {inv['hair_color']} | Marks: {inv['signature_mark']} | Weapon: {inv['weapon']}")
        if inv['forbidden']:
            lines.append(f"  - 🚫 NEVER WRITE: {', '.join(inv['forbidden'])}")
    lines.append("")
    
    lines.append("## 5. MANDATORY SENSORY PALETTE")
    s = brief["sensory_palette"]
    lines.append(f"- **Atmosphere**: {s['atmosphere']}")
    lines.append(f"- **Aromas to activate**: {', '.join(s['smells'])}")
    lines.append(f"- **Acoustics**: {', '.join(s['sounds'])}")
    lines.append(f"- **Tactile / Kinetic**: {', '.join(s['textures'])}")
    lines.append("")
    
    lines.append("## 6. ANTI-SLOP & STYLE INVARIANTS")
    lines.append("- ZERO filter words ('he saw', 'she felt', 'he realized', 'could hear'). Describe the world directly.")
    lines.append("- ZERO tricolons ('cold, dark, and silent') or generic AI cliches ('a testament to', 'dance of shadows').")
    lines.append("- Ground emotion in physical reflex, tool handling, and subtextual dialogue.")
    
    return "\n".join(lines)


build_scene_brief = generate_scene_brief
format_scene_prompt = generate_llm_authoring_prompt


# ==============================================================================
# CLI RUNNER
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Convergence Scene & Authoring Brief Generator")
    parser.add_argument("target", nargs="?", help="Book number/slug, chapter path, or query (default: active draft)")
    parser.add_argument("chapter", nargs="?", help="Chapter number, slug, or title (when target is a book)")
    parser.add_argument("--book", "-b", help="Specific book filter slug")
    parser.add_argument("--phase", choices=["pre", "post", "opening", "climax"], help="Pin to intra-chapter phase")
    parser.add_argument("--prompt", "-p", action="store_true", help="Output AI-ready authoring system prompt")
    parser.add_argument("--json", "-j", action="store_true", help="Output raw JSON brief object")
    
    args = parser.parse_args()
    
    brief = generate_scene_brief(args.target, book_filter=args.book, chapter_query=args.chapter, phase=args.phase)
    
    if args.json:
        print(json.dumps(brief, indent=2, ensure_ascii=False))
        return
        
    if args.prompt:
        if "error" in brief:
            print(f"❌ Error: {brief['error']}", file=sys.stderr)
            sys.exit(1)
        print(generate_llm_authoring_prompt(brief))
        return
        
    print_scene_brief(brief)


if __name__ == "__main__":
    main()
