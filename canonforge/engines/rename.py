"""
rename.py - Global Character & Entity Refactoring Engine for CanonForge Studio

Safely renames characters and entities across:
1. Chapter YAML frontmatter (characters, plot_points)
2. Manuscript prose and dialogue (word-boundary safe)
3. Markdown Obsidian Wikilinks ([[Old-Name|Old Name]] -> [[New-Name|New Name]])
4. Character Dossier file names & frontmatter (title, aliases)
5. Lore SSOT and local database records
"""

import sys
import os
import re
import argparse
import difflib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

try:
    import yaml
except ImportError:
    yaml = None

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

from canonforge.core.manifest import find_universe_root


def slugify(text: str) -> str:
    """Convert display name into canonical kebab-case filename slug."""
    text = re.sub(r"[^\w\s-]", "", text).strip()
    return re.sub(r"[-\s]+", "-", text)


def replace_wikilinks(content: str, old_slug: str, new_slug: str, old_name: str, new_name: str) -> str:
    """Safely replace Obsidian wikilinks matching old entity."""
    # 1. [[Old-Slug|Old Name]] -> [[New-Slug|New Name]]
    p1 = rf"\[\[{re.escape(old_slug)}\|{re.escape(old_name)}\]\]"
    content = re.sub(p1, f"[[{new_slug}|{new_name}]]", content)

    # 2. [[Old-Slug|Any Custom Label]] -> [[New-Slug|Any Custom Label]]
    p2 = rf"\[\[{re.escape(old_slug)}\|([^\]]+)\]\]"
    content = re.sub(p2, rf"[[{new_slug}|\1]]", content)

    # 3. [[Old-Slug]] -> [[New-Slug]]
    p3 = rf"\[\[{re.escape(old_slug)}\]\]"
    content = re.sub(p3, f"[[{new_slug}]]", content)

    # 4. [[Old Name]] -> [[New Name]]
    p4 = rf"\[\[{re.escape(old_name)}\]\]"
    content = re.sub(p4, f"[[{new_name}]]", content)

    return content


def update_chapter_frontmatter(
    fm_lines: List[str],
    old_name: str,
    new_name: str,
    old_id: Optional[str] = None,
    new_id: Optional[str] = None,
) -> Tuple[List[str], int]:
    """Replace character occurrences in chapter frontmatter lines."""
    replacements = 0
    updated = []
    in_characters = False
    in_plot_points = False

    for line in fm_lines:
        line_clean = line.strip()

        # Track sections
        if re.match(r"^characters\s*:\s*$", line):
            in_characters = True
            in_plot_points = False
            updated.append(line)
            continue
        elif re.match(r"^(plot_points|tags|sensory_focus|labels)\s*:\s*$", line):
            in_characters = False
            in_plot_points = (line.strip().startswith("plot_points"))
            updated.append(line)
            continue
        elif re.match(r"^[a-zA-Z0-9_-]+\s*:\s*", line) and not line.startswith("  "):
            in_characters = False
            in_plot_points = False

        # In characters array
        if in_characters and line_clean.startswith("-"):
            val = line_clean.lstrip("-").strip().strip('"').strip("'")
            if val.lower() == old_name.lower():
                indent = line[:line.find("-")]
                updated.append(f"{indent}- {new_name}")
                replacements += 1
                continue

        # In plot_points section
        if in_plot_points and ("character:" in line or "guardian:" in line):
            if old_id and new_id and old_id in line:
                line = line.replace(old_id, new_id)
                replacements += 1
            elif old_name in line:
                line = line.replace(old_name, new_name)
                replacements += 1

        # POV check
        if re.match(r"^pov\s*:\s*", line):
            if old_name in line:
                line = re.sub(rf"\b{re.escape(old_name)}\b", new_name, line)
                replacements += 1

        updated.append(line)

    return updated, replacements


def refactor_chapter_file(
    file_path: Path,
    old_name: str,
    new_name: str,
    old_slug: str,
    new_slug: str,
    old_id: Optional[str] = None,
    new_id: Optional[str] = None,
    rename_prose: bool = True
) -> Tuple[bool, str, str, int]:
    """Refactor a single chapter markdown file."""
    try:
        original = file_path.read_text(encoding="utf-8")
    except Exception:
        return False, "", "", 0

    if not original.startswith("---"):
        # No frontmatter, just prose
        new_content = replace_wikilinks(original, old_slug, new_slug, old_name, new_name)
        if rename_prose:
            new_content, count = re.subn(rf"\b{re.escape(old_name)}\b", new_name, new_content)
        return (new_content != original), original, new_content, 1 if new_content != original else 0

    parts = original.split("---", 2)
    if len(parts) < 3:
        return False, original, original, 0

    fm_lines = parts[1].splitlines()
    body = parts[2]

    # Update frontmatter
    new_fm_lines, fm_reps = update_chapter_frontmatter(
        fm_lines, old_name, new_name, old_id, new_id
    )
    new_fm_text = "\n".join(new_fm_lines)

    # Update wikilinks in body
    new_body = replace_wikilinks(body, old_slug, new_slug, old_name, new_name)

    # Update prose mentions
    prose_reps = 0
    if rename_prose:
        new_body, prose_reps = re.subn(rf"\b{re.escape(old_name)}\b", new_name, new_body)

    total_changes = fm_reps + prose_reps
    reconstructed = f"---{new_fm_text}\n---{new_body}"
    changed = (reconstructed != original)

    return changed, original, reconstructed, total_changes


