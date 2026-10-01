"""
Terminal formatting and tabular metrics summaries.
"""
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

from canonforge.core.manifest import find_universe_root
from canonforge.engines.metrics.calculator import get_chapter_metrics

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

def find_target_file(query: str, universe_dir: Optional[Path] = None) -> Optional[Path]:
    """Find chapter file by exact path, relative path, or filename search."""
    p = Path(query)
    if p.exists() and p.is_file():
        return p
        
    u_root = universe_dir or find_universe_root()
    p_full = u_root / query
    if p_full.exists() and p_full.is_file():
        return p_full
        
    # Search in manuscript directory
    ms_dir = u_root / "manuscript"
    if ms_dir.is_dir():
        matches = list(ms_dir.rglob(f"*{query}*"))
        md_matches = [m for m in matches if m.suffix == ".md" and not m.name.startswith(".")]
        if md_matches:
            # Prefer exact match or shortest filename
            md_matches.sort(key=lambda x: len(x.name))
            return md_matches[0]
        
    return None


