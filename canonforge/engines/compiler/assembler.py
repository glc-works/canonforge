"""
Manuscript chapter parser and multi-act assembler.
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent
MANUSCRIPT_DIR = PACKAGE_ROOT / "manuscript"

def parse_scene_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """Parse scene file, extracting frontmatter metadata and body prose."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return None

    meta: Dict[str, Any] = {}
    body = content

    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if fm_match:
        yaml_text = fm_match.group(1)
        body = content[fm_match.end():]
        try:
            meta = yaml.safe_load(yaml_text) or {}
        except Exception:
            # Fallback regex parser if PyYAML fails on complex frontmatter
            meta = {}

    clean_body = re.sub(r"^>.*$\n?", "", body, flags=re.MULTILINE)
    clean_body = re.sub(r"^---\s*$\n?", "", clean_body, flags=re.MULTILINE)
    # Strip any hardcoded markdown headings at the top like '# ACT 1' or '## Chapter 1: Foo'
    clean_body = re.sub(r"^#\s+ACT\s+.*$\n?", "", clean_body, flags=re.MULTILINE)
    clean_body = re.sub(r"^##\s+Chapter\s+.*$\n?", "", clean_body, flags=re.MULTILINE)
    clean_body = re.sub(r"^\*POV:.*$\n?", "", clean_body, flags=re.MULTILINE)
    clean_body = clean_body.strip()

    # Extract and resolve Obsidian/Wiki cross-links:
    # During writing: [[Character-Name|Alias]] or [[Faction]] links to lore
    # During compilation: resolves to clean text ("Character", "Faction")
    auto_entities = []
    wikilink_matches = re.findall(r"\[\[(.*?)\]\]", body)
    for wl in wikilink_matches:
        target = wl.split("|")[0].split("#")[0].strip()
        if target:
            entity_label = target.replace("-", " ").title()
            if entity_label not in auto_entities:
                auto_entities.append(entity_label)

    def resolve_wikilink(match):
        full = match.group(1)
        if "|" in full:
            return full.split("|", 1)[1]
        target = full.split("#", 1)[0].strip()
        return target.replace("-", " ")

    clean_body = re.sub(r"\[\[(.*?)\]\]", resolve_wikilink, clean_body)

    words = len(re.findall(r"\b\w+\b", clean_body))

    title = meta.get("title")
    if not title:
        raw_name = file_path.stem
        # Remove any leading chXX- if present
        raw_name = re.sub(r"^ch\d+-", "", raw_name)
        title = raw_name.replace("-", " ").title()
    else:
        title = str(title).strip('"').strip("'")

    pov = meta.get("pov") or meta.get("pov_character") or "Omniscient"
    setting = meta.get("location") or meta.get("setting") or "Unknown"
    timeline = meta.get("timeline") or meta.get("timeline_anchor") or "Unknown"
    characters = meta.get("characters") or meta.get("characters_present") or []
    if not isinstance(characters, list):
        characters = [characters]
    for ent in auto_entities:
        if ent not in characters:
            characters.append(ent)

    return {
        "path": file_path,
        "filename": file_path.name,
        "title": title,
        "pov": pov,
        "setting": setting,
        "timeline_anchor": timeline,
        "characters_present": characters,
        "target_words": meta.get("target_words", 3000),
        "actual_words": words,
        "raw_body": body,
        "clean_body": clean_body,
        "meta": meta
    }

