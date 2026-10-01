"""
CanonForge: SSOT Manifest Loader & Workspace Resolver
--------------------------------------------------------------------------------
Enforces Rule 1 (Hierarchy & Manifest SSOT) and Rule 2 (Zero Hardcoding).
Loads universe.yaml, series.yaml, and toc.yaml dynamically.
"""

import re
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from canonforge.core.exceptions import ManifestError

def load_yaml_file(path: Path) -> Dict[str, Any]:
    """Load and parse YAML file with graceful fallback for standard library environments."""
    if not path.is_file():
        raise ManifestError(f"Manifest not found: {path}")

    text = path.read_text(encoding="utf-8")
    if HAS_YAML:
        try:
            return yaml.safe_load(text) or {}
        except Exception as e:
            raise ManifestError(f"Error parsing YAML in {path}: {e}")

    # Pure standard library fallback: parse key: value pairs
    data = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^([a-zA-Z0-9_-]+):\s*[\"']?([^\"']*)[\"']?$", line)
        if m:
            key, val = m.group(1), m.group(2)
            data[key] = val
    return data

def find_universe_root(start_dir: Optional[Path] = None) -> Path:
    """Traverse upwards to locate enclosing universe.yaml."""
    curr = (start_dir or Path.cwd()).resolve()
    for parent in [curr, *curr.parents]:
        if (parent / "universe.yaml").is_file():
            return parent
    return curr

def find_workspace_root(start_dir: Optional[Path] = None) -> Path:
    """Locate the workspace root containing multiple universes."""
    curr = (start_dir or Path.cwd()).resolve()
    for parent in [curr, *curr.parents]:
        if (parent / "universe.yaml").is_file():
            return parent.parent
        if any(p.is_dir() and (p / "universe.yaml").is_file() for p in parent.iterdir() if not p.name.startswith(".")):
            return parent
    return curr
