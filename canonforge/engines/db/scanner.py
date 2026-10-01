"""
Entity markdown scanner and YAML frontmatter parser.
"""
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

def parse_yaml_frontmatter(content: str) -> Optional[Dict[str, Any]]:
    """Robust YAML frontmatter parser supporting PyYAML with fallback."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return None
    
    yaml_text = match.group(1)
    if HAS_YAML:
        try:
            loaded = yaml.safe_load(yaml_text)
            if isinstance(loaded, dict):
                return loaded
        except Exception:
            pass
    
    data: Dict[str, Any] = {}
    current_key = None
    in_list = False
    
    for line in yaml_text.splitlines():
        line_clean = line.strip()
        if not line_clean or line_clean.startswith("#"):
            continue
            
        if line_clean.startswith("- "):
            if current_key and in_list:
                item = line_clean[2:].strip().strip('"').strip("'")
                data[current_key].append(item)
            continue
            
        if ":" in line:
            parts = line.split(":", 1)
            key = parts[0].strip()
            raw_val = parts[1].strip()
            
            # Remove trailing comments if not quoted
            if " #" in raw_val and not (raw_val.startswith('"') or raw_val.startswith("'")):
                raw_val = raw_val.split(" #", 1)[0].strip()
                
            if raw_val == "":
                data[key] = []
                current_key = key
                in_list = True
            elif raw_val.startswith("[") and raw_val.endswith("]"):
                items = [x.strip().strip('"').strip("'") for x in raw_val[1:-1].split(",") if x.strip()]
                data[key] = items
                in_list = False
                current_key = key
            else:
                in_list = False
                current_key = key
                val = raw_val.strip('"').strip("'")
                if val.lower() == "true":
                    data[key] = True
                elif val.lower() == "false":
                    data[key] = False
                elif val.lower() == "null" or val == "":
                    data[key] = None
                elif re.match(r"^-?\d+$", val):
                    data[key] = int(val)
                elif re.match(r"^-?\d+\.\d+$", val):
                    data[key] = float(val)
                else:
                    data[key] = val
                    
    return data

def extract_body_markdown(content: str) -> str:
    """Extract markdown text following the YAML frontmatter delimiter."""
    m = re.match(r"^---\s*\n.*?\n---\s*\n(.*)$", content, re.DOTALL)
    if m:
        return m.group(1).strip()
    return ""

def scan_markdown_entities(directory: Path, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Scan all markdown files in a directory and extract frontmatter metadata and markdown body."""
    entities = []
    if not directory.exists():
        return entities
        
    for md_file in sorted(directory.glob("*.md")):
        if md_file.name in ["index.md", "README.md"]:
            continue
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"Warning: Failed to read {md_file}: {e}", file=sys.stderr)
            continue
            
        meta = parse_yaml_frontmatter(content)
        if meta:
            if entity_type is None or meta.get("type") == entity_type:
                meta["_file_path"] = str(md_file.relative_to(CONVERGENCE_DIR))
                meta["_filename"] = md_file.name
                meta["description_md"] = extract_body_markdown(content)
                entities.append(meta)
                
    return entities

def escape_sql(val: Any) -> str:
    """Escape strings for SQL inclusion."""
    if val is None:
        return "NULL"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, list):
        items_str = ", ".join(f'"{str(x).replace("\"", "\\\"")}"' for x in val)
        return f"'{items_str}'"
    s = str(val).replace("'", "''")
    return f"'{s}'"

# ==============================================================================
# AUDIT & VALIDATION
# ==============================================================================
