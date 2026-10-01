"""
radar.py

5-Senses Radar & Atmospheric Immersion Scoring Engine.
Enforces the Four-Sense Rule across 500-word sliding scene windows.
"""

import re
from pathlib import Path
from typing import Dict, Any, List, Set, Optional, Tuple

PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PACKAGE_ROOT / "data"

from canonforge.engines.sensory.dictionary import get_dictionary

SIGHT_LEXICON = {
    "shadow", "shadows", "shadowy", "silhouette", "silhouettes", "flicker", "flickering", "flickered",
    "glint", "glinted", "glinting", "lantern", "lanterns", "torch", "torches", "torchlight", "sodium", "glare",
    "pale", "amber", "bronze", "violet", "scarlet", "obsidian", "crimson", "twilight",
    "gloom", "gleam", "gleamed", "gleaming", "quartz", "refraction", "shimmer", "shimmering", "haze",
    "soot", "sooty", "flame", "flames", "dim", "darkness", "blind", "blinding", "dusk",
    "cinder", "cinders", "spark", "sparks", "sparking", "luminous", "iridescent", "murky", "blaze", "blazing",
    "glance", "glanced", "glancing", "gaze", "gazed", "gazing", "stare", "stared", "staring", "sight"
}

SOUND_LEXICON = {
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
    "tallow", "grease", "chicory", "cabbage", "sulfur", "ozone", "copper", "peat",
    "smoke", "smoked", "smoky", "slate", "resin", "vinegar", "whale", "cedar", "pine",
    "rot", "rotten", "rotting", "burnt", "musk", "musky", "mold", "moldy", "musty",
    "brine", "coal", "charcoal", "damp", "stench", "sour", "kerosene", "iron", "blood",
    "lard", "parsnip", "sawdust", "persimmon", "bacon", "singed", "ammonia", "scented",
    "stale", "pungent", "acrid", "reek", "reeked", "reeking", "perfume", "aroma",
    "scent", "scents", "smell", "smells", "smelled", "smelling", "odor", "odors", "fumes", "fragrance", "fragrant"
}

