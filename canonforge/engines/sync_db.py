#!/usr/bin/env python3
"""
sync_db.py

Unified CanonForge Lore (SSOT) to Game DB Compiler.
CLI entrypoint delegating to canonforge.engines.db.
"""

import sys
import argparse
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
WIKI_DIR = PACKAGE_ROOT / "wiki"
DATA_DIR = PACKAGE_ROOT / "data"

CHARACTERS_WIKI = WIKI_DIR / "terms" / "characters"
BESTIARY_WIKI = WIKI_DIR / "terms" / "monsters"
SKILLS_WIKI = WIKI_DIR / "terms" / "skills"
EQUIPMENT_WIKI = WIKI_DIR / "terms" / "equipment"
ITEMS_WIKI = WIKI_DIR / "terms" / "items"
RECIPES_WIKI = WIKI_DIR / "terms" / "recipes"
QUESTS_WIKI = WIKI_DIR / "terms" / "quests"
FACTIONS_WIKI = WIKI_DIR / "terms" / "factions"
PLACES_WIKI = WIKI_DIR / "terms" / "places"

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
