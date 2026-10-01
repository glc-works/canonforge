#!/usr/bin/env python3
"""
init_local_db.py

Local Game Database Engine & Relational Query Runner for Convergence.
Builds and maintains an active SQLite database (data/game_world.db) compiled directly
from the SSOT canonical datasets, providing SQL endpoints for game engines and tools.

Usage:
    uv run scripts/init_local_db.py --seed
    uv run scripts/init_local_db.py --query-sample
    uv run scripts/init_local_db.py --query "SELECT name, base_hp, danger_rating FROM monsters WHERE danger_rating >= 4"
"""

import sys
import os
import re
import json
import sqlite3
import argparse
from pathlib import Path
from typing import Dict, Any, List
try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

SCRIPT_DIR = Path(__file__).resolve().parent
CONVERGENCE_DIR = SCRIPT_DIR.parent
DATA_DIR = CONVERGENCE_DIR / "data"
WIKI_DIR = CONVERGENCE_DIR / "wiki"
DB_PATH = DATA_DIR / "game_world.db"

def clean_wikilinks(text: str) -> str:
    """Clean Obsidian wikilinks and markdown link syntax into readable plain text."""
    if not text:
        return ""
    # [[target|label]] -> label, [[target]] -> target
    t = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", text)
    # [label](link) -> label
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    return t

def sanitize_fts_query(query: str) -> str:
    """Sanitize user query for SQLite FTS5 matching without throwing syntax errors."""
    q = query.strip()
    if not q:
        return ""
    has_bool_ops = any(f" {op} " in f" {q} " for op in ["AND", "OR", "NOT", "NEAR"])
    if not has_bool_ops and not q.startswith('"') and not q.endswith('"'):
        clean = q.replace('"', '""')
        return f'"{clean}"'
    tokens = q.split()
    sanitized_tokens = []
    for tok in tokens:
        if tok.upper() in ["AND", "OR", "NOT", "NEAR"] or tok.startswith('"'):
            sanitized_tokens.append(tok)
        elif "-" in tok:
            clean = tok.replace('"', '""')
            sanitized_tokens.append(f'"{clean}"')
        else:
            sanitized_tokens.append(tok)
    return " ".join(sanitized_tokens)