TASTE_LEXICON = {
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

WARM_LEXICON = {"warm", "warmth", "hot", "heat", "scorch", "scald", "sear", "ember", "hearth", "flame", "blaze", "roast", "cider", "simmer"}
COLD_LEXICON = {"cold", "chill", "freeze", "froze", "frozen", "sleet", "ice", "frazil", "slush", "numb", "shiver", "frost", "rime", "glacier"}
HARD_LEXICON = {"hard", "iron", "stone", "granite", "slate", "bronze", "brass", "steel", "anvil", "flint", "bedrock", "rigid", "stiff"}
SOFT_LEXICON = {"soft", "velvet", "silk", "moss", "wool", "feather", "cushion", "dough", "pulp", "fleece", "yielding"}

DEFAULT_FORBIDDEN_WORDS = {"suddenly", "very", "seemed", "felt", "almost", "somehow"}

def get_token_variants(t: str) -> List[str]:
    """Generate plausible base stems and morphological variants for an English token."""
    variants = [t]
    if t.endswith("ies") and len(t) > 4:
        variants.append(t[:-3] + "y")
    elif t.endswith("es") and len(t) > 3:
        variants.append(t[:-2])
    elif t.endswith("s") and len(t) > 3 and not t.endswith("ss"):
        variants.append(t[:-1])

    if t.endswith("ed") and len(t) > 4:
        variants.append(t[:-2])
        variants.append(t[:-1])
        if len(t) > 5 and t[-3] == t[-4]:
            variants.append(t[:-3])

    if t.endswith("ing") and len(t) > 5:
        variants.append(t[:-3])
        variants.append(t[:-3] + "e")
        if len(t) > 6 and t[-4] == t[-5]:
            variants.append(t[:-4])

    if t.endswith("ly") and len(t) > 4:
        variants.append(t[:-2])
    if t.endswith("y") and len(t) > 3 and not t.endswith(("ey", "ay", "oy")):
        variants.append(t[:-1])
        variants.append(t[:-1] + "e")

    return variants

def load_composite_profiles(
    profile_args: Optional[List[str]] = None,
    require_args: Optional[List[str]] = None,
    forbidden_args: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Load and compose multiple sensory profiles."""
    p_names = []
    if profile_args:
        for p in profile_args:
            p_names.extend([x.strip() for x in p.split(",") if x.strip()])
    
    if not p_names:
        p_names = ["core", "high_fantasy", "industrial_foundry"]

    loaded_senses = {k: set(v) for k, v in DEFAULT_SENSES.items()}
    theme_lexicons: Dict[str, Set[str]] = {}
    found_profiles = []

    sensory_dict = get_dictionary()
    for pid in p_names:
        theme_key = pid.replace(".yaml", "").replace(".yml", "").lower()
        theme_words = set()

        if sensory_dict:
            theme_lexemes = sensory_dict.get_lexemes_for_theme(theme_key)
            if theme_lexemes:
                for lex in theme_lexemes:
                    theme_words.update(lex.forms)
                    for s in lex.senses:
                        cap_s = s.capitalize()
                        if cap_s in loaded_senses:
                            loaded_senses[cap_s].update(lex.forms)

        if theme_words:
            theme_lexicons[theme_key] = theme_words
            found_profiles.append(theme_key)

    if not found_profiles:
        found_profiles = ["builtin_default"]
        theme_lexicons["builtin"] = set().union(*DEFAULT_SENSES.values())

    required = set()
    if require_args:
        for r in require_args:
            required.update([x.strip() for x in r.split(",") if x.strip()])

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

def analyze_text(
    text: str,
    composite: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Analyze text against 5-senses radar and 500-word sliding window immersion."""
    comp = composite or load_composite_profiles()
    senses_map = comp["senses"]
    theme_lexicons = comp["theme_lexicons"]
    forbidden_words = comp["forbidden"]
    required_themes = comp["required"]

    sensory_dict = get_dictionary()
    sentences = re.split(r"[.!?;\n]+", text.lower())
    all_tokens = []

    sense_counts = {name: 0 for name in senses_map}
    sense_samples = {name: set() for name in senses_map}
    theme_counts = {th: 0 for th in theme_lexicons}
    
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
            phrase_hit, phrase_len, phrase_text = sensory_dict.match_longest_phrase(s_tokens, i) if sensory_dict else (None, 0, "")
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

            t = s_tokens[i]
            variants = get_token_variants(t)
            matched_senses = set()
            matched_themes = set()
            v_warm = False
            v_cold = False
            v_hard = False
            v_soft = False

            if sensory_dict:
                hit = sensory_dict.lookup(t)
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

    total_words = len(text.split())
    total_sensory_hits = sum(sense_counts.values())

    # Window analysis (500-word blocks)
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
                phrase_hit, phrase_len, _ = sensory_dict.match_longest_phrase(c_tokens, i) if sensory_dict else (None, 0, "")
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
                if sensory_dict:
                    hit = sensory_dict.lookup(t)
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

    diversity_score = 100.0
    zero_senses = sum(1 for name, cnt in sense_counts.items() if cnt == 0)
    if zero_senses > 1:
        diversity_score -= (zero_senses - 1) * 20.0

    compliance_pct = (compliant_windows_pass / max(1, len(windows))) * 100.0
    target_density = 0.04
    actual_density = total_sensory_hits / max(1, total_words)
    density_score = min(100.0, (actual_density / target_density) * 100.0)

    immersion_score = round((0.40 * compliance_pct) + (0.35 * diversity_score) + (0.25 * density_score), 1)

    return {
        "total_words": total_words,
        "total_sensory_hits": total_sensory_hits,
        "sensory_density_pct": round(actual_density * 100, 2),
        "immersion_score": immersion_score,
        "four_sense_compliance_pct": round(compliance_pct, 1),
        "compliant_windows": f"{compliant_windows_pass}/{len(windows)}",
        "sense_counts": sense_counts,
        "sense_samples": {k: sorted(list(v)) for k, v in sense_samples.items()},
        "theme_counts": theme_counts,
        "thermal_vector": {"warm": warm_hits, "cold": cold_hits},
        "tactile_vector": {"hard": hard_hits, "soft": soft_hits},
        "forbidden_hits": forbidden_hits,
        "windows": windows,
        "profiles": comp["profile_ids"],
    }
