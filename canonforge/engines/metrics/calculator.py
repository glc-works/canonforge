"""
Detailed prose metrics and readability calculation.
"""
import re
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, Any
from collections import Counter

from canonforge.core.manifest import find_universe_root
from canonforge.engines.metrics.cache import init_metrics_cache
from canonforge.engines.metrics.registry import (
    get_canonical_character_registry, get_item_registry,
    SENSES, STOPWORDS, ITEM_REGISTRY
)

UNIVERSE_DIR = find_universe_root()

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
    rel_path = file_path.relative_to(UNIVERSE_DIR) if file_path.is_relative_to(UNIVERSE_DIR) else file_path
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

