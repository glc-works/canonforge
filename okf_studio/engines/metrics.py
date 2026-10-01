#!/usr/bin/env python3
"""
chapter_metrics.py

Convergence Studio: High-Performance Chapter Metrics & Content Counter Engine.
Provides instant (<0.005s cached) single-pass text analysis, counters, and sensory telemetry:
- Character counters (total & non-whitespace)
- Word, sentence, and paragraph counters
- Estimated reading time (at 220 wpm)
- Top 10 frequent content words (stopwords filtered)
- Top 5 canonical characters mentioned
- Top 5 canonical items / relics mentioned
- 5-Senses radar & immersion score
- Persistent SQLite caching indexed by file path & mtime

Usage:
    ./ax stats manuscript/book-1-the-stone-child/act-1-the-ambition/ch01-the-river-pebble.md
    ./ax stats ch01-the-river-pebble.md
    ./ax stats --book the-stone-child
    ./ax stats --book the-sun-sanctum-champion
    ./ax stats --all
    ./ax stats --clear-cache
"""

import sys
import os
import re
import json
import time
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

def init_metrics_cache() -> sqlite3.Connection:
    """Initialize SQLite table for caching chapter metrics."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS chapter_metrics (
        file_path TEXT PRIMARY KEY,
        file_name TEXT,
        book_slug TEXT,
        file_mtime REAL,
        file_sha256 TEXT,
        char_total INTEGER,
        char_no_space INTEGER,
        word_count INTEGER,
        sentence_count INTEGER,
        paragraph_count INTEGER,
        reading_time_min REAL,
        top_words_json TEXT,
        top_chars_json TEXT,
        top_items_json TEXT,
        sensory_summary_json TEXT,
        immersion_score REAL,
        analyzed_at TEXT
    );
    """)
    conn.commit()
    return conn


def clear_metrics_cache():
    """Clear all cached metrics."""
    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS chapter_metrics;")
        conn.commit()
        conn.close()
        print("  ✓ Cleared chapter metrics SQLite cache.")


# ==============================================================================
# HIGH-PERFORMANCE SINGLE-PASS ANALYSIS
# ==============================================================================

# ==============================================================================
# CANONICAL CHARACTER & RELIC REGISTRIES
# ==============================================================================

def get_canonical_character_registry() -> Dict[str, List[str]]:
    """Return map of Canonical Name -> list of search terms (e.g. 'Kazan the Faithful Blade' -> ['Kazan'])."""
    rel_file = WIKI_DIR / "database" / "relationships.json"
    registry: Dict[str, Set[str]] = {}
    if rel_file.exists():
        try:
            d = json.loads(rel_file.read_text(encoding="utf-8"))
            for r in d.get("relationships", []):
                for key in ["source", "target"]:
                    name = r.get(key)
                    if name:
                        first = name.split()[0]
                        registry.setdefault(name, set())
                        registry[name].add(name)
                        if len(first) >= 4 and first not in ("Elder", "Brother", "Mother", "Father", "Master", "Commander", "Inquisitor", "Abbot", "Lady", "Lord"):
                            registry[name].add(first)
        except Exception:
            pass
            
    extras = {
        "Kazan the Faithful Blade": ["Kazan"],
        "Bryn Verdan": ["Bryn"],
        "Cairn the Hearth Guardian": ["Cairn"],
        "Tika Vohr": ["Tika"],
        "Doran the Unmade": ["Doran"],
        "Elder Ozun Vohr": ["Ozun"],
        "Kaelen Verdan": ["Kaelen"],
        "Sariel Verdan": ["Sariel"],
        "Inquest Auditor Sallow": ["Sallow"],
        "Master Barnaby Corvo": ["Barnaby Corvo", "Barnaby", "Corvo"],
        "Vaelin the Pale Weaver": ["Vaelin"],
        "Corin Solen": ["Corin"],
        "Lyra of the Low Sinks": ["Lyra"],
        "Viktor Kray": ["Viktor", "Kray"],
        "Althea Vaell": ["Althea"],
        "Seren Halren": ["Seren"],
        "Lucian Lumis": ["Lucian"],
        "High Justiciar Bartok": ["Bartok"],
        "Barthor the Devoted": ["Barthor"],
        "Brother Kroll": ["Kroll"],
        "Abbot Caelis": ["Caelis"],
        "Mother Seraphi": ["Seraphi"],
        "Inquisitor Vael": ["Vael"],
        "Ren the Dawnbringer / The Black Sun": ["Ren", "Black Sun"],
        "Skitter": ["Skitter"],
        "Scribe Vane": ["Scribe Vane", "Broker Vane", "Vane"],
        "Matron Olympe": ["Olympe"]
    }
    for full, terms in extras.items():
        registry.setdefault(full, set()).update(terms)
        
    return {k: sorted(list(v), key=lambda x: len(x), reverse=True) for k, v in registry.items()}


