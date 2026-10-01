#!/usr/bin/env python3
"""
CONVERGENCE STUDIO: 5-SENSES RADAR & SENSORY HEATMAP AUDITOR
------------------------------------------------------------------------------
Enforces Section 4.A of the Convergence Style Guide (The "Four-Sense Rule"):
  "Every major scene sequence (every 500–700 words) must activate at least
   four of the five senses (Sight, Sound, Smell, Taste, Touch/Kinetic)."
------------------------------------------------------------------------------
"""

import sys
import re
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple, Set, Optional

CONVERGENCE_DIR = Path(__file__).resolve().parent.parent
MANUSCRIPT_DIR = CONVERGENCE_DIR / "manuscript"
PROFILES_DIR = CONVERGENCE_DIR / "data" / "sensory_profiles"

try:
    from canonforge.engines.sensory_dictionary import get_dictionary
    SENSORY_DICT = get_dictionary()
except ImportError:
    try:
        from sensory_dictionary import get_dictionary
        SENSORY_DICT = get_dictionary()
    except ImportError:
        SENSORY_DICT = None

# ==============================================================================
# SENSORY LEXICON (CANONICAL CONVERGENCE FLAVORS)
# ==============================================================================

SIGHT_LEXICON = {
    # Lighting & Shadow
    "shadow", "shadows", "shadowy", "silhouette", "silhouettes", "flicker", "flickering", "flickered",
    "glint", "glinted", "glinting", "lantern", "lanterns", "torch", "torches", "torchlight", "sodium", "glare",
    "pale", "amber", "bronze", "violet", "scarlet", "obsidian", "crimson", "twilight",
    "gloom", "gleam", "gleamed", "gleaming", "quartz", "refraction", "shimmer", "shimmering", "haze",
    "soot", "sooty", "flame", "flames", "dim", "darkness", "blind", "blinding", "dusk",
    "cinder", "cinders", "spark", "sparks", "sparking", "luminous", "iridescent", "murky", "blaze", "blazing",
    "glance", "glanced", "glancing", "gaze", "gazed", "gazing", "stare", "stared", "staring", "sight"
}