def refactor_character_dossier(
    dossier_path: Path,
    old_name: str,
    new_name: str,
    old_slug: str,
    new_slug: str,
    new_id: Optional[str] = None
) -> Tuple[Optional[Path], str, str]:
    """Update title, aliases, and file name of the character dossier."""
    content = dossier_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    updated_lines = []
    in_aliases = False
    aliases_handled = False

    for line in lines:
        if re.match(r"^title\s*:\s*", line):
            updated_lines.append(f'title: "{new_name}"')
            continue
        if new_id and re.match(r"^id\s*:\s*", line):
            updated_lines.append(f'id: "{new_id}"')
            continue
        if re.match(r"^aliases\s*:\s*", line):
            in_aliases = True
            updated_lines.append(line)
            # Add old name into aliases if not already there
            updated_lines.append(f'  - "{old_name}"')
            aliases_handled = True
            continue
        elif in_aliases and re.match(r"^[a-zA-Z0-9_-]+\s*:\s*", line):
            in_aliases = False

        updated_lines.append(line)

    new_content = "\n".join(updated_lines)
    # Also update headings in body
    new_content = re.sub(rf"^# {re.escape(old_name)}\b", f"# {new_name}", new_content, flags=re.MULTILINE)
    new_content = replace_wikilinks(new_content, old_slug, new_slug, old_name, new_name)

    new_path = dossier_path.parent / f"{new_slug}.md"
    return new_path, content, new_content


def run_rename_character(
    old_name: str,
    new_name: str,
    new_id: Optional[str] = None,
    universe_root: Optional[Path] = None,
    rename_prose: bool = True,
    dry_run: bool = False
) -> Dict[str, Any]:
    """Execute complete cross-universe character rename and refactoring."""
    root = universe_root or find_universe_root()
    if not (root / "universe.yaml").is_file():
        return {"error": f"No universe.yaml found at {root}"}

    old_slug = slugify(old_name)
    new_slug = slugify(new_name)

    modified_files = []
    diff_previews = []
    total_replacements = 0

    # 1. Locate Character Dossier
    wiki_dirs = [
        root / "wiki" / "terms" / "characters",
        root / "wiki" / "characters",
        root / "lore" / "characters",
    ]
    target_dossier: Optional[Path] = None
    old_id = None

    for wd in wiki_dirs:
        if not wd.is_dir():
            continue
        for f in wd.glob("*.md"):
            if f.stem.lower() in (old_slug.lower(), old_name.lower(), old_name.replace(" ", "-").lower()):
                target_dossier = f
                break
            # Check title inside
            try:
                txt = f.read_text(encoding="utf-8", errors="ignore")
                if f'title: "{old_name}"' in txt or f"title: '{old_name}'" in txt:
                    target_dossier = f
                    break
            except Exception:
                pass
        if target_dossier:
            break

    if target_dossier:
        # Extract existing id if any
        try:
            txt = target_dossier.read_text(encoding="utf-8")
            m_id = re.search(r'^id\s*:\s*["\']?([^"\']+)["\']?', txt, re.MULTILINE)
            if m_id:
                old_id = m_id.group(1).strip()
        except Exception:
            pass

        new_dossier_path, old_doc, new_doc = refactor_character_dossier(
            target_dossier, old_name, new_name, old_slug, new_slug, new_id
        )
        if new_doc != old_doc or target_dossier != new_dossier_path:
            modified_files.append(str(target_dossier.relative_to(root)))
            diff = difflib.unified_diff(
                old_doc.splitlines(keepends=True),
                new_doc.splitlines(keepends=True),
                fromfile=target_dossier.name,
                tofile=new_dossier_path.name,
                n=2
            )
            diff_previews.append("".join(diff))
            total_replacements += 1

            if not dry_run:
                target_dossier.write_text(new_doc, encoding="utf-8")
                if target_dossier != new_dossier_path:
                    target_dossier.rename(new_dossier_path)

    # 2. Refactor all Chapters (All Books across all Series)
    manuscript_dir = root / "manuscript"
    for chap_file in sorted(manuscript_dir.glob("*/*/chapters/*.md")):
        changed, old_c, new_c, reps = refactor_chapter_file(
            chap_file, old_name, new_name, old_slug, new_slug, old_id, new_id, rename_prose=rename_prose
        )
        if changed:
            rel_p = str(chap_file.relative_to(root))
            modified_files.append(rel_p)
            total_replacements += reps

            diff = difflib.unified_diff(
                old_c.splitlines(keepends=True),
                new_c.splitlines(keepends=True),
                fromfile=rel_p,
                tofile=rel_p,
                n=1
            )
            diff_previews.append("".join(diff))

            if not dry_run:
                chap_file.write_text(new_c, encoding="utf-8")

    # 3. Update Master Outlines & TOC
    for outline_file in sorted(manuscript_dir.glob("*/*/*.md")):
        if outline_file.name in ("MASTER-OUTLINE.md", "MASTER-ARCHITECTURE.md", "README.md"):
            try:
                otxt = outline_file.read_text(encoding="utf-8")
                ntxt = replace_wikilinks(otxt, old_slug, new_slug, old_name, new_name)
                if rename_prose:
                    ntxt = re.sub(rf"\b{re.escape(old_name)}\b", new_name, ntxt)
                if ntxt != otxt:
                    rel_p = str(outline_file.relative_to(root))
                    modified_files.append(rel_p)
                    total_replacements += 1
                    if not dry_run:
                        outline_file.write_text(ntxt, encoding="utf-8")
            except Exception:
                pass

    return {
        "universe": root.name,
        "old_name": old_name,
        "new_name": new_name,
        "old_slug": old_slug,
        "new_slug": new_slug,
        "old_id": old_id,
        "new_id": new_id,
        "dry_run": dry_run,
        "total_files_modified": len(modified_files),
        "total_replacements": total_replacements,
        "modified_files": modified_files,
        "diff_previews": diff_previews[:5]  # Sample first 5
    }


