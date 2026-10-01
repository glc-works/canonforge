"""
Previous chapter continuity hooks and setting sensory palettes.
"""
import re
from pathlib import Path
from typing import Dict, Any, Optional

from canonforge.engines.prep.locator import parse_frontmatter

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
    
    # Generic archetype sensory palettes
    archetypes = {
        "foundry": {
            "atmosphere": "Industrial foundry, forge, and mechanical scrap warrens",
            "smells": ["Hot machine oil", "Spent coal dust", "Acid battery tang", "Solder flux"],
            "sounds": ["Piston thrum", "Hissing pneumatic exhaust", "Rattling iron grates", "Drop-hammers"],
            "textures": ["Gritty soot on palms", "Cold greasy iron", "Rough burlap", "Chilled slate"],
            "lighting": "Flickering forge fires and harsh industrial lanterns."
        },
        "palace": {
            "atmosphere": "Hermetic aristocratic halls and marble galleries",
            "smells": ["Distilled rosewater", "Almond oil", "Old parchment", "Beeswax seals"],
            "sounds": ["Whispering pendulum clockwork", "Muffled boot steps on heavy velvet", "Lead-glass wind hum"],
            "textures": ["Polished marble", "Chilled brass rails", "Heavy silk drapery"],
            "lighting": "Filtered daylight through leaded casements; pale lanterns."
        },
        "wilderness": {
            "atmosphere": "Snowbound alpine clearing and deep forest",
            "smells": ["Pine resin", "Peat smoke", "Wet moss", "Frozen stream water"],
            "sounds": ["Wind in the pines", "Cracking ice on branches", "Distant bird call"],
            "textures": ["Biting sleet against skin", "Rough bark", "Frozen earth"],
            "lighting": "Crisp morning mist; filtered sunlight through canopy."
        },
        "travel": {
            "atmosphere": "Cargo wagon traversing rugged terrain",
            "smells": ["Tarred canvas", "Axle grease", "Road dust", "Damp horse sweat"],
            "sounds": ["Rhythmic clank of crawler tracks", "Groaning wood joints", "Wind over open ground"],
            "textures": ["Coarse potato sack", "Damp leather reins", "Vibrating floorboards"],
            "lighting": "Gloom under overcast skies; swinging brass oil lantern."
        },
        "academy": {
            "atmosphere": "Ancient library and stone cloister halls",
            "smells": ["Dried ink", "Old vellum", "Fresh cedar shavings", "Faint candlewax"],
            "sounds": ["Rustle of heavy pages", "Chime of bell tower", "Echoing corridor footsteps"],
            "textures": ["Smooth stone desks", "Warm wool cloaks", "Bound leather folios"],
            "lighting": "Warm candlelight and tall arched stained-glass windows."
        }
    }
    
    for key, pal in archetypes.items():
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