def load_from_manifest(book_dir: Path) -> Optional[Dict[str, Any]]:
    """Load and assemble chapters dynamically from toc.yaml."""
    toc_path = book_dir / "toc.yaml"
    if not toc_path.exists():
        return None

    try:
        toc = yaml.safe_load(toc_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error parsing {toc_path}: {e}", file=sys.stderr)
        return None

    chapters_dir = book_dir / "chapters"
    assembled_chapters = []
    global_ch_num = 1

    acts = toc.get("acts", [])
    for act_idx, act_info in enumerate(acts, 1):
        act_num = act_info.get("act", act_idx)
        act_title = act_info.get("title", f"Act {act_num}")
        ch_files = act_info.get("chapters", [])

        for ch_file in ch_files:
            file_path = chapters_dir / ch_file
            if not file_path.exists():
                # Check directly in book_dir for backwards compatibility
                file_path = book_dir / ch_file
            
            if not file_path.exists():
                print(f"⚠️ Warning: Chapter file not found: {ch_file} in {book_dir}", file=sys.stderr)
                continue

            parsed = parse_scene_file(file_path)
            if parsed:
                parsed["act_num"] = act_num
                parsed["act_title"] = act_title
                parsed["chapter_num"] = global_ch_num
                assembled_chapters.append(parsed)
                global_ch_num += 1

    return {
        "manifest": toc,
        "chapters": assembled_chapters
    }

def discover_chapters_fallback(book_dir: Path) -> List[Dict[str, Any]]:
    """Fallback scanner if toc.yaml is absent."""
    chapters = []
    for f in sorted(book_dir.rglob("*.md")):
        if "archive" in f.parts:
            continue
        if f.name.lower() in ["readme.md", "index.md", "summary.md", "master-outline.md", "outline.md"]:
            continue
        parsed = parse_scene_file(f)
        if parsed:
            chapters.append(parsed)
    return chapters

def compile_manuscript(chapters: List[Dict[str, Any]], manifest: Optional[Dict[str, Any]], book_name: str, output_path: Path):
    """Compile clean combined markdown manuscript with dynamic numbering."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    book_title = manifest.get("title", book_name.replace("-", " ").title()) if manifest else book_name.replace("-", " ").title()
    series_name = manifest.get("series", "Original Saga") if manifest else "Original Saga"
    edition_label = manifest.get("edition", "Studio Authoritative Edition") if manifest else "Studio Authoritative Edition"

    epigraph_text = None
    epigraph_author = None
    if manifest and "epigraph" in manifest:
        epigraph_text = manifest["epigraph"].get("text")
        epigraph_author = manifest["epigraph"].get("attribution")

    lines = [
        f"% {book_title}",
        f"% {series_name}",
        f"% {edition_label}",
        "",
        "---",
        ""
    ]

    if epigraph_text:
        lines.append(f"> *\"{epigraph_text}\"*")
        if epigraph_author:
            lines.append(f"> — {epigraph_author}")
        lines.append("")
        lines.append("---")
        lines.append("")

    current_act = None

    for ch in chapters:
        act_num = ch.get("act_num")
        act_title = ch.get("act_title")
        if act_num and act_num != current_act:
            current_act = act_num
            lines.append(f"\n\n# ACT {act_num}: {act_title.upper()}\n\n")

        ch_num = ch.get("chapter_num", "")
        ch_label = f"Chapter {ch_num}: " if ch_num else ""
        lines.append(f"## {ch_label}{ch['title']}\n")
        lines.append(f"*POV: {ch['pov']} · Location: {ch['setting']} · Timeline: {ch['timeline_anchor']}*\n\n")
        lines.append(ch["clean_body"])
        lines.append("\n\n* * *\n\n")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"📖 Compiled clean reader manuscript ({len(chapters)} chapters) to: {output_path}")


def resolve_book_dir(query: str) -> Optional[Path]:
    p = MANUSCRIPT_DIR / query
    if p.is_dir() and (p / "chapters").exists():
        return p

    for b_dir in MANUSCRIPT_DIR.glob(f"*/{query}"):
        if b_dir.is_dir() and (b_dir / "chapters").exists():
            return b_dir

    try:
        from book_navigator import BOOK_REGISTRY
        q_clean = query.lower().strip()
        for reg in BOOK_REGISTRY:
            if q_clean == reg["id"].lower() or q_clean in [a.lower() for a in reg["aliases"]] or str(reg["num"]) == q_clean:
                cand = MANUSCRIPT_DIR / reg["id"]
                if cand.is_dir():
                    return cand
    except Exception:
        pass

    for toc in MANUSCRIPT_DIR.glob("*/*/toc.yaml"):
        b_cand = toc.parent
        if query.lower() in b_cand.name.lower() or query.lower() in b_cand.parent.name.lower():
            return b_cand
    return None