ITEM_REGISTRY = {
    "River Pebble": ["Blue River Pebble", "River Pebble"],
    "Conduit-Blade": ["Silver Conduit-Blade", "Conduit-Blade"],
    "Heated Katana": ["Heated Katana", "Red Blade", "Charcoal-burner's blade"],
    "Force Eye": ["Storm-Raptor Force Eye", "Force Eye"],
    "Hearth-Core": ["Granite Hearth-Core", "Hearth-Core"],
    "Pneumatic Hammer": ["Pneumatic Hammer"],
    "Brass Calipers": ["Brass Calipers", "Calipers"],
    "Obsidian Record": ["Obsidian Record"],
    "Cartographer's Parchment": ["Cartographer's Parchment", "Parchment Map"],
    "Gilly-Moss": ["Gilly-Moss"],
    "Chalice of Dawn": ["Chalice of Dawn", "The Chalice"],
    "Rust Strider": ["Rust Strider"],
    "Salt-Trunk": ["Salt-Trunk"],
    "Aether-Flint": ["Aether-Flint"],
    "Steam-Carbine": ["Steam-Carbine"],
    "Scabbard": ["Scabbard"],
    "Waterwheel": ["Waterwheel", "Millwheel"],
    "Sledge": ["Transport Sledge", "Oak Sledge", "Sledge"]
}