SCHEMA_DDL = """
DROP VIEW IF EXISTS v_character_combat_stats;
DROP VIEW IF EXISTS v_recipe_details;
DROP VIEW IF EXISTS v_monster_loot;
DROP VIEW IF EXISTS v_place_connections;
DROP TABLE IF EXISTS place_routes;
DROP TABLE IF EXISTS monster_loot_drops;
DROP TABLE IF EXISTS recipe_ingredients;
DROP TABLE IF EXISTS characters;
DROP TABLE IF EXISTS monsters;
DROP TABLE IF EXISTS skills;
DROP TABLE IF EXISTS equipment;
DROP TABLE IF EXISTS items;
DROP TABLE IF EXISTS recipes;
DROP TABLE IF EXISTS quests;
DROP TABLE IF EXISTS factions;
DROP TABLE IF EXISTS places;
DROP TABLE IF EXISTS lore_search_fts;

CREATE TABLE characters (
    char_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    house TEXT,
    faction TEXT,
    role TEXT,
    char_type TEXT DEFAULT 'npc',
    status TEXT,
    birthday TEXT,
    birth_race TEXT DEFAULT 'Aurei',
    biological_state TEXT DEFAULT 'Pure Flesh',
    current_phase TEXT DEFAULT 'Phase 1',
    level INTEGER DEFAULT 1,
    strength INTEGER DEFAULT 10,
    dexterity INTEGER DEFAULT 10,
    vitality INTEGER DEFAULT 10,
    willpower INTEGER DEFAULT 10,
    force_stat INTEGER DEFAULT 0,
    system_affinity INTEGER DEFAULT 0,
    description_md TEXT,
    wiki_path TEXT
);

CREATE TABLE monsters (
    monster_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    classification TEXT,
    origin TEXT,
    rarity TEXT,
    element TEXT,
    aspect TEXT,
    base_hp INTEGER DEFAULT 50,
    base_atk INTEGER DEFAULT 10,
    primary_habitat TEXT,
    danger_rating INTEGER DEFAULT 1,
    weaknesses TEXT DEFAULT '[]',
    immunities TEXT DEFAULT '[]',
    description_md TEXT,
    wiki_path TEXT
);

CREATE TABLE monster_loot_drops (
    monster_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    drop_chance REAL DEFAULT 1.0,
    min_qty INTEGER DEFAULT 1,
    max_qty INTEGER DEFAULT 1,
    PRIMARY KEY (monster_id, item_id),
    FOREIGN KEY (monster_id) REFERENCES monsters(monster_id),
    FOREIGN KEY (item_id) REFERENCES items(item_id)
);

CREATE TABLE skills (
    skill_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    job_path TEXT,
    skill_tier TEXT,
    skill_type TEXT,
    resource_pool TEXT,
    resource_cost INTEGER DEFAULT 0,
    target_pattern TEXT,
    primary_effect TEXT DEFAULT 'damage',
    effect_magnitude REAL DEFAULT 1.0,
    resonance_capable BOOLEAN DEFAULT 0,
    polarity_affinity TEXT,
    legal_races TEXT DEFAULT 'All',
    description_md TEXT,
    wiki_path TEXT
);

CREATE TABLE equipment (
    equip_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    equipment_type TEXT,
    slot TEXT,
    rarity TEXT,
    job_class TEXT,
    terrestrial_element TEXT,
    master_polarity TEXT,
    item_power INTEGER DEFAULT 100,
    base_atk INTEGER DEFAULT 0,
    base_def INTEGER DEFAULT 0,
    granted_skill TEXT,
    description_md TEXT,
    wiki_path TEXT
);

CREATE TABLE items (
    item_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    item_kind TEXT,
    rarity TEXT,
    terrestrial_element TEXT,
    master_polarity TEXT,
    unit_value INTEGER DEFAULT 0,
    description_md TEXT,
    wiki_path TEXT
);

CREATE TABLE recipes (
    recipe_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    required_station TEXT,
    crafting_time_seconds INTEGER DEFAULT 0,
    output_item TEXT NOT NULL,
    output_quantity INTEGER DEFAULT 1,
    ingredients TEXT,
    description_md TEXT,
    wiki_path TEXT
);

CREATE TABLE recipe_ingredients (
    recipe_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (recipe_id, item_id),
    FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id),
    FOREIGN KEY (item_id) REFERENCES items(item_id)
);

CREATE TABLE quests (
    quest_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    quest_tier TEXT,
    recommended_item_power INTEGER DEFAULT 100,
    giver TEXT,
    location TEXT,
    dialogue_script TEXT,
    description_md TEXT,
    wiki_path TEXT
);

CREATE TABLE factions (
    faction_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    ideology TEXT,
    seat_of_power TEXT,
    leadership TEXT,
    currency TEXT,
    master_polarity TEXT,
    signature_unit TEXT,
    description_md TEXT,
    wiki_path TEXT
);

CREATE TABLE places (
    place_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    location_kind TEXT,
    danger_level INTEGER DEFAULT 1,
    governing_faction TEXT,
    master_polarity TEXT,
    terrestrial_element TEXT,
    description_md TEXT,
    wiki_path TEXT
);

CREATE TABLE place_routes (
    route_id TEXT PRIMARY KEY,
    from_place_id TEXT NOT NULL,
    to_place_id TEXT NOT NULL,
    distance_miles REAL NOT NULL,
    terrain_type TEXT NOT NULL,
    elevation_change_ft INTEGER DEFAULT 0,
    hazard_rating INTEGER DEFAULT 1,
    standard_foot_hours REAL NOT NULL,
    mount_hours REAL NOT NULL,
    glider_crawler_hours REAL NOT NULL,
    notes TEXT,
    FOREIGN KEY (from_place_id) REFERENCES places(place_id),
    FOREIGN KEY (to_place_id) REFERENCES places(place_id)
);

-- ==============================================================================
-- SQLITE FTS5 FULL-TEXT SEARCH VIRTUAL TABLE
-- ==============================================================================
CREATE VIRTUAL TABLE IF NOT EXISTS lore_search_fts USING fts5(
    entity_id UNINDEXED,
    domain UNINDEXED,
    name,
    role_or_type,
    faction_or_region,
    description_md,
    file_path UNINDEXED
);

-- ==============================================================================
-- CANONICAL RPG VIEWS (COMBAT STAT DERIVATIONS & RELATIONS)
-- ==============================================================================
CREATE VIEW v_character_combat_stats AS
SELECT
    char_id,
    name,
    faction,
    house,
    role,
    char_type,
    birth_race,
    biological_state,
    current_phase,
    level,
    strength,
    dexterity,
    vitality,
    willpower,
    force_stat,
    system_affinity,
    (80 + (vitality * 6) + (level * 5)) AS max_hp,
    (CASE WHEN birth_race LIKE '%Korvath%' THEN 0 ELSE (force_stat * 4 + willpower * 3 + level * 2) END) AS max_fp,
    (40 + (vitality * 3) + (level * 2)) AS max_sp,
    (CASE WHEN birth_race LIKE '%Korvath%' OR biological_state LIKE '%Cyborg%' THEN (50 + system_affinity * 4) ELSE 0 END) AS heat_capacity,
    (vitality * 2) AS base_phys_def,
    (willpower * 2) AS base_force_def,
    (strength * 2) AS base_phys_atk,
    (CASE WHEN birth_race LIKE '%Korvath%' THEN 0 ELSE (force_stat * 2) END) AS base_force_atk
FROM characters;

CREATE VIEW v_recipe_details AS
SELECT
    r.recipe_id,
    r.name AS recipe_name,
    r.category,
    r.required_station,
    r.crafting_time_seconds,
    r.output_item,
    r.output_quantity,
    ri.item_id AS ingredient_item_id,
    COALESCE(i.name, eq.name, ri.item_id) AS ingredient_name,
    ri.quantity AS required_quantity
FROM recipes r
JOIN recipe_ingredients ri ON r.recipe_id = ri.recipe_id
LEFT JOIN items i ON ri.item_id = i.item_id
LEFT JOIN equipment eq ON ri.item_id = eq.equip_id;

CREATE VIEW v_monster_loot AS
SELECT
    m.monster_id,
    m.name AS monster_name,
    m.danger_rating,
    m.primary_habitat,
    d.item_id,
    COALESCE(i.name, d.item_id) AS item_name,
    d.drop_chance,
    d.min_qty,
    d.max_qty
FROM monsters m
JOIN monster_loot_drops d ON m.monster_id = d.monster_id
LEFT JOIN items i ON d.item_id = i.item_id;

CREATE VIEW v_place_connections AS
SELECT
    r.route_id,
    p1.name AS from_place_name,
    p2.name AS to_place_name,
    r.distance_miles,
    ROUND(r.distance_miles / 3.0, 1) AS distance_leagues,
    r.terrain_type,
    r.hazard_rating,
    r.standard_foot_hours,
    r.mount_hours,
    r.glider_crawler_hours,
    r.notes
FROM place_routes r
JOIN places p1 ON r.from_place_id = p1.place_id
JOIN places p2 ON r.to_place_id = p2.place_id;
"""

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def seed_database():
    """Create tables and insert all canonical records from data/*.json."""
    print("=" * 65)
    print("CONVERGENCE LOCAL GAME DB SEEDER (SQLite / PostgreSQL Mirror)")
    print("=" * 65)

    conn = get_connection()
    cur = conn.cursor()
    cur.executescript(SCHEMA_DDL)

    def index_fts(entity_id, domain, name, role_or_type, faction_or_region, desc, fpath):
        clean_desc = clean_wikilinks(desc or "")
        cur.execute("""
            INSERT INTO lore_search_fts (entity_id, domain, name, role_or_type, faction_or_region, description_md, file_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(entity_id or ""),
            str(domain or ""),
            str(name or ""),
            str(role_or_type or ""),
            str(faction_or_region or ""),
            clean_desc,
            str(fpath or "")
        ))

    # 1. Seed Characters
    chars_file = DATA_DIR / "characters.json"
    if chars_file.exists():
        data = json.loads(chars_file.read_text(encoding="utf-8")).get("characters", [])
        for c in data:
            cur.execute("""
                INSERT INTO characters (char_id, name, house, faction, role, char_type, status, birthday, birth_race, biological_state, current_phase, level, strength, dexterity, vitality, willpower, force_stat, system_affinity, description_md, wiki_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                c.get("char_id"), c.get("char_name"), c.get("house"), c.get("faction"),
                c.get("role"), c.get("char_type", "npc"), c.get("status"), c.get("birthday"),
                c.get("birth_race", "Aurei"), c.get("biological_state", "Pure Flesh"), c.get("current_phase", "Phase 1"),
                c.get("level", 1), c.get("strength", 10), c.get("dexterity", 10), c.get("vitality", 10),
                c.get("willpower", 10), c.get("force", 0), c.get("system_affinity", 0),
                c.get("description_md", ""), c.get("wiki_path", "")
            ))
            index_fts(c.get("char_id"), "characters", c.get("char_name"), c.get("role"), c.get("faction") or c.get("house"), c.get("description_md"), c.get("wiki_path"))
        print(f"  ✓ Seeded {len(data):>3} Characters into table 'characters' & FTS")

    # 2. Seed Monsters & Loot Drops
    mon_file = DATA_DIR / "monsters.json"
    if mon_file.exists():
        data = json.loads(mon_file.read_text(encoding="utf-8")).get("monsters", [])
        total_drops = 0
        for m in data:
            cur.execute("""
                INSERT INTO monsters (monster_id, name, classification, origin, rarity, element, aspect, base_hp, base_atk, primary_habitat, danger_rating, weaknesses, immunities, description_md, wiki_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                m.get("id"), m.get("name"), m.get("classification"), m.get("origin"),
                m.get("rarity"), m.get("element"), m.get("aspect"),
                m.get("base_hp", 50), m.get("base_atk", 10), m.get("primary_habitat"),
                m.get("danger_rating", 1), json.dumps(m.get("weaknesses", [])), json.dumps(m.get("immunities", [])),
                m.get("description_md", ""), m.get("wiki_path", "")
            ))
            index_fts(m.get("id"), "monsters", m.get("name"), m.get("classification"), m.get("primary_habitat"), m.get("description_md"), m.get("wiki_path"))
            for drop in m.get("signature_drops", []):
                cur.execute("""
                    INSERT OR IGNORE INTO monster_loot_drops (monster_id, item_id, drop_chance, min_qty, max_qty)
                    VALUES (?, ?, 1.0, 1, 1)
                """, (m.get("id"), drop))
                total_drops += 1
        print(f"  ✓ Seeded {len(data):>3} Monsters   into table 'monsters' & FTS")
        print(f"  ✓ Seeded {total_drops:>3} Loot Drops into table 'monster_loot_drops'")

    # 3. Seed Skills
    skill_file = DATA_DIR / "skills.json"
    if skill_file.exists():
        data = json.loads(skill_file.read_text(encoding="utf-8")).get("skills", [])
        for s in data:
            cur.execute("""
                INSERT INTO skills (skill_id, name, job_path, skill_tier, skill_type, resource_pool, resource_cost, target_pattern, primary_effect, effect_magnitude, resonance_capable, polarity_affinity, legal_races, description_md, wiki_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                s.get("id"), s.get("name"), s.get("job_path"), s.get("tier"),
                s.get("type"), s.get("resource_pool"), s.get("resource_cost", 0),
                s.get("target"), s.get("primary_effect", "damage"), s.get("effect_magnitude", 1.0),
                1 if s.get("resonance_capable") else 0, s.get("polarity_affinity"),
                ", ".join(s.get("legal_races", ["All"])),
                s.get("description_md", ""), s.get("wiki_path", "")
            ))
            index_fts(s.get("id"), "skills", s.get("name"), f"{s.get('job_path', '')} / {s.get('type', '')}", s.get("polarity_affinity"), s.get("description_md"), s.get("wiki_path"))
        print(f"  ✓ Seeded {len(data):>3} Skills     into table 'skills' & FTS")

    # 4. Seed Equipment
    eq_file = DATA_DIR / "equipment.json"
    if eq_file.exists():
        data = json.loads(eq_file.read_text(encoding="utf-8")).get("equipment", [])
        for eq in data:
            cur.execute("""
                INSERT INTO equipment (equip_id, name, equipment_type, slot, rarity, job_class, terrestrial_element, master_polarity, item_power, base_atk, base_def, granted_skill, description_md, wiki_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                eq.get("id"), eq.get("name"), eq.get("equipment_type"), eq.get("slot"),
                eq.get("rarity"), eq.get("job_class"), eq.get("terrestrial_element"),
                eq.get("master_polarity"), eq.get("item_power", 100), eq.get("base_atk", 0),
                eq.get("base_def", 0), eq.get("granted_skill"),
                eq.get("description_md", ""), eq.get("wiki_path", "")
            ))
            index_fts(eq.get("id"), "equipment", eq.get("name"), f"{eq.get('equipment_type', '')} / {eq.get('slot', '')}", eq.get("job_class"), eq.get("description_md"), eq.get("wiki_path"))
        print(f"  ✓ Seeded {len(data):>3} Equipment  into table 'equipment' & FTS")

    # 5. Seed Factions
    fc_file = DATA_DIR / "factions.json"
    if fc_file.exists():
        data = json.loads(fc_file.read_text(encoding="utf-8")).get("factions", [])
        for fc in data:
            cur.execute("""
                INSERT INTO factions (faction_id, name, ideology, seat_of_power, leadership, currency, master_polarity, signature_unit, description_md, wiki_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fc.get("id"), fc.get("name"), fc.get("ideology"), fc.get("seat_of_power"),
                fc.get("leadership"), fc.get("currency"), fc.get("master_polarity"),
                fc.get("signature_unit"),
                fc.get("description_md", ""), fc.get("wiki_path", "")
            ))
            index_fts(fc.get("id"), "factions", fc.get("name"), fc.get("ideology"), fc.get("seat_of_power"), fc.get("description_md"), fc.get("wiki_path"))
        print(f"  ✓ Seeded {len(data):>3} Factions   into table 'factions' & FTS")

    # 6. Seed Places
    pl_file = DATA_DIR / "places.json"
    if pl_file.exists():
        data = json.loads(pl_file.read_text(encoding="utf-8")).get("places", [])
        for pl in data:
            cur.execute("""
                INSERT INTO places (place_id, name, location_kind, danger_level, governing_faction, master_polarity, terrestrial_element, description_md, wiki_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pl.get("id"), pl.get("name"), pl.get("location_kind"), pl.get("danger_level", 1),
                pl.get("governing_faction"), pl.get("master_polarity"), pl.get("terrestrial_element"),
                pl.get("description_md", ""), pl.get("wiki_path", "")
            ))
            index_fts(pl.get("id"), "places", pl.get("name"), pl.get("location_kind"), pl.get("governing_faction"), pl.get("description_md"), pl.get("wiki_path"))
        print(f"  ✓ Seeded {len(data):>3} Places     into table 'places' & FTS")

    # 7. Seed Items
    items_file = DATA_DIR / "items.json"
    if items_file.exists():
        data = json.loads(items_file.read_text(encoding="utf-8")).get("items", [])
        for it in data:
            cur.execute("""
                INSERT INTO items (item_id, name, item_kind, rarity, terrestrial_element, master_polarity, unit_value, description_md, wiki_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                it.get("id"), it.get("name"), it.get("item_kind"), it.get("rarity"),
                it.get("terrestrial_element"), it.get("master_polarity"), it.get("unit_value", 0),
                it.get("description_md", ""), it.get("wiki_path", "")
            ))
            index_fts(it.get("id"), "items", it.get("name"), it.get("item_kind"), it.get("master_polarity"), it.get("description_md"), it.get("wiki_path"))
        print(f"  ✓ Seeded {len(data):>3} Items      into table 'items' & FTS")

    # 8. Seed Quests
    quests_file = DATA_DIR / "quests.json"
    if quests_file.exists():
        data = json.loads(quests_file.read_text(encoding="utf-8")).get("quests", [])
        for q in data:
            cur.execute("""
                INSERT INTO quests (quest_id, title, quest_tier, recommended_item_power, giver, location, dialogue_script, description_md, wiki_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                q.get("id"), q.get("title"), q.get("quest_tier"), q.get("recommended_item_power", 100),
                q.get("giver"), q.get("location"), q.get("dialogue_script"),
                q.get("description_md", ""), q.get("wiki_path", "")
            ))
            index_fts(q.get("id"), "quests", q.get("title"), q.get("quest_tier"), q.get("location"), q.get("description_md"), q.get("wiki_path"))
        print(f"  ✓ Seeded {len(data):>3} Quests     into table 'quests' & FTS")

    # 9. Seed Recipes & Ingredients
    recipes_file = DATA_DIR / "recipes.json"
    if recipes_file.exists():
        data = json.loads(recipes_file.read_text(encoding="utf-8")).get("recipes", [])
        total_ingredients = 0
        for r in data:
            cur.execute("""
                INSERT INTO recipes (recipe_id, name, category, required_station, crafting_time_seconds, output_item, output_quantity, ingredients, description_md, wiki_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                r.get("id"), r.get("name"), r.get("category"), r.get("required_station"),
                r.get("crafting_time_seconds", 0), r.get("output_item"),
                r.get("output_quantity", 1), json.dumps(r.get("ingredients", [])),
                r.get("description_md", ""), r.get("wiki_path", "")
            ))
            index_fts(r.get("id"), "recipes", r.get("name"), r.get("category"), r.get("required_station"), r.get("description_md"), r.get("wiki_path"))
            for ing in r.get("ingredients", []):
                ing_id = ing.get("item_id") if isinstance(ing, dict) else ing
                qty = ing.get("quantity", 1) if isinstance(ing, dict) else 1
                cur.execute("""
                    INSERT OR REPLACE INTO recipe_ingredients (recipe_id, item_id, quantity)
                    VALUES (?, ?, ?)
                """, (r.get("id"), ing_id, qty))
                total_ingredients += 1
        print(f"  ✓ Seeded {len(data):>3} Recipes    into table 'recipes' & FTS")
        print(f"  ✓ Seeded {total_ingredients:>3} Ingredient Requirements into table 'recipe_ingredients'")

    # 10. Seed Place Routes & Transit Matrix
    routes_file = DATA_DIR / "routes.json"
    if routes_file.exists():
        data = json.loads(routes_file.read_text(encoding="utf-8")).get("routes", [])
        for rt in data:
            cur.execute("""
                INSERT INTO place_routes (route_id, from_place_id, to_place_id, distance_miles, terrain_type, elevation_change_ft, hazard_rating, standard_foot_hours, mount_hours, glider_crawler_hours, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rt.get("id"), rt.get("from_place_id"), rt.get("to_place_id"),
                rt.get("distance_miles", 10.0), rt.get("terrain_type", "Paved Road"),
                rt.get("elevation_change_ft", 0), rt.get("hazard_rating", 1),
                rt.get("standard_foot_hours", 3.0), rt.get("mount_hours", 2.0),
                rt.get("glider_crawler_hours", 1.5), rt.get("notes", "")
            ))
        print(f"  ✓ Seeded {len(data):>3} Place Routes into table 'place_routes'")

    # 11. Seed General Worldbuilding, Canon Lore & Systems into FTS
    lore_folders = [
        (WIKI_DIR / "terms" / "lore", "lore_concept", "World Mechanics & Metaphysics"),
        (WIKI_DIR / "terms" / "war", "war_doctrine", "Military Doctrine & War Law"),
        (WIKI_DIR / "terms" / "economy", "economy", "Trade & Economic Systems"),
        (WIKI_DIR / "terms" / "politics", "politics", "Politics & Statecraft"),
        (WIKI_DIR / "terms" / "memory", "memory_history", "History & Lineage"),
        (WIKI_DIR / "terms" / "progression", "progression", "Progression & Magic System"),
        (WIKI_DIR / "lore", "canon_lore", "Canon Lore & Biology"),
        (WIKI_DIR / "systems", "system_canon", "System Specification & Writing Guides"),
    ]

    indexed_lore_count = 0
    existing_fts_ids = {r[0] for r in cur.execute("SELECT entity_id FROM lore_search_fts").fetchall()}

    for folder, domain_key, default_role in lore_folders:
        if not folder.exists():
            continue
        for md_file in sorted(folder.glob("*.md")):
            if md_file.name in ["index.md", "README.md"]:
                continue
            try:
                content = md_file.read_text(encoding="utf-8")
            except Exception:
                continue

            entity_id = f"doc_{md_file.stem.lower().replace('-', '_')}"
            if entity_id in existing_fts_ids:
                continue

            title = md_file.stem.replace("-", " ")
            body = content

            fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
            if fm_match:
                body = fm_match.group(2).strip()
                t_m = re.search(r'title:\s*["\']?(.*?)["\']?$', fm_match.group(1), re.MULTILINE)
                if t_m and t_m.group(1).strip():
                    title = t_m.group(1).strip()
            else:
                h1_m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
                if h1_m:
                    title = h1_m.group(1).strip()

            rel_path = str(md_file.relative_to(CONVERGENCE_DIR))
            index_fts(
                entity_id=entity_id,
                domain=domain_key,
                name=title,
                role_or_type=default_role,
                faction_or_region="Oryn Canon Worldbuilding",
                desc=body,
                fpath=rel_path
            )
            existing_fts_ids.add(entity_id)
            indexed_lore_count += 1

    print(f"  ✓ Seeded {indexed_lore_count:>3} World Lore & System Articles into FTS ('lore_search_fts')")

    conn.commit()
    conn.close()
    print("-" * 65)
    print(f"✅ Local Game Database active and fully synced at: {DB_PATH}\n")

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
    print("CONVERGENCE GAME ENGINE DATABASE SAMPLES")
    print("=" * 75)

    samples = [
        (
            "1. Canonical Combat Stats Derivation View (v_character_combat_stats)",
            "SELECT name, birth_race, biological_state, max_hp, max_fp, max_sp, heat_capacity, base_phys_def, base_force_def FROM v_character_combat_stats WHERE char_id IN ('char_vaelin_pale_weaver', 'char_doran_the_unmade', 'char_kazan_the_faithful_blade', 'char_lyra_of_the_low_sinks') ORDER BY name"
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
            "SELECT domain, name, role_or_type, snippet(lore_search_fts, 5, '«', '»', '...', 15) AS excerpt FROM lore_search_fts WHERE lore_search_fts MATCH 'berserk OR colossus' LIMIT 5"
        )
    ]

    for title, query in samples:
        print(f"\n🔍 {title}:")
        print(f"   SQL: {query}")
        execute_user_query(query)

def main():
    parser = argparse.ArgumentParser(description="Convergence Local Game Database Runner")
    parser.add_argument("--seed", action="store_true", help="Rebuild and reseed data/game_world.db from data/*.json")
    parser.add_argument("--query-sample", action="store_true", help="Run sample game queries")
    parser.add_argument("--query", type=str, help="Execute a custom SQL query string")
    parser.add_argument("--search", "-s", type=str, help="Search lore using SQLite FTS5 full-text search")

    args = parser.parse_args()

    if not DB_PATH.exists() or args.seed:
        seed_database()

    if args.search:
        search_lore_fts(args.search)
    elif args.query:
        execute_user_query(args.query)
    elif args.query_sample:
        run_sample_queries()
    elif not args.seed:
        # Default run sample queries
        run_sample_queries()

if __name__ == "__main__":
    main()
