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
    birth_race TEXT DEFAULT 'Human',
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
    (CASE WHEN biological_state LIKE '%Mechanical%' THEN 0 ELSE (force_stat * 4 + willpower * 3 + level * 2) END) AS max_fp,
    (40 + (vitality * 3) + (level * 2)) AS max_sp,
    (CASE WHEN biological_state LIKE '%Cyborg%' OR biological_state LIKE '%Mechanical%' THEN (50 + system_affinity * 4) ELSE 0 END) AS heat_capacity,
    (vitality * 2) AS base_phys_def,
    (willpower * 2) AS base_force_def,
    (strength * 2) AS base_phys_atk,
    (CASE WHEN biological_state LIKE '%Mechanical%' THEN 0 ELSE (force_stat * 2) END) AS base_force_atk
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
