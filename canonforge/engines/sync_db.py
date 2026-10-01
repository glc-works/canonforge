#!/usr/bin/env python3
"""
sync_db.py

Unified CanonForge Lore (SSOT) to Game DB Compiler.
CLI entrypoint delegating to canonforge.engines.db.
"""

import sys
import argparse
from pathlib import Path

from canonforge.core.manifest import find_universe_root

UNIVERSE_DIR = find_universe_root()
WIKI_DIR = UNIVERSE_DIR / "wiki"
DATA_DIR = UNIVERSE_DIR / "data"

def _resolve_wiki_sub(*candidates: Path) -> Path:
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]

CHARACTERS_WIKI = _resolve_wiki_sub(WIKI_DIR / "terms" / "characters", WIKI_DIR / "characters")
BESTIARY_WIKI = _resolve_wiki_sub(WIKI_DIR / "database" / "bestiary", WIKI_DIR / "terms" / "monsters", WIKI_DIR / "monsters")
SKILLS_WIKI = _resolve_wiki_sub(WIKI_DIR / "database" / "skills", WIKI_DIR / "terms" / "skills", WIKI_DIR / "skills")
EQUIPMENT_WIKI = _resolve_wiki_sub(WIKI_DIR / "database" / "equipment", WIKI_DIR / "terms" / "equipment", WIKI_DIR / "equipment")
ITEMS_WIKI = _resolve_wiki_sub(WIKI_DIR / "database" / "items", WIKI_DIR / "terms" / "items", WIKI_DIR / "items")
RECIPES_WIKI = _resolve_wiki_sub(WIKI_DIR / "database" / "recipes", WIKI_DIR / "terms" / "recipes", WIKI_DIR / "recipes")
QUESTS_WIKI = _resolve_wiki_sub(WIKI_DIR / "database" / "quests", WIKI_DIR / "terms" / "quests", WIKI_DIR / "quests")
FACTIONS_WIKI = _resolve_wiki_sub(WIKI_DIR / "terms" / "factions", WIKI_DIR / "factions")
PLACES_WIKI = _resolve_wiki_sub(WIKI_DIR / "terms" / "places", WIKI_DIR / "places")

from canonforge.engines.db.scanner import scan_markdown_entities
from canonforge.engines.db.validator import validate_all
from canonforge.engines.db.json_sync import sync_all_json
from canonforge.engines.db.sql_export import export_all_sql_seeds

def main():
    parser = argparse.ArgumentParser(description="Unified CanonForge Lore (SSOT) to Game DB Compiler")
    parser.add_argument("--validate", action="store_true", help="Validate frontmatter and cross-references across all 9 domains")
    parser.add_argument("--sync", action="store_true", help="Compile markdown SSOT to data/*.json and export SQL seeds")
    parser.add_argument("--export-sql", action="store_true", help="Export PostgreSQL seed scripts only")
    
    args = parser.parse_args()
    
    chars = scan_markdown_entities(CHARACTERS_WIKI, "Character Entity")
    bestiary = scan_markdown_entities(BESTIARY_WIKI, "Bestiary Entity")
    skills = scan_markdown_entities(SKILLS_WIKI, "Skill Entity")
    equipment = scan_markdown_entities(EQUIPMENT_WIKI, "Equipment Entity")
    items = scan_markdown_entities(ITEMS_WIKI, "Item Entity")
    recipes = scan_markdown_entities(RECIPES_WIKI, "Recipe Entity")
    quests = scan_markdown_entities(QUESTS_WIKI, "Quest Entity")
    factions = scan_markdown_entities(FACTIONS_WIKI, "Faction Entity")
    places = scan_markdown_entities(PLACES_WIKI, "Location Entity")
    
    if args.sync:
        validate_all(chars, bestiary, skills, equipment, items, recipes, quests, factions, places)
        sync_all_json(chars, bestiary, skills, equipment, items, recipes, quests, factions, places)
        export_all_sql_seeds(chars, bestiary, skills, equipment, items, recipes, quests, factions, places)
    elif args.export_sql:
        export_all_sql_seeds(chars, bestiary, skills, equipment, items, recipes, quests, factions, places)
    else:
        validate_all(chars, bestiary, skills, equipment, items, recipes, quests, factions, places)

if __name__ == "__main__":
    main()