def compute_metrics(file_path: Path) -> Dict[str, Any]:
    """Perform fast, single-pass text analysis on a markdown chapter file."""
    raw_text = file_path.read_text(encoding="utf-8")
    
    # Strip YAML frontmatter if present
    content = raw_text
    fm_match = re.match(r"^---\n(.*?)\n---\n", raw_text, re.DOTALL)
    if fm_match:
        content = raw_text[fm_match.end():]

    # 1. Basic Character & Paragraph Counters
    char_total = len(content)
    char_no_space = len(re.sub(r"\s+", "", content))
    
    raw_paras = [p.strip() for p in content.split("\n\n") if p.strip()]
    paragraphs = [p for p in raw_paras if not p.startswith("#")]
    paragraph_count = max(1, len(paragraphs))

    # 2. Word & Sentence Counters
    clean_prose = re.sub(r"^#+\s+.*$", "", content, flags=re.MULTILINE)
    clean_prose = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", clean_prose)
    clean_prose = re.sub(r"[*_`>#]", " ", clean_prose)
    
    raw_words = clean_prose.split()
    word_count = len(raw_words)
    reading_time_min = round(word_count / 220.0, 1)

    # Sentences
    sentences = [s.strip() for s in re.split(r"[.!?]+(?:\s+|\n+|$)", clean_prose) if len(s.strip()) > 3]
    sentence_count = max(1, len(sentences))

    # 3. Fast Single-Pass Tokenization
    tokens = re.findall(r"\b[a-zA-Z]{2,}\b", clean_prose.lower())
    
    # 4. Top 10 Frequent Content Words
    content_word_counts = Counter()
    for t in tokens:
        if len(t) >= 3 and t not in STOPWORDS:
            content_word_counts[t] += 1
    top_10_words = content_word_counts.most_common(10)

    # 5. Top 5 Canonical Characters Mentioned (Grouped without alias duplicates)
    known_chars = get_canonical_character_registry()
    char_counts = Counter()
    for full_name, search_terms in known_chars.items():
        term_pattern = r"\b(?:" + "|".join(re.escape(t) for t in search_terms) + r")\b"
        hits = len(re.findall(term_pattern, content, flags=re.IGNORECASE))
        if hits > 0:
            char_counts[full_name] = hits
    top_5_chars = char_counts.most_common(5)

    # 6. Top 5 Items & Relics Mentioned (Grouped)
    item_counts = Counter()
    for item_name, terms in ITEM_REGISTRY.items():
        term_pattern = r"\b(?:" + "|".join(re.escape(t) for t in terms) + r")\b"
        hits = len(re.findall(term_pattern, content, flags=re.IGNORECASE))
        if hits > 0:
            item_counts[item_name] = hits
    top_5_items = item_counts.most_common(5)

    # 7. Sensory 5-Senses Radar
    sense_counts = {name: 0 for name in SENSES}
    sense_samples = {name: set() for name in SENSES}
    for t in tokens:
        for s_name, lex in SENSES.items():
            if t in lex:
                sense_counts[s_name] += 1
                if len(sense_samples[s_name]) < 5:
                    sense_samples[s_name].add(t)

    total_sensory_hits = sum(sense_counts.values())
    sensory_density_pct = round((total_sensory_hits / max(1, len(tokens))) * 100, 2)

    # 500-word window rule calculation
    window_size = 500
    word_chunks = [raw_words[i:i + window_size] for i in range(0, len(raw_words), window_size)]
    compliant_windows = 0
    for chunk in word_chunks:
        c_text = " ".join(chunk).lower()
        c_tokens = set(re.findall(r"\b[a-zA-Z]{3,}\b", c_text))
        active_in_chunk = sum(1 for lex in SENSES.values() if lex & c_tokens)
        if active_in_chunk >= 3:
            compliant_windows += 1
            
    four_sense_pass_pct = round((compliant_windows / max(1, len(word_chunks))) * 100, 1)
    
    # Immersion score calculation
    immersion_score = min(100.0, round((four_sense_pass_pct * 0.6) + (min(40.0, sensory_density_pct * 8.0)), 1))

    # Detect book slug
    rel_path = file_path.relative_to(CONVERGENCE_DIR) if file_path.is_relative_to(CONVERGENCE_DIR) else file_path
    book_slug = "standalone"
    for part in rel_path.parts:
        if part.startswith("book-") or part.startswith("the-"):
            book_slug = part
            break

    return {
        "file_path": str(file_path.resolve()),
        "file_name": file_path.name,
        "book_slug": book_slug,
        "char_total": char_total,
        "char_no_space": char_no_space,
        "word_count": word_count,
        "sentence_count": sentence_count,
        "paragraph_count": paragraph_count,
        "reading_time_min": reading_time_min,
        "top_10_words": top_10_words,
        "top_5_chars": top_5_chars,
        "top_5_items": top_5_items,
        "sensory_summary": {
            "counts": sense_counts,
            "samples": {k: sorted(list(v)) for k, v in sense_samples.items()},
            "density_pct": sensory_density_pct,
            "pass_pct": four_sense_pass_pct,
            "total_hits": total_sensory_hits
        },
        "immersion_score": immersion_score,
        "cached": False,
        "retrieval_ms": 0.0
    }


def get_chapter_metrics(file_path: Path, force_refresh: bool = False) -> Dict[str, Any]:
    """Retrieve metrics for chapter, using SQLite persistent cache when valid."""
    start_t = time.perf_counter()
    if not file_path.exists():
        raise FileNotFoundError(f"Chapter file not found: {file_path}")

    st = file_path.stat()
    current_mtime = st.st_mtime
    
    conn = init_metrics_cache()
    cur = conn.cursor()

    if not force_refresh:
        cur.execute("""
            SELECT char_total, char_no_space, word_count, sentence_count, paragraph_count,
                   reading_time_min, top_words_json, top_chars_json, top_items_json,
                   sensory_summary_json, immersion_score, book_slug
            FROM chapter_metrics
            WHERE file_path = ? AND file_mtime = ?
        """, (str(file_path.resolve()), current_mtime))
        row = cur.fetchone()
        if row:
            elapsed_ms = (time.perf_counter() - start_t) * 1000.0
            conn.close()
            return {
                "file_path": str(file_path.resolve()),
                "file_name": file_path.name,
                "book_slug": row[11],
                "char_total": row[0],
                "char_no_space": row[1],
                "word_count": row[2],
                "sentence_count": row[3],
                "paragraph_count": row[4],
                "reading_time_min": row[5],
                "top_10_words": json.loads(row[6]),
                "top_5_chars": json.loads(row[7]),
                "top_5_items": json.loads(row[8]),
                "sensory_summary": json.loads(row[9]),
                "immersion_score": row[10],
                "cached": True,
                "retrieval_ms": round(elapsed_ms, 2)
            }

    # Cache miss or forced refresh: compute fresh
    metrics = compute_metrics(file_path)
    file_bytes = file_path.read_bytes()
    sha256 = hashlib.sha256(file_bytes).hexdigest()
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        INSERT OR REPLACE INTO chapter_metrics
        (file_path, file_name, book_slug, file_mtime, file_sha256, char_total, char_no_space,
         word_count, sentence_count, paragraph_count, reading_time_min, top_words_json,
         top_chars_json, top_items_json, sensory_summary_json, immersion_score, analyzed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(file_path.resolve()),
        file_path.name,
        metrics["book_slug"],
        current_mtime,
        sha256,
        metrics["char_total"],
        metrics["char_no_space"],
        metrics["word_count"],
        metrics["sentence_count"],
        metrics["paragraph_count"],
        metrics["reading_time_min"],
        json.dumps(metrics["top_10_words"]),
        json.dumps(metrics["top_5_chars"]),
        json.dumps(metrics["top_5_items"]),
        json.dumps(metrics["sensory_summary"]),
        metrics["immersion_score"],
        now_str
    ))
    conn.commit()
    conn.close()

    elapsed_ms = (time.perf_counter() - start_t) * 1000.0
    metrics["retrieval_ms"] = round(elapsed_ms, 2)
    return metrics


