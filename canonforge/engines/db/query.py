"""
SQLite and FTS5 query runner with tabular formatting.
"""
import sys
import re
import sqlite3
from pathlib import Path
from typing import Optional
from canonforge.engines.db.seeder import get_connection, sanitize_fts_query, DB_PATH

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

def execute_user_query(sql: str):
    """Execute raw SQL query and pretty print results in ASCII table."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql)
        rows = cur.fetchall()
        if not rows:
            print("Query returned 0 rows.")
            return

        headers = [d[0] for d in cur.description]
        table_rows = [list(r) for r in rows]
        if HAS_TABULATE:
            print("\n" + tabulate(table_rows, headers=headers, tablefmt="psql"))
        else:
            print("\n | ".join(headers))
            print("-" * 50)
            for r in table_rows:
                print(" | ".join(str(x) for x in r))
        print(f"({len(rows)} rows)\n")
    except Exception as e:
        print(f"SQL Error: {e}", file=sys.stderr)
    finally:
        conn.close()

def search_lore_fts(query: str, limit: int = 10):
    """Query lore_search_fts with SQLite FTS5 query syntax and format results."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        match_expr = sanitize_fts_query(query)

        sql = """
            SELECT domain, name, role_or_type, faction_or_region,
                   snippet(lore_search_fts, 5, '«', '»', '...', 18) AS excerpt,
                   file_path
            FROM lore_search_fts
            WHERE lore_search_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """
        try:
            cur.execute(sql, (match_expr, limit))
            rows = cur.fetchall()
        except sqlite3.OperationalError:
            rows = []

        if not rows:
            fallback_sql = """
                SELECT domain, name, role_or_type, faction_or_region,
                       substr(description_md, 1, 100) AS excerpt,
                       file_path
                FROM lore_search_fts
                WHERE name LIKE ? OR description_md LIKE ? OR role_or_type LIKE ?
                LIMIT ?
            """
            cur.execute(fallback_sql, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
            rows = cur.fetchall()

        if not rows:
            print(f"No lore entries matching '{query}' found.")
            return

        headers = ["Domain", "Name", "Role / Type", "Faction / Region", "Markdown Excerpt", "File Path"]
        table_rows = [list(r) for r in rows]
        if HAS_TABULATE:
            print(f"\n🔍 LORE FULL-TEXT SEARCH RESULTS FOR: '{query}'")
            print(tabulate(table_rows, headers=headers, tablefmt="psql"))
        else:
            print(f"\n🔍 LORE FULL-TEXT SEARCH RESULTS FOR: '{query}'")
            print("\n | ".join(headers))
            print("-" * 50)
            for r in table_rows:
                print(" | ".join(str(x) for x in r))
        print(f"({len(rows)} matching lore dossiers found)\n")
    except Exception as e:
        print(f"Lore Search Error: {e}", file=sys.stderr)
    finally:
        conn.close()

def run_sample_queries():
    """Run standard game engine query demonstrations."""
    print("=" * 75)
    print("CANONFORGE GAME ENGINE DATABASE SAMPLES")
    print("=" * 75)

    samples = [
        (
            "1. Canonical Combat Stats Derivation View (v_character_combat_stats)",
            "SELECT name, birth_race, biological_state, max_hp, max_fp, max_sp, heat_capacity, base_phys_def, base_force_def FROM v_character_combat_stats ORDER BY name LIMIT 5"
        ),
        (
            "2. Primordial World Bosses & Mythic Horrors (Danger Rating >= 4)",
            "SELECT name, origin, element, base_hp, base_atk, primary_habitat, danger_rating FROM monsters WHERE danger_rating >= 4 ORDER BY danger_rating DESC, base_hp DESC"
        ),
        (
            "3. Relational Monster Loot Drops View (v_monster_loot)",
            "SELECT monster_name, danger_rating, item_name, drop_chance FROM v_monster_loot WHERE danger_rating >= 3 LIMIT 10"
        ),
        (
            "4. Equipment Arsenal with Base Attack, Base Defense & Granted Skills",
            "SELECT name, equipment_type, slot, job_class, base_atk, base_def, granted_skill FROM equipment WHERE base_def > 0 OR base_atk > 15 LIMIT 8"
        ),
        (
            "5. Relational Crafting Bill of Materials View (v_recipe_details)",
            "SELECT recipe_name, required_station, output_item, ingredient_name, required_quantity FROM v_recipe_details LIMIT 10"
        ),
        (
            "6. SQLite FTS5 Full-Text Lore Search (Sub-millisecond keyword lookup across all markdown bodies)",
            "SELECT domain, name, role_or_type, snippet(lore_search_fts, 5, '«', '»', '...', 15) AS excerpt FROM lore_search_fts WHERE lore_search_fts MATCH 'blade OR warrior' LIMIT 5"
        )
    ]

    for title, query in samples:
        print(f"\n🔍 {title}:")
        print(f"   SQL: {query}")
        execute_user_query(query)

