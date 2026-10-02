"""
CanonForge Core: Unified Entity, Alias & Wikilink Resolver (OKF v0.3)
--------------------------------------------------------------------------------
Provides authoritative, bidirectional Obsidian wikilink validation and resolution
across wiki dossiers, aliases, and manuscript chapters.
Understands:
  - Piped links: [[target-slug|Display Name]]
  - Anchors: [[target-slug#section-name|Display Name]]
  - Direct alias links: [[Alias Name]] via frontmatter 'aliases:'
  - Internal manuscript links: [[ch02-the-sky-catcher]]
Emits fuzzy correction suggestions via difflib when typos occur.
"""

import re
import difflib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from canonforge.core.manifest import find_universe_root
from canonforge.core.resolver import get_all_chapters


def _extract_frontmatter_metadata(file_path: Path) -> Dict[str, Any]:
    """Extract title, aliases, and id from markdown frontmatter."""
    meta: Dict[str, Any] = {
        "title": file_path.stem.replace("-", " "),
        "aliases": [],
        "id": file_path.stem
    }
    try:
        text = file_path.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        if not m:
            return meta

        fm_text = m.group(1)
        in_aliases = False

        for line in fm_text.splitlines():
            line_s = line.strip()
            if not line_s or line_s.startswith("#"):
                continue

            if in_aliases:
                if line_s.startswith("-"):
                    val = line_s.lstrip("-").strip().strip('"').strip("'")
                    if val and val not in meta["aliases"]:
                        meta["aliases"].append(val)
                    continue
                elif ":" in line_s:
                    in_aliases = False

            if ":" in line_s:
                k, v = line_s.split(":", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k in ("title", "name") and v:
                    meta["title"] = v
                elif k == "id" and v:
                    meta["id"] = v
                elif k in ("aliases", "labels") and not v:
                    in_aliases = True
                elif k in ("aliases", "labels") and v:
                    for item in v.split(","):
                        val = item.strip().lstrip("-").strip().strip('"').strip("'")
                        if val and val not in meta["aliases"]:
                            meta["aliases"].append(val)
    except Exception:
        pass

    return meta


def build_universe_entity_index(universe_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    Build a comprehensive, bidirectional lookup index of all wiki entities
    and manuscript chapters in the universe.
    """
    u_root = universe_dir or find_universe_root()
    wiki_dir = u_root / "wiki"
    
    entities_by_stem: Dict[str, Dict[str, Any]] = {}
    entities_by_title: Dict[str, Dict[str, Any]] = {}
    entities_by_alias: Dict[str, Dict[str, Any]] = {}
    entities_by_id: Dict[str, Dict[str, Any]] = {}
    all_searchable_names: Dict[str, str] = {}  # lowercase -> original display

    # 1. Index Wiki Dossiers
    if wiki_dir.is_dir():
        for f in wiki_dir.rglob("*.md"):
            if f.name.startswith((".", "README", "SUMMARY", "TODO")):
                continue

            meta = _extract_frontmatter_metadata(f)
            stem = f.stem
            stem_clean = stem.replace("-", " ")
            title = meta["title"]
            eid = meta["id"]
            aliases = meta["aliases"]

            record = {
                "type": "wiki",
                "path": str(f.resolve()),
                "stem": stem,
                "title": title,
                "id": eid,
                "aliases": aliases
            }

            # Map stems
            entities_by_stem[stem.lower()] = record
            entities_by_stem[stem_clean.lower()] = record
            all_searchable_names[stem.lower()] = stem
            all_searchable_names[stem_clean.lower()] = stem_clean

            # Map title
            if title:
                entities_by_title[title.lower()] = record
                all_searchable_names[title.lower()] = title

            # Map ID
            if eid:
                entities_by_id[eid.lower()] = record
                all_searchable_names[eid.lower()] = eid

            # Map aliases
            for a in aliases:
                a_clean = a.strip()
                if a_clean:
                    entities_by_alias[a_clean.lower()] = record
                    all_searchable_names[a_clean.lower()] = a_clean

    # 2. Index Manuscript Chapters & Docs (for internal cross-chapter linking)
    chapters = get_all_chapters(u_root)
    chapters_by_stem: Dict[str, str] = {}
    for ch in chapters:
        ch_stem = ch.stem
        chapters_by_stem[ch_stem.lower()] = ch.name
        chapters_by_stem[ch_stem.replace("-", " ").lower()] = ch.name
        all_searchable_names[ch_stem.lower()] = ch_stem
        all_searchable_names[ch_stem.replace("-", " ").lower()] = ch_stem

    # Include special manuscript READMEs
    for ms_readme in (u_root / "manuscript").rglob("README.md"):
        chapters_by_stem["readme"] = ms_readme.name
        all_searchable_names["readme"] = "README"

    return {
        "universe_dir": str(u_root),
        "entities_by_stem": entities_by_stem,
        "entities_by_title": entities_by_title,
        "entities_by_alias": entities_by_alias,
        "entities_by_id": entities_by_id,
        "chapters_by_stem": chapters_by_stem,
        "all_searchable_names": all_searchable_names
    }


def resolve_wikilink(
    raw_target: str,
    index: Dict[str, Any]
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Resolve a wikilink target to its destination entity or chapter.
    Returns: (is_valid, resolved_entity_record, fuzzy_suggestion)
    """
    clean_target = raw_target.strip()
    
    # Strip anchor if present: [[target#anchor]] -> target
    if "#" in clean_target:
        clean_target = clean_target.split("#", 1)[0].strip()

    if not clean_target:
        return True, None, None  # Pure section anchor link within same page [[#Heading]]

    t_lower = clean_target.lower()
    t_hyphen = t_lower.replace(" ", "-")
    t_space = t_lower.replace("-", " ")

    # 1. Match wiki entity by stem
    if t_lower in index["entities_by_stem"]:
        return True, index["entities_by_stem"][t_lower], None
    if t_hyphen in index["entities_by_stem"]:
        return True, index["entities_by_stem"][t_hyphen], None
    if t_space in index["entities_by_stem"]:
        return True, index["entities_by_stem"][t_space], None

    # 2. Match wiki entity by canonical title
    if t_lower in index["entities_by_title"]:
        return True, index["entities_by_title"][t_lower], None
    if t_space in index["entities_by_title"]:
        return True, index["entities_by_title"][t_space], None

    # 3. Match wiki entity by declared alias
    if t_lower in index["entities_by_alias"]:
        return True, index["entities_by_alias"][t_lower], None

    # 4. Match wiki entity by ID
    if t_lower in index["entities_by_id"]:
        return True, index["entities_by_id"][t_lower], None

    # 5. Match manuscript chapter
    if t_lower in index["chapters_by_stem"]:
        return True, {"type": "chapter", "stem": clean_target}, None
    if t_hyphen in index["chapters_by_stem"]:
        return True, {"type": "chapter", "stem": clean_target}, None

    # Not found: compute fuzzy suggestion
    searchable_keys = list(index["all_searchable_names"].keys())
    matches = difflib.get_close_matches(t_lower, searchable_keys, n=1, cutoff=0.72)
    suggestion = index["all_searchable_names"][matches[0]] if matches else None

    return False, None, suggestion


def validate_chapter_wikilinks(
    ch_path: Path,
    index: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Scan a markdown chapter for broken or mistyped Obsidian wikilinks.
    Understands piped links, section anchors, and declared entity aliases.
    """
    if not ch_path.is_file():
        return []

    if index is None:
        index = build_universe_entity_index(find_universe_root(ch_path))

    text = ch_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    diagnostics = []

    # Find all [[...]] in body text (ignoring YAML frontmatter)
    in_frontmatter = False
    in_codeblock = False

    for line_idx, line in enumerate(lines, start=1):
        line_strip = line.strip()

        # Track frontmatter delimiters
        if line_idx == 1 and line_strip == "---":
            in_frontmatter = True
            continue
        elif in_frontmatter:
            if line_strip == "---":
                in_frontmatter = False
            continue

        # Track code blocks
        if line_strip.startswith("```"):
            in_codeblock = not in_codeblock
            continue
        if in_codeblock:
            continue

        # Find wikilinks on current line
        matches = re.finditer(r"\[\[([^\]]+)\]\]", line)
        for m in matches:
            raw_content = m.group(1).strip()
            if not raw_content:
                continue

            # Separate target and display alias if piped: [[target|display]]
            if "|" in raw_content:
                target_part, display_part = raw_content.split("|", 1)
                target_part = target_part.strip()
                display_part = display_part.strip()
            else:
                target_part = raw_content
                display_part = raw_content

            is_valid, entity_info, suggestion = resolve_wikilink(target_part, index)

            if not is_valid:
                # If target wasn't found, check if display_part happens to be a valid alias!
                if display_part != target_part:
                    valid_disp, d_info, _ = resolve_wikilink(display_part, index)
                    if valid_disp and d_info:
                        suggestion = d_info.get("stem") or d_info.get("title")

                # Format concrete suggestion
                if suggestion:
                    if "|" in raw_content:
                        sugg_text = f"Replace with [[{suggestion}|{display_part}]]"
                    else:
                        sugg_text = f"Replace with [[{suggestion}]]"
                else:
                    sugg_text = "Verify target file stem in wiki/ or declare alias in entity frontmatter."

                diagnostics.append({
                    "code": "LNK001",
                    "severity": "warning",
                    "file": ch_path.name,
                    "line": line_idx,
                    "snippet": line.strip(),
                    "link": raw_content,
                    "target": target_part,
                    "message": f"Broken Obsidian wikilink target: '[[{target_part}]]' does not resolve to any wiki dossier, alias, or chapter.",
                    "suggestion": sugg_text
                })

    return diagnostics