# ==============================================================================
# REPORTING & FORMATTING
# ==============================================================================

def print_chapter_dossier(m: Dict[str, Any]):
    """Print an author-friendly, comprehensive metrics dossier for a chapter."""
    status_icon = "⚡ CACHED" if m["cached"] else "🔄 COMPUTED"
    score = m["immersion_score"]
    score_badge = "🟢" if score >= 85 else ("🟡" if score >= 70 else "🔴")
    
    print("\n" + "=" * 80)
    print(f"  📊 CHAPTER METRICS & CONTENT COUNTER: {m['file_name']}")
    print(f"      Book: {m['book_slug']} | Retrieval: {status_icon} ({m['retrieval_ms']} ms)")
    print("=" * 80)

    # 1. Counters
    words_per_sentence = round(m["word_count"] / max(1, m["sentence_count"]), 1)
    words_per_para = round(m["word_count"] / max(1, m["paragraph_count"]), 1)
    print("\n📈 DOCUMENT COUNTERS:")
    print(f"  • Total Characters (huruf)  : {m['char_total']:,} chars ({m['char_no_space']:,} without spaces)")
    print(f"  • Total Words (kata)        : {m['word_count']:,} words")
    print(f"  • Total Sentences (kalimat) : {m['sentence_count']:,} sentences (~{words_per_sentence} words/sentence)")
    print(f"  • Total Paragraphs (paragraf): {m['paragraph_count']:,} paragraphs (~{words_per_para} words/paragraph)")
    print(f"  • Estimated Reading Time    : ~{m['reading_time_min']} minutes (at standard 220 wpm)")

    # 2. Top 10 Words
    print("\n🔤 TOP 10 CONTENT WORDS (STOPWORDS FILTERED):")
    if m["top_10_words"]:
        row_1 = [f"{w} ({c})" for w, c in m["top_10_words"][:5]]
        row_2 = [f"{w} ({c})" for w, c in m["top_10_words"][5:10]]
        print(f"  1–5 : " + ", ".join(row_1))
        if row_2:
            print(f"  6–10: " + ", ".join(row_2))
    else:
        print("  (None detected)")

    # 3. Top 5 Characters
    print("\n👥 TOP 5 CANONICAL CHARACTERS PRESENT:")
    if m["top_5_chars"]:
        for idx, (c, cnt) in enumerate(m["top_5_chars"], 1):
            print(f"  [{idx}] {c:<28} : {cnt:>3} mention(s)")
    else:
        print("  (No registered canonical characters detected)")

    # 4. Top 5 Items
    print("\n⚔️ TOP 5 CANONICAL ITEMS & RELICS:")
    if m["top_5_items"]:
        for idx, (item, cnt) in enumerate(m["top_5_items"], 1):
            print(f"  [{idx}] {item:<28} : {cnt:>3} mention(s)")
    else:
        print("  (No specific canonical relics detected in this scene)")

    # 5. Sensory Immersion Summary
    s = m["sensory_summary"]
    counts = s["counts"]
    print("\n👃 SENSORY RADAR & IMMERSION AUDIT:")
    print(f"  • Immersion Score   : {score_badge} {score}/100")
    print(f"  • Sensory Density   : {s['density_pct']}% of prose ({s['total_hits']} sensory words)")
    print(f"  • 3-Sense Pass Rate : {s['pass_pct']}% of 500-word scene windows")
    print("  • 5-Senses Spectrum : "
          f"👁️ Sight: {counts.get('Sight', 0)} | "
          f"👂 Sound: {counts.get('Sound', 0)} | "
          f"👃 Smell: {counts.get('Smell', 0)} | "
          f"👅 Taste: {counts.get('Taste', 0)} | "
          f"✋ Touch: {counts.get('Touch', 0)}")
    print("=" * 80 + "\n")


