"""
Mermaid diagram generation & SQLite database synchronization
"""
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional
from canonforge.engines.relations.timeline import resolve_active_relationship, DB_PATH

def export_mermaid_diagram(data: Dict[str, Any], ao_year: Optional[int] = None) -> str:
    """Generate clean Mermaid diagram string of the relationship network."""
    lines = ["graph TD", "    %% CanonForge Canonical Relationship Graph", ""]
    
    lines.append("    classDef kinship fill:#e8f8f5,stroke:#1abc9c,stroke-width:2px,color:#16a085;")
    lines.append("    classDef comrade fill:#eaf2f8,stroke:#2980b9,stroke-width:2px,color:#2471a3;")
    lines.append("    classDef romance fill:#fdf2e9,stroke:#e67e22,stroke-width:2px,color:#d35400;")
    lines.append("    classDef rivalry fill:#fdedec,stroke:#c0392b,stroke-width:2px,color:#922b21;")
    lines.append("    classDef tension fill:#fcf3cf,stroke:#f39c12,stroke-width:2px,color:#b7950b;")
    lines.append("    classDef mentor fill:#f4ecf7,stroke:#8e44ad,stroke-width:2px,color:#6c3483;")
    lines.append("")
    
    def sanitize_id(name: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_]", "_", name)
        
    seen_edges = set()
    for rel in data.get("relationships", []):
        src = rel["source"]
        tgt = rel["target"]
        edge_key = tuple(sorted([src, tgt]))
        
        is_sym = rel.get("symmetry") == "symmetric"
        if is_sym and edge_key in seen_edges:
            continue
        seen_edges.add(edge_key)
        
        active = resolve_active_relationship(rel, ao_year=ao_year)
        id_src = sanitize_id(src)
        id_tgt = sanitize_id(tgt)
        label = active["sub_type"].replace("_", " ")
        
        arrow = "---" if is_sym else "-->"
        lines.append(f'    {id_src}["{src}"] {arrow}|"{label}"| {id_tgt}["{tgt}"]')
        
    return "\n".join(lines)


# ==============================================================================
# SQLITE SEEDING & SYNC
# ==============================================================================

def sync_relationships_to_db(data: Dict[str, Any]) -> bool:
    """Seed relationship records into SQLite character_relations table."""
    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}. Run `./ax db` or `./ax update` first.")
        return False
        
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Ensure schema is up to date
    cur.execute("DROP TABLE IF EXISTS character_relations;")
    cur.execute("""
    CREATE TABLE character_relations (
        relation_id TEXT PRIMARY KEY,
        source_char TEXT NOT NULL,
        target_char TEXT NOT NULL,
        relation_type TEXT NOT NULL,
        sub_type TEXT,
        sentiment REAL DEFAULT 0.0,
        symmetry TEXT DEFAULT 'directed',
        active_phase TEXT DEFAULT 'All',
        dynamic_state TEXT,
        timeline_json TEXT,
        notes TEXT
    );
    """)
    
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rel_source ON character_relations(source_char);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rel_target ON character_relations(target_char);")
    
    cur.execute("DELETE FROM character_relations;")
    inserted = 0
    for rel in data.get("relationships", []):
        cur.execute("""
            INSERT OR REPLACE INTO character_relations 
            (relation_id, source_char, target_char, relation_type, sub_type, sentiment, symmetry, active_phase, dynamic_state, timeline_json, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rel.get("id"),
            rel.get("source"),
            rel.get("target"),
            rel.get("relation_type"),
            rel.get("sub_type"),
            rel.get("sentiment", 0.0),
            rel.get("symmetry", "directed"),
            rel.get("active_phase", "All"),
            rel.get("dynamic_state", ""),
            json.dumps(rel.get("timeline", [])),
            rel.get("notes", "")
        ))
        inserted += 1
        
    conn.commit()
    conn.close()
    print(f"  ✓ Synchronized {inserted} character relationships into SQLite table 'character_relations'.")
    return True


# ==============================================================================
# RELATIONSHIP CRUD & TOPOLOGY SEPARATION
# ==============================================================================

