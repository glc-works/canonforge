"""
canonforge.engines.relations

Character Relationship Graph Engine & Continuity Auditor.
"""
from canonforge.engines.relations.timeline import (
    load_relationships_data,
    save_relationships_data,
    get_all_characters,
    resolve_character_name,
    resolve_active_relationship,
)
from canonforge.engines.relations.graph import (
    build_adjacency_graph,
    inspect_character_relations,
    find_relationship_path,
)
from canonforge.engines.relations.matrix import (
    build_cast_matrix,
    audit_chapter_relations,
)
from canonforge.engines.relations.exporter import (
    export_mermaid_diagram,
    sync_relationships_to_db,
)
from canonforge.engines.relations.mutations import (
    check_relationship_exists,
    add_relationship,
    update_relationship,
    add_timeline_slice,
)
from canonforge.engines.relations.cli import main

__all__ = [
    "load_relationships_data",
    "save_relationships_data",
    "get_all_characters",
    "resolve_character_name",
    "resolve_active_relationship",
    "build_adjacency_graph",
    "inspect_character_relations",
    "find_relationship_path",
    "build_cast_matrix",
    "audit_chapter_relations",
    "export_mermaid_diagram",
    "sync_relationships_to_db",
    "check_relationship_exists",
    "add_relationship",
    "update_relationship",
    "add_timeline_slice",
    "main",
]