def print_book_summary(book_slug: str, files: List[Path]):
    """Audit all chapters in a book and print high-speed aggregate dashboard."""
    print("\n" + "=" * 85)
    print(f"  📚 BOOK COMPREHENSIVE METRICS SUMMARY: {book_slug}")
    print("=" * 85)
    
    total_words = 0
    total_chars = 0
    total_sentences = 0
    total_paragraphs = 0
    total_reading_time = 0.0
    book_word_counter = Counter()
    book_char_counter = Counter()
    book_item_counter = Counter()
    all_scores = []
    
    start_total_t = time.perf_counter()
    records = []
    
    for f in sorted(files):
        m = get_chapter_metrics(f)
        records.append(m)
        total_words += m["word_count"]
        total_chars += m["char_total"]
        total_sentences += m["sentence_count"]
        total_paragraphs += m["paragraph_count"]
        total_reading_time += m["reading_time_min"]
        all_scores.append(m["immersion_score"])
        
        for w, cnt in m["top_10_words"]:
            book_word_counter[w] += cnt
        for c, cnt in m["top_5_chars"]:
            book_char_counter[c] += cnt
        for item, cnt in m["top_5_items"]:
            book_item_counter[item] += cnt

    total_time_ms = (time.perf_counter() - start_total_t) * 1000.0
    avg_score = round(sum(all_scores) / max(1, len(all_scores)), 1)
    score_badge = "🟢" if avg_score >= 85 else ("🟡" if avg_score >= 70 else "🔴")

    print(f"• Total Chapters Analyzed : {len(files)} chapters")
    print(f"• Total Manuscript Words  : {total_words:,} words")
    print(f"• Total Characters        : {total_chars:,} characters")
    print(f"• Total Sentences         : {total_sentences:,} sentences")
    print(f"• Total Reading Time      : ~{total_reading_time / 60.0:.1f} hours ({total_reading_time:.0f} mins)")
    print(f"• Average Immersion Score : {score_badge} {avg_score}/100")
    print(f"• Telemetry Execution Time: ⚡ {total_time_ms:.1f} ms for the entire book!")
    print("-" * 85)

    print("\n🏆 MOST FREQUENT CONTENT WORDS IN BOOK:")
    top_book_words = book_word_counter.most_common(10)
    print("  " + ", ".join([f"{w} ({c})" for w, c in top_book_words]))

    print("\n👥 MOST ACTIVE CHARACTERS IN BOOK:")
    for idx, (c, cnt) in enumerate(book_char_counter.most_common(5), 1):
        print(f"  [{idx}] {c:<28} : {cnt:>4} mentions")

    print("\n⚔️ MOST FREQUENT RELICS & EQUIPMENT:")
    for idx, (item, cnt) in enumerate(book_item_counter.most_common(5), 1):
        print(f"  [{idx}] {item:<28} : {cnt:>4} mentions")

    # Table breakdown
    print("\n📋 CHAPTER-BY-CHAPTER BREAKDOWN TABLE:")
    print(f"{'Chapter':<38} | {'Words':>7} | {'Sentences':>9} | {'Read (min)':>10} | {'Immersion':>9}")
    print("-" * 85)
    for r in records:
        sc = r['immersion_score']
        badge = "🟢" if sc >= 85 else ("🟡" if sc >= 70 else "🔴")
        print(f"{r['file_name'][:38]:<38} | {r['word_count']:>7,} | {r['sentence_count']:>9,} | {r['reading_time_min']:>10.1f} | {badge} {sc:>5.1f}")
    print("=" * 85 + "\n")