SOUND_LEXICON = {
    # Acoustic Architecture & Vocal Expressions
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

SMELL_LEXICON = {
    # Olfactory Signatures & Aromas
    "tallow", "grease", "chicory", "cabbage", "sulfur", "ozone", "copper", "peat",
    "smoke", "smoked", "smoky", "slate", "resin", "vinegar", "whale", "cedar", "pine",
    "rot", "rotten", "rotting", "burnt", "musk", "musky", "mold", "moldy", "musty",
    "brine", "coal", "charcoal", "damp", "stench", "sour", "kerosene", "iron", "blood",
    "lard", "parsnip", "sawdust", "persimmon", "bacon", "singed", "ammonia", "scented",
    "stale", "pungent", "acrid", "reek", "reeked", "reeking", "perfume", "aroma",
    "scent", "scents", "smell", "smells", "smelled", "smelling", "odor", "odors", "fumes", "fragrance", "fragrant"
}

TASTE_LEXICON = {
    # Gustatory & Oral Texture
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

TOUCH_LEXICON = {
    # Tactile Physics, Temperature & Kinetic Weight
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

DEFAULT_SENSES = {
    "Sight": SIGHT_LEXICON,
    "Sound": SOUND_LEXICON,
    "Smell": SMELL_LEXICON,
    "Taste": TASTE_LEXICON,
    "Touch": TOUCH_LEXICON,
}

SENSE_ICONS = {
    "Sight": "👁️ ",
    "Sound": "👂",
    "Smell": "👃",
    "Taste": "👅",
    "Touch": "✋",
}

# ==============================================================================
# COMPOSABLE MULTI-PROFILE & ATMOSPHERIC ENGINE
# ==============================================================================

WARM_LEXICON = {
    "warm", "warmth", "hot", "burning", "embers", "hearth", "flame", "flames", "roast",
    "roasted", "stew", "porridge", "tea", "cider", "sun", "wool", "woolen", "cedar",
    "candle", "blanket", "baking", "cozy", "comfort", "simmer", "dough", "honey"
}

COLD_LEXICON = {
    "cold", "chill", "freezing", "frost", "sleet", "ice", "numb", "numbness", "shivering",
    "shiver", "shale", "frazil", "winter", "blizzard", "leaden", "slush", "pale", "cool"
}

HARD_LEXICON = {
    "iron", "brass", "steel", "bronze", "stone", "granite", "anvil", "hammer", "rivet",
    "chiseled", "piston", "cog", "flint", "knuckle", "callous", "calloused", "grit", "gritty",
    "chisel", "screech", "clang", "screws", "shale", "slate"
}

SOFT_LEXICON = {
    "silk", "wool", "linen", "fur", "feather", "moss", "dough", "crust", "porridge",
    "persimmon", "velvet", "pine", "peat", "cedar", "blanket", "stream", "cloud", "mist"
}

DEFAULT_FORBIDDEN_WORDS = {
    "plastic", "silicon", "computer", "digital", "battery", "circuit", "antibiotic", "laser", "touchscreen", "microchip"
}

def load_composite_profiles(
    profile_args: Optional[List[str]] = None,
    require_args: Optional[List[str]] = None,
    forbidden_args: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Load and compose multiple sensory profiles with OR, AND, and NOT relations."""
    p_names = []
    if profile_args:
        for p in profile_args:
            p_names.extend([x.strip() for x in p.split(",") if x.strip()])
    
    # If not passed, check universe.yaml
    if not p_names:
        universe_yaml = CONVERGENCE_DIR / "universe.yaml"
        if universe_yaml.is_file():
            try:
                import yaml
                data = yaml.safe_load(universe_yaml.read_text(encoding="utf-8"))
                sp = data.get("sensory_profile") or data.get("sensory", {}).get("profiles")
                if isinstance(sp, list):
                    p_names = sp
                elif isinstance(sp, str):
                    p_names = [sp]
            except Exception:
                pass

    if not p_names:
        p_names = ["core_senses", "high_fantasy", "industrial_foundry"]

    loaded_senses = {k: set(v) for k, v in DEFAULT_SENSES.items()}
    theme_lexicons = {}
    found_profiles = []

    for pid in p_names:
        theme_key = pid.replace(".yaml", "").replace(".yml", "").lower()
        theme_words = set()

        # 1. Query from Master Unified Sensory Dictionary
        if SENSORY_DICT:
            theme_lexemes = SENSORY_DICT.get_lexemes_for_theme(theme_key)
            if theme_lexemes:
                for lex in theme_lexemes:
                    theme_words.update(lex.forms)
                    for s in lex.senses:
                        cap_s = s.capitalize()
                        if cap_s in loaded_senses:
                            loaded_senses[cap_s].update(lex.forms)

        # 2. Check sensory_profiles/ directory for backward compatibility
        p_file = CONVERGENCE_DIR / "data" / "sensory_profiles" / f"{pid}.yaml"
        if not p_file.is_file():
            p_file = CONVERGENCE_DIR / "data" / "sensory_profiles" / f"{pid}.yml"
        if not p_file.is_file() and Path(pid).is_file():
            p_file = Path(pid)

        if p_file.is_file():
            try:
                import yaml
                p_data = yaml.safe_load(p_file.read_text(encoding="utf-8")) or {}
                for s_key in ["sight", "sound", "smell", "taste", "touch"]:
                    words = p_data.get(s_key, [])
                    title_s = s_key.capitalize()
                    if title_s in loaded_senses:
                        loaded_senses[title_s].update(words)
                    theme_words.update(words)
            except Exception:
                pass

        if theme_words:
            theme_lexicons[theme_key] = theme_words
            found_profiles.append(theme_key)

    if not found_profiles:
        found_profiles = ["builtin_default"]
        theme_lexicons["builtin"] = set().union(*DEFAULT_SENSES.values())

    # AND relation (required themes)
    required = set()
    if require_args:
        for r in require_args:
            required.update([x.strip() for x in r.split(",") if x.strip()])

    # NOT relation (forbidden words)
    forbidden = set(DEFAULT_FORBIDDEN_WORDS)
    if forbidden_args:
        for f in forbidden_args:
            forbidden.update([x.strip().lower() for x in f.split(",") if x.strip()])

    return {
        "profile_ids": found_profiles,
        "senses": loaded_senses,
        "theme_lexicons": theme_lexicons,
        "required": required,
        "forbidden": forbidden,
    }

def get_token_variants(t: str) -> List[str]:
    """Generate plausible base stems and morphological variants for an English token."""
    variants = [t]
    # -s / -es (e.g. embers -> ember, furnaces -> furnace)
    if t.endswith("ies") and len(t) > 4:
        variants.append(t[:-3] + "y")
    elif t.endswith("es") and len(t) > 3:
        variants.append(t[:-2])
    elif t.endswith("s") and len(t) > 3 and not t.endswith("ss"):
        variants.append(t[:-1])

    # -ed / -d (e.g. blistered -> blister, scorched -> scorch, tasted -> taste)
    if t.endswith("ed") and len(t) > 4:
        variants.append(t[:-2])
        variants.append(t[:-1])
        if len(t) > 5 and t[-3] == t[-4]:  # gripped -> grip
            variants.append(t[:-3])

    # -ing (e.g. sizzling -> sizzle, humming -> hum, glowing -> glow)
    if t.endswith("ing") and len(t) > 5:
        variants.append(t[:-3])
        variants.append(t[:-3] + "e")
        if len(t) > 6 and t[-4] == t[-5]:  # humming -> hum
            variants.append(t[:-4])

    # -ly / -y (e.g. gritty -> grit, greasy -> grease, smoky -> smoke)
    if t.endswith("ly") and len(t) > 4:
        variants.append(t[:-2])
    if t.endswith("y") and len(t) > 3 and not t.endswith(("ey", "ay", "oy")):
        variants.append(t[:-1])
        variants.append(t[:-1] + "e")

    return variants

def analyze_text(
    text: str,
    composite: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    comp = composite or load_composite_profiles()
    senses_map = comp["senses"]
    theme_lexicons = comp["theme_lexicons"]
    forbidden_words = comp["forbidden"]
    required_themes = comp["required"]

    sentences = re.split(r"[.!?;\n]+", text.lower())
    all_tokens = []

    sense_counts = {name: 0 for name in senses_map}
    sense_samples = {name: set() for name in senses_map}

    # Thematic distribution counts
    theme_counts = {th: 0 for th in theme_lexicons}
    
    # Thermal & Tactile vector counts
    warm_hits = 0
    cold_hits = 0
    hard_hits = 0
    soft_hits = 0
    forbidden_hits = []

    for s in sentences:
        s_tokens = re.findall(r"\b[a-zA-Z]{3,}\b", s)
        if not s_tokens:
            continue
        all_tokens.extend(s_tokens)

        i = 0
        while i < len(s_tokens):
            # 1. Multi-word phrase matching (Greedy Longest Match / Maximal Munch)
            phrase_hit, phrase_len, phrase_text = SENSORY_DICT.match_longest_phrase(s_tokens, i) if SENSORY_DICT else (None, 0, "")
            if phrase_hit:
                matched_senses = set()
                for s_name in phrase_hit.senses:
                    cap_s = s_name.capitalize()
                    if cap_s in senses_map and cap_s not in matched_senses:
                        sense_counts[cap_s] += 1
                        sense_samples[cap_s].add(phrase_text)
                        matched_senses.add(cap_s)

                for th in phrase_hit.thematic_tags:
                    if th in theme_counts:
                        theme_counts[th] += 1

                if phrase_hit.thermal == "warm":
                    warm_hits += 1
                elif phrase_hit.thermal == "cold":
                    cold_hits += 1
                if phrase_hit.tactile == "hard":
                    hard_hits += 1
                elif phrase_hit.tactile == "soft":
                    soft_hits += 1

                i += phrase_len
                continue

            # 2. Single token fallback
            t = s_tokens[i]
            variants = get_token_variants(t)
            matched_senses = set()
            matched_themes = set()
            v_warm = False
            v_cold = False
            v_hard = False
            v_soft = False

            # Master Sensory Lexicon O(1) exact inflected lookup
            if SENSORY_DICT:
                hit = SENSORY_DICT.lookup(t)
                if hit:
                    for s_name in hit.senses:
                        cap_s = s_name.capitalize()
                        if cap_s in senses_map and cap_s not in matched_senses:
                            sense_counts[cap_s] += 1
                            sense_samples[cap_s].add(t)
                            matched_senses.add(cap_s)
                    if hit.thermal == "warm" and not v_warm:
                        warm_hits += 1
                        v_warm = True
                    elif hit.thermal == "cold" and not v_cold:
                        cold_hits += 1
                        v_cold = True
                    if hit.tactile == "hard" and not v_hard:
                        hard_hits += 1
                        v_hard = True
                    elif hit.tactile == "soft" and not v_soft:
                        soft_hits += 1
                        v_soft = True

            for v in variants:
                for sense_name, lexicon in senses_map.items():
                    if sense_name not in matched_senses and v in lexicon:
                        sense_counts[sense_name] += 1
                        sense_samples[sense_name].add(t)
                        matched_senses.add(sense_name)

                for th, th_words in theme_lexicons.items():
                    if th not in matched_themes and v in th_words:
                        theme_counts[th] += 1
                        matched_themes.add(th)

                if not v_warm and v in WARM_LEXICON:
                    warm_hits += 1
                    v_warm = True
                if not v_cold and v in COLD_LEXICON:
                    cold_hits += 1
                    v_cold = True
                if not v_hard and v in HARD_LEXICON:
                    hard_hits += 1
                    v_hard = True
                if not v_soft and v in SOFT_LEXICON:
                    soft_hits += 1
                    v_soft = True

            if t in forbidden_words:
                forbidden_hits.append(t)

            i += 1

    total_tokens = len(all_tokens)
    total_sensory_hits = sum(sense_counts.values())

    # Window analysis (500-word blocks) to test the Three-Sense Rule
    window_size = 500
    words = text.split()
    windows = []
    compliant_windows_pass = 0

    word_chunks = []
    for i in range(0, len(words), window_size):
        chunk = words[i:i + window_size]
        if word_chunks and len(chunk) < 250:
            word_chunks[-1].extend(chunk)
        else:
            word_chunks.append(chunk)

    current_word_idx = 1
    for w_idx, chunk_words in enumerate(word_chunks, start=1):
        chunk_text = " ".join(chunk_words).lower()
        chunk_sentences = re.split(r"[.!?;\n]+", chunk_text)

        active_senses = set()
        chunk_themes = set()
        for c_sent in chunk_sentences:
            c_tokens = re.findall(r"\b[a-zA-Z]{3,}\b", c_sent)
            i = 0
            while i < len(c_tokens):
                phrase_hit, phrase_len, _ = SENSORY_DICT.match_longest_phrase(c_tokens, i) if SENSORY_DICT else (None, 0, "")
                if phrase_hit:
                    for s_name in phrase_hit.senses:
                        cap_s = s_name.capitalize()
                        if cap_s in senses_map:
                            active_senses.add(cap_s)
                    for th in phrase_hit.thematic_tags:
                        if th in theme_lexicons:
                            chunk_themes.add(th)
                    i += phrase_len
                    continue

                t = c_tokens[i]
                if SENSORY_DICT:
                    hit = SENSORY_DICT.lookup(t)
                    if hit:
                        for s_name in hit.senses:
                            cap_s = s_name.capitalize()
                            if cap_s in senses_map:
                                active_senses.add(cap_s)
                variants = get_token_variants(t)
                for v in variants:
                    for s_name, lex in senses_map.items():
                        if v in lex:
                            active_senses.add(s_name)
                    for th_name, th_lex in theme_lexicons.items():
                        if v in th_lex:
                            chunk_themes.add(th_name)
                i += 1

        is_compliant = len(active_senses) >= 3
        if is_compliant:
            compliant_windows_pass += 1

        start_pos = current_word_idx
        end_pos = current_word_idx + len(chunk_words) - 1
        current_word_idx += len(chunk_words)

        missing = set(senses_map.keys()) - active_senses
        windows.append({
            "window_index": w_idx,
            "word_start": start_pos,
            "word_end": end_pos,
            "active_count": len(active_senses),
            "active_senses": sorted(list(active_senses)),
            "active_themes": sorted(list(chunk_themes)),
            "missing_senses": sorted(list(missing)),
            "compliant": is_compliant
        })

    # Scores
    diversity_score = 100.0
    zero_senses = sum(1 for name, cnt in sense_counts.items() if cnt == 0)
    if zero_senses > 1:
        diversity_score -= (zero_senses - 1) * 15.0

    for name, cnt in sense_counts.items():
        ratio = (cnt / max(1, total_sensory_hits)) * 100
        if ratio > 65:
            diversity_score -= (ratio - 65) * 1.5

    compliance_ratio = compliant_windows_pass / max(1, len(word_chunks))
    final_score = (diversity_score * 0.4) + (compliance_ratio * 100 * 0.6)

    # Penalize for forbidden words
    if forbidden_hits:
        final_score = max(0.0, final_score - (len(forbidden_hits) * 5.0))

    final_score = max(0.0, min(100.0, final_score))

    # Thermal & Tactile percentages
    tot_thermal = max(1, warm_hits + cold_hits)
    tot_tactile = max(1, hard_hits + soft_hits)

    return {
        "profiles": comp["profile_ids"],
        "total_words": len(words),
        "total_sensory_hits": total_sensory_hits,
        "sensory_density_pct": round((total_sensory_hits / max(1, total_tokens)) * 100, 2),
        "sense_counts": sense_counts,
        "sense_samples": {k: sorted(list(v))[:8] for k, v in sense_samples.items()},
        "theme_counts": theme_counts,
        "thermal": {
            "warm_hits": warm_hits,
            "cold_hits": cold_hits,
            "warm_pct": round((warm_hits / tot_thermal) * 100, 1),
            "cold_pct": round((cold_hits / tot_thermal) * 100, 1)
        },
        "tactile": {
            "hard_hits": hard_hits,
            "soft_hits": soft_hits,
            "hard_pct": round((hard_hits / tot_tactile) * 100, 1),
            "soft_pct": round((soft_hits / tot_tactile) * 100, 1)
        },
        "forbidden_hits": sorted(list(set(forbidden_hits))),
        "required_missing": [r for r in required_themes if theme_counts.get(r, 0) == 0],
        "windows": windows,
        "four_sense_compliance_pct": round(compliance_ratio * 100, 1),
        "immersion_score": round(final_score, 1),
    }

def harvest_sensory_candidates(text: str, comp: Dict[str, Any]) -> List[Tuple[str, int]]:
    """Extract high-frequency descriptive words not yet registered in any active sensory lexicon."""
    all_known = set()
    for lex in comp["senses"].values():
        all_known.update(lex)

    tokens = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
    stopwords = {
        "that", "with", "have", "this", "from", "they", "will", "would", "there", "their",
        "what", "about", "which", "when", "make", "like", "time", "just", "know", "take",
        "people", "into", "year", "your", "good", "some", "could", "them", "other", "than",
        "then", "look", "only", "come", "over", "think", "also", "back", "after", "used",
        "head", "down", "eyes", "hand", "hands", "face", "said", "told", "asked", "stood",
        "turned", "walked", "stepped", "looked", "stared", "moved", "door", "room", "wall",
        "floor", "table", "house", "where", "here", "went", "came", "took", "gave", "made",
        "knew", "thought", "felt", "seemed", "heard", "saw", "seen", "very", "much", "more",
        "most", "even", "well", "again", "still", "each", "every", "both", "between", "under",
        "above", "through", "before", "while", "never", "always", "often", "once", "away",
        "around", "against", "along"
    }

    from collections import Counter
    counts = Counter()
    for t in tokens:
        if t in stopwords:
            continue
        vars_list = get_token_variants(t)
        if any(v in all_known for v in vars_list):
            continue
        # Check if word has descriptive texture: ends in -ed, -ing, -ic, -ous, -y, -en, -al, etc.
        if re.search(r"(ed|ing|ic|ous|ive|ish|ful|less|ish|ary|ory|est|ant|ent|id|ar|er)$", t) or t.endswith("y"):
            counts[t] += 1

    return counts.most_common(12)

def promote_word_to_profile(profile_id: str, sense: str, word: str) -> bool:
    """Add a newly approved sensory lemma into the target YAML profile file."""
    p_path = PROFILES_DIR / f"{profile_id}.yaml"
    if not p_path.is_file():
        print(f"❌ Error: Profile {profile_id}.yaml not found in {PROFILES_DIR}")
        return False

    try:
        import yaml
        data = yaml.safe_load(p_path.read_text(encoding="utf-8")) or {}
        sense_key = sense.lower()
        if sense_key not in ["sight", "sound", "smell", "taste", "touch"]:
            print(f"❌ Error: Invalid sense category '{sense}'. Choose from sight, sound, smell, taste, touch.")
            return False

        existing_words = data.get(sense_key, [])
        clean_w = word.strip().lower()
        if clean_w in existing_words:
            print(f"ℹ️ Word '{clean_w}' already exists in {profile_id}.yaml under '{sense_key}'.")
            return True

        existing_words.append(clean_w)
        data[sense_key] = sorted(list(set(existing_words)))
        p_path.write_text(yaml.dump(data, sort_keys=False), encoding="utf-8")
        print(f"✅ Promoted '{clean_w}' -> {profile_id}.yaml under [{sense_key}] successfully!")
        return True
    except Exception as e:
        print(f"❌ Error promoting word: {e}")
        return False

def print_sensory_report(filename: str, res: Dict[str, Any], comp: Dict[str, Any], show_windows: bool = False, harvest_words: Optional[List[Tuple[str, int]]] = None):
    score = res["immersion_score"]
    color = "🟢" if score >= 85 else ("🟡" if score >= 70 else "🔴")

    print("\n" + "=" * 80)
    print(f"COMPOSABLE 5-SENSES & ATMOSPHERIC RADAR: {filename}")
    print("=" * 80)
    print(f"• Active Profiles (OR)     : {', '.join(res['profiles'])}")
    print(f"• Total Words              : {res['total_words']:,} words")
    print(f"• Total Sensory Hits       : {res['total_sensory_hits']:,} ({res['sensory_density_pct']}% of text)")
    print(f"• Three-Sense Pass Rate    : {res['four_sense_compliance_pct']}% of scene windows")
    print("-" * 80)
    print(f"🏆 SENSORY IMMERSION SCORE : {color} {score}/100")
    print("-" * 80)

    # 1. 5-Senses Distribution
    print("\nSENSORY SPECTRUM DISTRIBUTION:")
    total_hits = max(1, res["total_sensory_hits"])
    for sense_name in ["Sight", "Sound", "Smell", "Taste", "Touch"]:
        cnt = res["sense_counts"][sense_name]
        pct = (cnt / total_hits) * 100
        bar_len = int(round((pct / 100) * 26))
        bar = "█" * bar_len + "░" * (26 - bar_len)
        icon = SENSE_ICONS[sense_name]
        samples = ", ".join(res["sense_samples"][sense_name][:4])
        print(f"  {icon} {sense_name:<6}: [{bar}] {pct:>5.1f}% ({cnt:>3}) | e.g. {samples}")

    # 2. Thematic Mixin Blend
    print("\nTHEMATIC BLEND RATIO (COMPOSABLE RADAR):")
    total_theme_hits = max(1, sum(res["theme_counts"].values()))
    for th_name, cnt in sorted(res["theme_counts"].items(), key=lambda x: x[1], reverse=True):
        th_pct = (cnt / total_theme_hits) * 100
        th_bar_len = int(round((th_pct / 100) * 26))
        th_bar = "█" * th_bar_len + "░" * (26 - th_bar_len)
        print(f"  🎨 {th_name:<20}: [{th_bar}] {th_pct:>5.1f}% ({cnt:>3} hits)")

    # 3. Atmospheric Vectors: Thermal & Tactile
    th = res["thermal"]
    tac = res["tactile"]
    print("\nATMOSPHERIC VECTORS:")
    print(f"  🌡️  Thermal Balance : 🔥 Warm {th['warm_pct']}% ({th['warm_hits']}) vs ❄️ Cold {th['cold_pct']}% ({th['cold_hits']})")
    print(f"  ⚙️  Tactile Texture : 🔨 Hard/Mechanic {tac['hard_pct']}% ({tac['hard_hits']}) vs 🌿 Soft/Comfort {tac['soft_pct']}% ({tac['soft_hits']})")

    # 4. Forbidden & Required Relations
    if res["forbidden_hits"]:
        print(f"\n❌ FORBIDDEN ANACRONISMS (NOT Relation): {', '.join(res['forbidden_hits'])}")
    if res["required_missing"]:
        print(f"\n⚠️  MISSING REQUIRED THEMES (AND Relation): {', '.join(res['required_missing'])}")

    # 5. Scene Window Diagnostics & Prescriptive Suggestions
    failing_windows = [w for w in res["windows"] if not w["compliant"]]
    if failing_windows or show_windows:
        print("\n🔍 SCENE WINDOW SENSORY DIAGNOSTICS & PRESCRIPTIVE ADVICE:")
        for w in res["windows"]:
            if not w["compliant"] or show_windows:
                status = "✓ PASS" if w["compliant"] else "⚠️ DEFICIT"
                print(f"  [{status}] Window {w['window_index']} (Words {w['word_start']}-{w['word_end']}) | Active Senses ({w['active_count']}/5): {', '.join(w['active_senses']) or 'None'}")
                if not w["compliant"]:
                    missing_names = ", ".join(w["missing_senses"])
                    print(f"    👉 Missing Senses: {missing_names} (Must have at least 3 senses per 500 words)")
                    print(f"    💡 Prescriptive Injections from Active Profiles & Knowledge Graph:")
                    for m in w["missing_senses"]:
                        sample_pool = []
                        if SENSORY_DICT:
                            active_theme = res['profiles'][0] if res.get('profiles') else 'core_senses'
                            theme_lexemes = SENSORY_DICT.get_lexemes_for_theme(active_theme)
                            sense_lexemes = [l.lemma for l in theme_lexemes if m.lower() in l.senses]
                            sample_pool = sense_lexemes[:5]
                        if not sample_pool:
                            sample_pool = list(comp["senses"].get(m, []))[:5]
                        print(f"       • {SENSE_ICONS.get(m, '')} {m}: Infuse sensory cues like: {', '.join(sample_pool)}")

    # 6. Lexicon Harvesting
    if harvest_words:
        print("\n🌾 HARVESTED SENSORY CANDIDATES (Evocative words in text not yet in profiles):")
        for word, freq in harvest_words[:8]:
            print(f"  • '{word}' (frequency: {freq})")
        print("  💡 TIP: Promote any candidate into a profile via: ./ax sensory --promote <profile_id> <sense> <word>")
    print("\n" + "=" * 80 + "\n")


def find_chapter_files(target: str) -> List[Path]:
    p = Path(target)
    if p.is_file():
        return [p]
    m_path = MANUSCRIPT_DIR / target
    if m_path.is_file():
        return [m_path]
    elif m_path.is_dir():
        chapters_dir = m_path / "chapters"
        if chapters_dir.exists():
            return sorted([f for f in chapters_dir.glob("*.md") if "archive" not in f.parts])
        return sorted([f for f in m_path.rglob("*.md") if "archive" not in f.parts and "_build" not in f.parts])

    matches = list(MANUSCRIPT_DIR.rglob(f"*{target}*"))
    files = [
        f for f in matches
        if f.is_file() and f.suffix == ".md" and not f.name.startswith((".", "MASTER-", "README"))
        and "_build" not in f.parts and "compiled" not in f.parts and "darlings" not in f.parts and "exports" not in f.parts and "archive" not in f.parts
    ]
    return sorted(files)

def main():
    parser = argparse.ArgumentParser(description="Convergence Composable 5-Senses Radar & Atmospheric Auditor")
    parser.add_argument("target", nargs="?", default="the-iron-on-the-anvil.md", help="Chapter markdown file or book slug")
    parser.add_argument("--profiles", "-p", nargs="*", help="List or comma-separated profile mix-ins (e.g. high_fantasy,industrial_foundry,cozy_hearth)")
    parser.add_argument("--require", "-r", nargs="*", help="Required theme palettes (AND relation, e.g. high_fantasy,industrial_foundry)")
    parser.add_argument("--forbidden", "-f", nargs="*", help="Forbidden words/anachronisms (NOT relation)")
    parser.add_argument("--all-books", action="store_true", help="Audit all chapters across all books")
    parser.add_argument("--show-windows", "-w", action="store_true", help="Show all 500-word scene windows")
    parser.add_argument("--harvest", action="store_true", help="Harvest and discover unmapped sensory candidate words from text")
    parser.add_argument("--promote", nargs=3, metavar=("PROFILE", "SENSE", "WORD"), help="Promote candidate word to YAML profile (e.g. cozy_hearth smell sourdough)")
    parser.add_argument("--thesaurus", "-t", help="Explore sensory synonyms, antonyms, and lore aliases for a word")
    args = parser.parse_args()

    if args.thesaurus:
        if SENSORY_DICT:
            hit = SENSORY_DICT.lookup(args.thesaurus)
            if not hit:
                print(f"\n❌ Word '{args.thesaurus}' not found in Sensory Knowledge Graph.\n")
                return
            syns = SENSORY_DICT.get_synonyms(args.thesaurus)
            ants = SENSORY_DICT.get_antonyms(args.thesaurus)
            print(f"\n📚 SENSORY THESAURUS GRAPH: '{args.thesaurus}' (Intensity: {hit.intensity}/3)")
            print(f"  • Primary Senses: {', '.join(hit.senses)}")
            if hit.aliases:
                print(f"  • Lore Aliases   : {', '.join(sorted(list(hit.aliases)))}")
            if syns:
                print(f"  • Synonyms       : {', '.join(s.lemma for s in syns)}")
            if ants:
                print(f"  • Antonyms       : {', '.join(a.lemma for a in ants)}\n")
        return

    if args.promote:
        prof, sense, word = args.promote
        promote_word_to_profile(prof, sense, word)
        return

    comp = load_composite_profiles(
        profile_args=args.profiles,
        require_args=args.require,
        forbidden_args=args.forbidden
    )

    files = find_chapter_files(args.target)
    if not files:
        print(f"❌ Error: Could not locate chapter markdown file for: {args.target}")
        sys.exit(1)

    for f in files:
        text = f.read_text(encoding="utf-8")
        res = analyze_text(text, composite=comp)
        harvest_candidates = harvest_sensory_candidates(text, comp) if args.harvest else None
        print_sensory_report(f.name, res, comp, show_windows=args.show_windows, harvest_words=harvest_candidates)

if __name__ == "__main__":
    main()

