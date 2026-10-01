"""
Chapter draft target locator and Git-modified draft discovery.
"""
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent
MANUSCRIPT_DIR = PACKAGE_ROOT / "manuscript"

try:
    import character_profile as cp
    HAS_CP = True
except ImportError:
    HAS_CP = False

try:
    import book_navigator as bn
    HAS_BN = True
except ImportError:
    HAS_BN = False


# ==============================================================================
# TARGET CHAPTER RESOLUTION
# ==============================================================================

def find_chapter_target(
    query: Optional[str] = None,
    book_filter: Optional[str] = None,
    chapter_query: Optional[str] = None,
    allow_interactive: bool = True
) -> Optional[Path]:
    """Find target chapter markdown file by exact path, book+chapter, or filename query."""
    if HAS_BN:
        # Check if query is a book or book_filter is provided
        target_1 = book_filter or query
        target_2 = chapter_query if (book_filter or (query and bn.resolve_book(query))) else None
        res = bn.resolve_interactive_or_cli(target_1, target_2, allow_interactive=allow_interactive)
        if res:
            return res[1]
    if not query:
        # Check git modified chapters first
        git_mod = get_git_modified_chapters()
        if git_mod:
            if book_filter:
                filtered = [f for f in git_mod if book_filter.lower() in str(f).lower()]
                if filtered:
                    return filtered[0]
            return git_mod[0]
            
        # Fallback to the latest active chapter
        all_chaps = list(MANUSCRIPT_DIR.rglob("*.md"))
        valid = [f for f in all_chaps if "chapters" in str(f) and not f.name.startswith("compiled") and not f.name.startswith(".")]
        if valid:
            valid.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return valid[0]
        return None

    # Check direct file path
    p = Path(query)
    if p.exists() and p.is_file():
        return p

    p_conv = CONVERGENCE_DIR / query
    if p_conv.exists() and p_conv.is_file():
        return p_conv

    # Substring / stem match across manuscript
    q_clean = query.lower().replace(".md", "").strip()
    all_chaps = list(MANUSCRIPT_DIR.rglob("*.md"))
    valid = [f for f in all_chaps if "chapters" in str(f) and not f.name.startswith("compiled") and not f.name.startswith(".")]
    
    # 1. Exact match on stem or filename
    exact = [f for f in valid if f.stem.lower() == q_clean or f.name.lower() == q_clean]
    if exact:
        if book_filter:
            b_exact = [f for f in exact if book_filter.lower() in str(f).lower()]
            if b_exact:
                return b_exact[0]
        return exact[0]

    # 2. Number prefix match (e.g. "ch09" -> ch09-*.md)
    m = re.search(r"\b(?:ch)?(\d+)\b", q_clean)
    if m:
        num = int(m.group(1))
        prefix = f"ch{num:02d}-"
        num_matches = [f for f in valid if f.name.startswith(prefix)]
        if num_matches:
            if book_filter:
                b_num = [f for f in num_matches if book_filter.lower() in str(f).lower()]
                if b_num:
                    return b_num[0]
            return num_matches[0]

    # 3. Substring match
    sub = [f for f in valid if q_clean in f.stem.lower()]
    if sub:
        if book_filter:
            b_sub = [f for f in sub if book_filter.lower() in str(f).lower()]
            if b_sub:
                return b_sub[0]
        return sub[0]

    return None


resolve_target_chapter = find_chapter_target


def get_git_modified_chapters() -> List[Path]:
    """Retrieve list of currently modified manuscript chapters from git."""
    import subprocess
    modified = []
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain", "manuscript/"],
            cwd=str(CONVERGENCE_DIR),
            capture_output=True,
            text=True
        )
        for line in res.stdout.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2:
                fpath = CONVERGENCE_DIR / parts[-1]
                if fpath.suffix == ".md" and "chapters" in str(fpath) and fpath.exists():
                    modified.append(fpath)
    except Exception:
        pass
    return modified


# ==============================================================================
# FRONTMATTER & METADATA EXTRACTION
# ==============================================================================

def parse_frontmatter(text: str) -> Dict[str, Any]:
    """Extract YAML frontmatter into a clean dictionary."""
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    
    yaml_raw = parts[1]
    meta: Dict[str, Any] = {}
    current_list_key = None
    
    for line in yaml_raw.splitlines():
        line_clean = line.strip()
        if not line_clean or line_clean.startswith("#"):
            continue
            
        if line_clean.startswith("- ") and current_list_key:
            val = line_clean[2:].strip().strip('"').strip("'")
            meta.setdefault(current_list_key, []).append(val)
            continue
            
        if ":" in line_clean:
            current_list_key = None
            key, val = line_clean.split(":", 1)
            key = key.strip()
            val = val.strip()
            
            if val == "":
                current_list_key = key
                meta[key] = []
            else:
                val_clean = val.strip('"').strip("'")
                if val_clean.isdigit():
                    meta[key] = int(val_clean)
                else:
                    meta[key] = val_clean
                    
    return meta