# ==============================================================================
# CLI RUNNER
# ==============================================================================

def find_target_file(query: str) -> Optional[Path]:
    """Find chapter file by exact path, relative path, or filename search."""
    p = Path(query)
    if p.exists() and p.is_file():
        return p
        
    p_full = CONVERGENCE_DIR / query
    if p_full.exists() and p_full.is_file():
        return p_full
        
    # Search in manuscript directory
    matches = list(MANUSCRIPT_DIR.rglob(f"*{query}*"))
    md_matches = [m for m in matches if m.suffix == ".md" and not m.name.startswith(".")]
    if md_matches:
        # Prefer exact match or shortest filename
        md_matches.sort(key=lambda x: len(x.name))
        return md_matches[0]
        
    return None


def main():
    parser = argparse.ArgumentParser(description="Convergence Chapter Metrics & Content Counter Engine")
    parser.add_argument("target", nargs="?", help="Chapter path, filename, or book slug")
    parser.add_argument("--book", "-b", help="Audit all chapters in specified book slug")
    parser.add_argument("--all", "-a", action="store_true", help="Audit all chapters across all 4 books")
    parser.add_argument("--clear-cache", action="store_true", help="Clear SQLite cache table")
    parser.add_argument("--refresh", "-r", action="store_true", help="Force refresh metrics without cache")
    parser.add_argument("--json", action="store_true", help="Output raw JSON metrics")
    
    args = parser.parse_args()
    
    if args.clear_cache:
        clear_metrics_cache()
        return

    if args.all:
        md_files = [
            f for f in MANUSCRIPT_DIR.rglob("*.md")
            if not f.name.startswith((".", "MASTER-", "README")) and "_build" not in f.parts and "compiled" not in f.parts and "exports" not in f.parts and "darlings" not in f.parts
        ]
        print_book_summary("All Convergence Books (Full Saga)", md_files)
        return

    if args.book:
        target_dir = MANUSCRIPT_DIR / args.book
        if not target_dir.exists():
            candidates = list(MANUSCRIPT_DIR.glob(f"*/{args.book}")) + [
                d for d in MANUSCRIPT_DIR.glob("*/*") if d.is_dir() and args.book in d.name
            ]
            if candidates:
                target_dir = candidates[0]
            else:
                for toc in MANUSCRIPT_DIR.glob("*/*/toc.yaml"):
                    if args.book.lower() in toc.read_text(encoding="utf-8").lower():
                        target_dir = toc.parent
                        break
                else:
                    print(f"❌ Book folder not found: {args.book}")
                    return
        files = [
            f for f in target_dir.rglob("*.md")
            if not f.name.startswith((".", "MASTER-", "README")) and "_build" not in f.parts and "compiled" not in f.parts and "exports" not in f.parts and "darlings" not in f.parts
        ]
        print_book_summary(target_dir.name, files)
        return

    if not args.target:
        print("\n" + "=" * 70)
        print("  CONVERGENCE CHAPTER METRICS & CONTENT COUNTER ENGINE")
        print("=" * 70)
        print("Usage:")
        print("  ./ax stats <chapter_path_or_name>   : Audit single chapter file")
        print("  ./ax stats --book the-stone-child   : Audit entire Book 1")
        print("  ./ax stats --book the-sun-sanctum-champion : Audit entire Book 4")
        print("  ./ax stats --all                    : Audit all manuscript books")
        print("  ./ax stats --clear-cache            : Invalidate SQLite cache")
        print("=" * 70 + "\n")
        return

    # Check if target is a book directory
    book_candidate = MANUSCRIPT_DIR / args.target
    if book_candidate.exists() and book_candidate.is_dir():
        files = [f for f in book_candidate.rglob("*.md") if not f.name.startswith(".") and "compiled" not in f.parts]
        print_book_summary(book_candidate.name, files)
        return

    target_file = find_target_file(args.target)
    if not target_file:
        print(f"❌ Chapter file not found matching '{args.target}'")
        return

    metrics = get_chapter_metrics(target_file, force_refresh=args.refresh)
    if args.json:
        print(json.dumps(metrics, indent=2))
    else:
        print_chapter_dossier(metrics)


if __name__ == "__main__":
    main()
