"""
SQLite metrics cache for sub-millisecond repeated queries.
"""
import sqlite3
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PACKAGE_ROOT / "data"
CACHE_DB_PATH = DATA_DIR / "metrics_cache.db"

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