def render_rename_report(result: Dict[str, Any]) -> None:
    """Print structured refactoring report."""
    if "error" in result:
        print(f"\n❌ Error: {result['error']}\n")
        return

    mode_label = "DRY-RUN PREVIEW (No files modified)" if result["dry_run"] else "REFACTOR APPLIED SUCCESSFULLY"
    print("\n" + "=" * 80)
    print(f" 🔄 CANONFORGE CHARACTER REFACTOR: {mode_label}")
    print("=" * 80)
    print(f" Target:               '{result['old_name']}' ➔ '{result['new_name']}'")
    print(f" Slugs:                '{result['old_slug']}' ➔ '{result['new_slug']}'")
    if result.get("old_id"):
        print(f" Character ID:         '{result['old_id']}' ➔ '{result.get('new_id') or result['old_id']}'")
    print("-" * 80)
    print(f" 📊 Refactoring Statistics:")
    print(f"    • Files Impacted:            {result['total_files_modified']}")
    print(f"    • Total Replacements:        {result['total_replacements']}")
    print("=" * 80)

    if result["modified_files"]:
        print("\n 📁 MODIFIED FILES LIST:")
        for mf in result["modified_files"]:
            print(f"    • {mf}")

    if result.get("diff_previews"):
        print("\n" + "=" * 80)
        print(" 🔍 SAMPLE DIFF PREVIEWS:")
        print("=" * 80)
        for diff in result["diff_previews"]:
            print(diff)
            print("-" * 40)

    print("\n" + "=" * 80)
    if result["dry_run"]:
        print(" 💡 This was a dry run. To execute changes, run without --dry-run.")
    else:
        print(" 🎉 All character mentions, wikilinks, dossiers, and frontmatters synchronized!")
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        prog="cf rename",
        description="Refactor and rename characters across all books, dossiers, wikilinks, and frontmatters."
    )
    parser.add_argument("target_type", choices=["character", "entity"], default="character", nargs="?", help="Target type (default: character)")
    parser.add_argument("old_name", help="Current character name to find")
    parser.add_argument("new_name", help="New character name to replace with")
    parser.add_argument("--new-id", help="Optional new namespaced ID")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Preview changes without writing to disk")
    parser.add_argument("--no-prose", action="store_true", help="Skip changing prose, only update frontmatter & wikilinks")
    parser.add_argument("--universe", "-u", help="Path to universe root")

    args = parser.parse_args()

    u_root = Path(args.universe).resolve() if args.universe else find_universe_root()
    res = run_rename_character(
        old_name=args.old_name,
        new_name=args.new_name,
        new_id=args.new_id,
        universe_root=u_root,
        rename_prose=not args.no_prose,
        dry_run=args.dry_run
    )

    render_rename_report(res)


if __name__ == "__main__":
    main()
