"""
Metadata discovery and book resolution.
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
from canonforge.core.manifest import find_universe_root

def get_book_metadata(book_path: Path) -> Dict[str, Any]:
    """Dynamically construct book metadata from toc.yaml, series.yaml, and universe.yaml."""
    book_slug = book_path.name
    meta = {
        "title": book_slug.replace("-", " ").title(),
        "subtitle": "",
        "author": "Author",
        "publisher": "CanonForge Publishing",
        "language": "en",
        "description": "Novel manuscript compiled by CanonForge.",
        "rights": "All rights reserved by the author.",
    }

    # 1. Parse toc.yaml
    toc_file = book_path / "toc.yaml"
    if toc_file.is_file():
        try:
            import yaml
            t_data = yaml.safe_load(toc_file.read_text(encoding="utf-8")) or {}
            book_info = t_data.get("book", {})
            if "title" in book_info:
                meta["title"] = book_info["title"]
            if "subtitle" in book_info:
                meta["subtitle"] = book_info["subtitle"]
            if "description" in book_info:
                meta["description"] = book_info["description"]
        except Exception:
            pass

    # 2. Parse series.yaml
    series_file = book_path.parent / "series.yaml"
    if series_file.is_file():
        try:
            import yaml
            s_data = yaml.safe_load(series_file.read_text(encoding="utf-8")) or {}
            if "author" in s_data:
                meta["author"] = s_data["author"]
            if "publisher" in s_data:
                meta["publisher"] = s_data["publisher"]
        except Exception:
            pass

    return meta

BOOK_METADATA: Dict[str, Dict[str, Any]] = {}

# ==============================================================================
# LIGHTWEIGHT MARKDOWN TO CLEAN XHTML/HTML CONVERTER
# ==============================================================================

def resolve_book_dir(book_slug: str, base_dir: Optional[Path] = None) -> Optional[Path]:
    ms_dir = base_dir
    if not ms_dir:
        curr = Path.cwd().resolve()
        for cand in [curr, *curr.parents]:
            if (cand / "manuscript").is_dir():
                ms_dir = cand / "manuscript"
                break
        if not ms_dir:
            ms_dir = find_universe_root() / "manuscript"

    p = ms_dir / book_slug
    if p.exists() and (p / "chapters").exists():
        return p
    for b_dir in list(ms_dir.glob(f"*/{book_slug}")) + list(ms_dir.glob(f"*/*{book_slug}*")):
        if b_dir.is_dir() and (b_dir / "chapters").exists():
            return b_dir
    for toc in ms_dir.glob("*/*/toc.yaml"):
        if book_slug.lower() in toc.parent.name.lower():
            return toc.parent
    return None


