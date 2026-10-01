#!/usr/bin/env python3
"""
init_db.py

Local Game Database Engine & Relational Query Runner for CanonForge.
CLI entrypoint delegating to canonforge.engines.db.
"""

import sys
import argparse
from pathlib import Path

from canonforge.engines.db.seeder import seed_database, DB_PATH
from canonforge.engines.db.query import (
    execute_user_query,
    search_lore_fts,
    run_sample_queries,
)

def main():
    parser = argparse.ArgumentParser(description="CanonForge Local Game Database Runner")
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
        parser.print_help()

if __name__ == "__main__":
    main()
