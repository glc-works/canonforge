"""
canonforge.engines.db

Relational Worldbuilding Database & Lore Synchronization Engine.
"""

from canonforge.engines.db.scanner import (
    parse_yaml_frontmatter,
    extract_body_markdown,
    scan_markdown_entities,
    escape_sql,
)
from canonforge.engines.db.validator import validate_all
from canonforge.engines.db.json_sync import sync_all_json
from canonforge.engines.db.sql_export import export_all_sql_seeds
from canonforge.engines.db.seeder import (
    clean_wikilinks,
    sanitize_fts_query,
    get_schema_ddl,
    get_connection,
    seed_database,
)
from canonforge.engines.db.query import (
    execute_user_query,
    search_lore_fts,
    run_sample_queries,
)

__all__ = [
    "parse_yaml_frontmatter",
    "extract_body_markdown",
    "scan_markdown_entities",
    "escape_sql",
    "validate_all",
    "sync_all_json",
    "export_all_sql_seeds",
    "clean_wikilinks",
    "sanitize_fts_query",
    "get_schema_ddl",
    "get_connection",
    "seed_database",
    "execute_user_query",
    "search_lore_fts",
    "run_sample_queries",
]
