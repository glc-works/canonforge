"""
Dynamic entity registry scanner and literary vocabulary lookups.
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent

import hashlib
import sqlite3
import argparse
from pathlib import Path
from collections import Counter
from typing import Dict, List, Tuple, Optional, Any, Set

SCRIPT_DIR = Path(__file__).resolve().parent
CONVERGENCE_DIR = SCRIPT_DIR.parent
MANUSCRIPT_DIR = CONVERGENCE_DIR / "manuscript"
WIKI_DIR = CONVERGENCE_DIR / "wiki"
DATA_DIR = CONVERGENCE_DIR / "data"
DB_PATH = DATA_DIR / "game_world.db"

# ==============================================================================
# STOPWORDS & CANONICAL REGISTRIES
# ==============================================================================

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "as", "is", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "it", "its", "he", "him", "his", "she", "her", "hers", "they",
    "them", "their", "theirs", "we", "us", "our", "ours", "you", "your", "yours", "i",
    "me", "my", "mine", "that", "this", "these", "those", "which", "who", "whom", "whose",
    "what", "where", "when", "why", "how", "all", "any", "both", "each", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so",
    "than", "too", "very", "can", "will", "just", "should", "now", "into", "up", "out",
    "then", "there", "down", "off", "over", "under", "again", "further", "once", "here",
    "said", "one", "like", "back", "through", "could", "would", "about", "above", "across",
    "after", "against", "along", "among", "around", "before", "behind", "below", "beneath",
    "beside", "between", "beyond", "during", "inside", "near", "off", "outside", "past",
    "since", "toward", "towards", "underneath", "until", "upon", "within", "without",
    "even", "still", "well", "way", "much", "many", "must", "might", "shall", "cannot",
    "come", "came", "went", "made", "make", "took", "take", "seen", "saw", "looked",
    "look", "eyes", "hand", "hands", "face", "turned", "knew", "felt", "let", "never",
    "two", "three", "four", "five", "six", "first", "second", "another", "something",
    "nothing", "anything", "everything", "someone", "no one", "anyone", "everyone"
}

CANONICAL_ITEMS = [
    "Conduit-Blade", "Silver Conduit-Blade", "Heated Katana", "Force Eye",
    "Storm-Raptor Force Eye", "River Pebble", "Blue River Pebble", "Hearth-Core",
    "Granite Hearth-Core", "Pneumatic Hammer", "Brass Calipers", "Obsidian Record",
    "Sun-Ember Falcon", "Cartographer's Parchment", "Gilly-Moss", "Chalice of Dawn",
    "Rust Strider", "Salt-Trunk", "Ash-Sluice", "Sledge", "Aether-Flint",
    "Steam-Carbine", "Aether-Lantern", "Pneumatic Spear", "Clockwork Falcon",
    "Tallow-Candle", "Lead-Shim", "Seismograph", "Scabbard", "Waterwheel"
]

# Sensory lexicon from audit_sensory.py
SIGHT_LEX = {
    "shadow", "shadows", "shadowy", "silhouette", "silhouettes", "flicker", "flickering", "flickered",
    "glint", "glinted", "glinting", "lantern", "lanterns", "torch", "torches", "torchlight", "sodium", "glare",
    "pale", "amber", "bronze", "violet", "scarlet", "obsidian", "crimson", "twilight",
    "gloom", "gleam", "gleamed", "gleaming", "quartz", "refraction", "shimmer", "shimmering", "haze",
    "soot", "sooty", "flame", "flames", "dim", "darkness", "blind", "blinding", "dusk",
    "cinder", "cinders", "spark", "sparks", "sparking", "luminous", "iridescent", "murky", "blaze", "blazing",
    "glance", "glanced", "glancing", "gaze", "gazed", "gazing", "stare", "stared", "staring", "sight"
}

SOUND_LEX = {
    "hum", "hummed", "humming", "thrum", "thrummed", "thrumming", "scrape", "scraped",
    "scraping", "screech", "screeched", "screeching", "whistle", "whistled", "whistling",
    "groan", "groaned", "groaning", "groans", "rattle", "rattled", "rattling", "clang", "clanged",
    "clink", "clinked", "drip", "dripped", "dripping", "click", "clicked", "clicking",
    "hiss", "hissed", "hissing", "chime", "chimed", "chiming", "rustle", "rustled",
    "rustling", "roar", "roared", "roaring", "whisper", "whispered", "whispering",
    "reverberate", "reverberated", "reverberating", "crackle", "crackled", "crackling",
    "squeal", "squealed", "grind", "ground", "grinding", "creak", "creaked", "creaking",
    "clatter", "clattered", "snapped", "clop", "clopping", "muffled", "clangor", "shriek", "shrieked", "shrieking",
    "scream", "screamed", "screaming", "screams", "howl", "howled", "howling", "bellow", "bellowed", "bellowing",
    "yell", "yelled", "yelling", "gasp", "gasped", "gasping", "sob", "sobbed", "sobbing", "snarl", "snarled", "snarling"
}

SMELL_LEX = {
    "tallow", "grease", "chicory", "cabbage", "sulfur", "ozone", "copper", "peat",
    "smoke", "smoked", "smoky", "slate", "resin", "vinegar", "whale", "cedar", "pine",
    "rot", "rotten", "rotting", "burnt", "musk", "musky", "mold", "moldy", "musty",
    "brine", "coal", "charcoal", "damp", "stench", "sour", "kerosene", "iron", "blood",
    "lard", "parsnip", "sawdust", "persimmon", "bacon", "singed", "ammonia", "scented",
    "stale", "pungent", "acrid", "reek", "reeked", "reeking", "perfume", "aroma",
    "scent", "scents", "smell", "smells", "smelled", "smelling", "odor", "odors", "fumes", "fragrance", "fragrant"
}

TASTE_LEX = {
    "bitter", "sour", "sweet", "salty", "salt", "copper", "hardtack", "sourdough",
    "barley", "persimmon", "persimmons", "tea", "cider", "mash", "broth", "leek",
    "honey", "tallow", "grease", "tongue", "swallow", "swallowed", "saliva", "parched",
    "rind", "ale", "sip", "sipped", "chew", "chewed", "chewing", "flavor", "tang",
    "tangy", "tart", "biscuit", "roast", "roasted", "stew", "porridge", "rye", "crust",
    "mutton", "ginger", "clove", "chocolate", "scone", "scones", "pastry", "toast",
    "toasted", "syrup", "sugar", "spiced", "spicy", "venison", "sausage", "sausages",
    "crumpet", "crumpets", "plum", "jam", "molasses", "fruitcake", "brittle", "tasted",
    "taste", "savory", "nibble", "nibbled", "gulp", "gulped", "wine", "beer", "stout", "cocoa"
}

TOUCH_LEX = {
    "cold", "chill", "freezing", "frost", "blister", "blistered", "bruised", "bruise",
    "coarse", "grit", "gritty", "heavy", "heaviness", "weight", "vibration", "rough",
    "numb", "numbness", "slick", "splinter", "splintered", "searing", "leaden", "callous",
    "calloused", "shudder", "shuddered", "shivering", "shiver", "sweat", "sweating",
    "scald", "scalding", "nicked", "scrape", "scraped", "friction", "drag", "dragged",
    "crush", "crushed", "crushing", "pinch", "pinched", "raw", "cramp", "cramped",
    "stiff", "ache", "ached", "aching", "throbbing", "tremble", "trembled", "flint", "knuckle",
    "warmth", "warm", "hot", "burning", "blistering", "breeze", "draft", "dampness", "soaking", "soaked",
    "touch", "touched", "touching", "grip", "gripped", "gripping", "grips", "clutch", "clutched", "clutching",
    "grasp", "grasped", "grasping", "seize", "seized", "seizing", "pressure", "pressed", "pressing", "tight"
}

SENSES = {
    "Sight": SIGHT_LEX,
    "Sound": SOUND_LEX,
    "Smell": SMELL_LEX,
    "Taste": TASTE_LEX,
    "Touch": TOUCH_LEX
}

# ==============================================================================
# DATABASE CACHING ENGINE
# ==============================================================================


from canonforge.core.manifest import find_universe_root

def get_canonical_character_registry(universe_dir: Optional[Path] = None) -> Dict[str, List[str]]:
    """Return map of Canonical Name -> list of search terms dynamically from universe lore."""
    registry: Dict[str, Set[str]] = {}
    u_root = universe_dir or find_universe_root()

    HONORIFICS = {"the", "a", "an", "elder", "brother", "mother", "father", "master", "commander", "inquisitor", "abbot", "lady", "lord", "ser", "saint", "first"}

    # 1. Check relationships.json if present
    for rel_file in [u_root / "wiki" / "database" / "relationships.json", u_root / "data" / "relationships.json"]:
        if rel_file.exists():
            try:
                d = json.loads(rel_file.read_text(encoding="utf-8"))
                for r in d.get("relationships", []):
                    for key in ["source", "target"]:
                        name = r.get(key)
                        if name:
                            first = name.split()[0]
                            registry.setdefault(name, set()).add(name)
                            if len(first) >= 4 and first.lower() not in HONORIFICS:
                                registry[name].add(first)
            except Exception:
                pass

    # 2. Dynamic scan of lore/characters or wiki/terms/characters
    for char_dir in [u_root / "lore" / "characters", u_root / "wiki" / "terms" / "characters"]:
        if char_dir.is_dir():
            for cf in char_dir.glob("*.md"):
                canon_name = cf.stem.replace("-", " ").title()
                # Check frontmatter title if present
                try:
                    txt = cf.read_text(encoding="utf-8", errors="ignore")
                    m_title = re.search(r'^title:\s*["\']?(.*?)["\']?\s*$', txt, re.MULTILINE)
                    if m_title:
                        raw_title = m_title.group(1).replace(",", "").strip()
                        if raw_title:
                            canon_name = raw_title
                except Exception:
                    pass
                first = canon_name.split()[0]
                registry.setdefault(canon_name, set()).add(canon_name)
                if len(first) >= 4 and first.lower() not in HONORIFICS:
                    registry[canon_name].add(first)

    return {k: sorted(list(v), key=lambda x: len(x), reverse=True) for k, v in registry.items()}

def get_item_registry(universe_dir: Optional[Path] = None) -> Dict[str, List[str]]:
    """Dynamically return map of canonical items from universe lore."""
    registry: Dict[str, List[str]] = {}
    u_root = universe_dir or find_universe_root()
    for item_dir in [u_root / "lore" / "items", u_root / "wiki" / "terms" / "items"]:
        if item_dir.is_dir():
            for itm in item_dir.glob("*.md"):
                label = itm.stem.replace("-", " ").title()
                registry[label] = [label]
    return registry

ITEM_REGISTRY = get_item_registry()


