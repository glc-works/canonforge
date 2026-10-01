"""
Smart Chapter & Manuscript Context Resolver
--------------------------------------------------------------------------------
Provides intuitive, friction-free chapter location for authors and editors:
  - Shorthand notations: '2.1', 'b2c1', 'b1.ch03', 'ch05', '12'
  - Partial slug/title queries: 'salt-trunk', 'river-pebble', 'anvil'
  - Active draft resolution: defaults to most recently edited chapter
  - Multi-book disambiguation with recency weighting
"""

import os
import re
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from canonforge.core.manifest import find_universe_root


def get_all_chapters(universe_dir: Optional[Path] = None, book_filter: Optional[str] = None) -> List[Path]:
    """Discover all valid manuscript chapter markdown files."""
    u_root = universe_dir or find_universe_root()
    ms_dir = u_root / "manuscript"
    search_dir = ms_dir if ms_dir.is_dir() else u_root

    chapters: List[Path] = []
    for f in search_dir.rglob("*.md"):
        if f.name.startswith((".", "README", "MASTER-", "SUMMARY", "TODO", "CHANGELOG")):
            continue
        parts = f.parts
        if any(p in parts for p in ("_build", "compiled", "exports", "darlings", "wiki", "lore", "templates")):
            continue
        # Must be in chapters directory or have chXX naming or toc registration
        if "chapters" in parts or re.match(r"^ch\d+", f.name, re.IGNORECASE) or (f.parent / "toc.yaml").is_file():
            chapters.append(f)

    if book_filter:
        b_clean = book_filter.lower().replace("_", "-")
        chapters = [c for c in chapters if b_clean in str(c).lower().replace("_", "-")]

    return sorted(chapters)


def get_active_draft(universe_dir: Optional[Path] = None) -> Optional[Path]:
    """Locate the most recently modified chapter markdown file (the writer's active draft)."""
    chapters = get_all_chapters(universe_dir)
    if not chapters:
        return None
    # Sort by mtime descending
    chapters.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return chapters[0]


def _parse_shorthand(query: str) -> Optional[Tuple[Optional[int], int]]:
    """Parse shorthand expressions like '2.1' (Book 2, Ch 1) or 'ch04' (Ch 4)."""
    q = query.strip().lower()
    
    # Format: '2.1', '2:1', 'b2c1', 'b02.ch01'
    m_bc = re.match(r"^b(?:ook)?[-_]?(\d+)[.:/c_-]+(?:ch)?[-_]?(\d+)$", q)
    if m_bc:
        return int(m_bc.group(1)), int(m_bc.group(2))
    
    m_dot = re.match(r"^(\d+)[.:/](\d+)$", q)
    if m_dot:
        return int(m_dot.group(1)), int(m_dot.group(2))

    # Format: 'ch05', 'ch-5', 'chapter-5', '5'
    m_c = re.match(r"^(?:ch|chapter)?[-_]?(\d+)$", q)
    if m_c:
        return None, int(m_c.group(1))

    return None


def resolve_chapter(
    query: Optional[str] = None,
    universe_dir: Optional[Path] = None,
    book_filter: Optional[str] = None,
    prefer_active: bool = True
) -> Optional[Path]:
    """Smart resolve a chapter path from query or active draft."""
    u_root = universe_dir or find_universe_root()
    chapters = get_all_chapters(u_root, book_filter=book_filter)
    if not chapters:
        return None

    if not query:
        # Default to active draft (most recently edited)
        if prefer_active:
            return get_active_draft(u_root)
        return chapters[0]

    # 1. Exact path match
    direct = Path(query)
    if direct.is_file():
        return direct
    direct_rel = u_root / query
    if direct_rel.is_file():
        return direct_rel

    # 2. Parse numeric / book shorthand
    parsed = _parse_shorthand(query)
    if parsed:
        target_book, target_ch = parsed
        candidates: List[Path] = []
        # 2a. Check direct filename match
        for ch in chapters:
            parent_str = str(ch.parent).lower()
            ch_num_match = re.search(r"ch(?:apter)?[-_]?0*(\d+)", ch.name, re.IGNORECASE)
            
            book_matched = True
            if target_book is not None:
                book_matched = (
                    f"book-{target_book}" in parent_str or
                    f"book-0{target_book}" in parent_str or
                    f"book_{target_book}" in parent_str or
                    f"/{target_book}/" in parent_str
                )

            if book_matched and ch_num_match and int(ch_num_match.group(1)) == target_ch:
                candidates.append(ch)

        if candidates:
            candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return candidates[0]

        # 2b. Check TOC act/chapter ordering
        for toc_file in u_root.glob("manuscript/*/*/toc.yaml"):
            parent_name = toc_file.parent.name.lower()
            if target_book is not None:
                if not (f"book-{target_book}" in parent_name or f"book-0{target_book}" in parent_name or f"book_{target_book}" in parent_name):
                    continue
            try:
                import yaml
                data = yaml.safe_load(toc_file.read_text(encoding="utf-8")) or {}
                ordered_ch: List[str] = []
                for act in data.get("acts", []):
                    for ch_entry in act.get("chapters", []):
                        fn = ch_entry.get("file", ch_entry) if isinstance(ch_entry, dict) else str(ch_entry)
                        ordered_ch.append(fn)
                if 1 <= target_ch <= len(ordered_ch):
                    matched_name = ordered_ch[target_ch - 1]
                    for cand in [toc_file.parent / "chapters" / matched_name, toc_file.parent / matched_name]:
                        if cand.is_file():
                            return cand
            except Exception:
                pass

    # 3. Slug / keyword substring match
    q_norm = query.lower().replace("_", "-")
    exact_stem_matches = [c for c in chapters if q_norm == c.stem.lower()]
    if exact_stem_matches:
        exact_stem_matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return exact_stem_matches[0]

    partial_matches = [c for c in chapters if q_norm in c.stem.lower() or q_norm in c.name.lower()]
    if partial_matches:
        partial_matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return partial_matches[0]

    # 4. Fallback search inside toc.yaml entries
    for toc_file in u_root.glob("manuscript/*/*/toc.yaml"):
        try:
            txt = toc_file.read_text(encoding="utf-8")
            if q_norm in txt.lower():
                # Locate chapter file in that book
                b_dir = toc_file.parent
                for cand in b_dir.rglob("*.md"):
                    if q_norm in cand.name.lower():
                        return cand
        except Exception:
            pass

    return None
