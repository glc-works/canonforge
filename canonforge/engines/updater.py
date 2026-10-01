"""
canonforge/engines/updater.py

Authoritative CLI Entity Updater for CanonForge Studio.
Updates YAML frontmatter in wiki dossiers safely and losslessly with before/after diffs.
100% Free of Universe-Specific Hardcoding.
"""

import sys
import os
import re
import difflib
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

def find_universe_root() -> Path:
    cwd = Path.cwd().resolve()
    for parent in [cwd, *cwd.parents]:
        if (parent / "universe.yaml").exists():
            return parent
    return cwd

def get_wiki_dir(root: Path) -> Path:
    wiki = root / "wiki"
    return wiki if wiki.exists() else root

def get_all_entity_files(wiki_dir: Path) -> Dict[str, Path]:
    candidates = {}
    if not wiki_dir.exists():
        return candidates
    for f in wiki_dir.rglob("*.md"):
        if f.name.lower() in ("readme.md", "index.md", "summary.md"):
            continue
        stem = f.stem
        stem_clean = stem.replace("-", " ").lower()
        candidates[stem_clean] = f
        candidates[stem.lower()] = f
    return candidates

def find_entity_file(target: str, wiki_dir: Path) -> Tuple[Optional[Path], Optional[str], List[str]]:
    q_norm = re.sub(r"[^a-zA-Z0-9]", "", target).lower()
    q_lower = target.lower()

    candidates = get_all_entity_files(wiki_dir)
    for name, f in candidates.items():
        name_norm = re.sub(r"[^a-zA-Z0-9]", "", name).lower()
        if q_norm == name_norm or q_lower == name:
            return f, None, []

    close = difflib.get_close_matches(q_lower, list(candidates.keys()), n=4, cutoff=0.5)
    if close:
        return candidates[close[0]], close[0], close

    broader = [k for k in candidates.keys() if q_lower in k or any(p in k for p in q_lower.split())]
    return None, None, broader[:5]

def format_val_str(v: Any) -> str:
    if isinstance(v, (int, float, bool)):
        return str(v)
    v_str = str(v)
    if any(c in v_str for c in [":", "#", "{", "}", "[", "]", ",", "&", "*", "?", "|", "-", "<", ">", "=", "!"]):
        return f'"{v_str}"'
    return v_str

def process_tags_in_lines(lines: List[str], add_tags: List[str], remove_tags: List[str]) -> Tuple[List[str], List[Tuple[str, str, str]]]:
    diffs = []
    updated = []
    in_tags = False
    existing_tags = []

    for line in lines:
        if re.match(r"^(tags|labels)\s*:\s*$", line):
            in_tags = True
            updated.append(line)
            continue
        if in_tags:
            m = re.match(r"^\s*-\s*(.*)$", line)
            if m:
                existing_tags.append(m.group(1).strip().strip('"').strip("'"))
                continue
            else:
                in_tags = False
        updated.append(line)

    final_tags = [t for t in existing_tags if t not in remove_tags]
    for at in add_tags:
        if at not in final_tags:
            final_tags.append(at)

    if existing_tags != final_tags:
        diffs.append(("tags", ", ".join(existing_tags), ", ".join(final_tags)))

    result = []
    placed_tags = False
    for line in updated:
        result.append(line)
        if re.match(r"^(tags|labels)\s*:\s*$", line):
            for t in final_tags:
                result.append(f"  - {t}")
            placed_tags = True

    if not placed_tags and (add_tags or remove_tags):
        result.append("tags:")
        for t in final_tags:
            result.append(f"  - {t}")

    return result, diffs

def update_frontmatter_fields(
    fm_text: str,
    updates: Dict[str, Any],
    add_tags: List[str] = None,
    remove_tags: List[str] = None
) -> Tuple[str, List[Tuple[str, str, str]]]:
    diff_log = []
    lines = fm_text.splitlines()
    updated_lines = []
    keys_handled = set()

    for line in lines:
        matched_key = None
        for k, v in updates.items():
            pattern = rf"^({re.escape(k)}\s*:\s*)(.*)$"
            m = re.match(pattern, line)
            if m:
                matched_key = k
                old_val = m.group(2).strip().strip('"').strip("'")
                new_val_str = format_val_str(v)
                diff_log.append((k, old_val, str(v)))
                updated_lines.append(f"{k}: {new_val_str}")
                keys_handled.add(k)
                break
        if not matched_key:
            updated_lines.append(line)

    for k, v in updates.items():
        if k not in keys_handled:
            new_val_str = format_val_str(v)
            diff_log.append((k, "(None)", str(v)))
            updated_lines.append(f"{k}: {new_val_str}")

    if add_tags or remove_tags:
        updated_lines, tag_diffs = process_tags_in_lines(updated_lines, add_tags or [], remove_tags or [])
        diff_log.extend(tag_diffs)

    return "\n".join(updated_lines), diff_log

def update_entity(
    target: str,
    updates: Dict[str, Any],
    add_tags: Optional[List[str]] = None,
    remove_tags: Optional[List[str]] = None,
    dry_run: bool = False,
    auto_confirm: bool = False,
    no_sync: bool = False,
    root_dir: Optional[Path] = None,
) -> bool:
    root = root_dir or find_universe_root()
    wiki_dir = get_wiki_dir(root)

    file_path, fuzzy_name, suggestions = find_entity_file(target, wiki_dir)
    if not file_path:
        print(f"\n❌ Could not find entity dossier matching '{target}'.")
        if suggestions:
            print("💡 Closest matching entities:")
            for s in suggestions:
                print(f"   - {s}")
        print()
        return False

    if fuzzy_name and fuzzy_name != target.lower():
        print(f"ℹ️  Target '{target}' resolved via fuzzy match to '{fuzzy_name}'.")

    content = file_path.read_text(encoding="utf-8")
    m = re.match(r"^(---[\r\n]+)(.*?)([\r\n]+---[\r\n]+)(.*)$", content, re.DOTALL)
    if not m:
        fm_prefix, fm_text, fm_suffix, prose = "---\n", "", "---\n\n", content
    else:
        fm_prefix, fm_text, fm_suffix, prose = m.group(1), m.group(2), m.group(3), m.group(4)

    updated_fm, diff_log = update_frontmatter_fields(
        fm_text, updates, add_tags or [], remove_tags or []
    )

    if not diff_log:
        print(f"\n✨ Entity '{file_path.stem}' already has the requested attributes. No changes needed.\n")
        return True

    print(f"\n📝 Proposed updates for '{file_path.stem}':")
    headers = ["Attribute", "Current Value", "New Value"]
    diff_rows = [[k, old_v, new_v] for k, old_v, new_v in diff_log]
    if HAS_TABULATE:
        print(tabulate(diff_rows, headers=headers, tablefmt="rounded_grid"))
    else:
        for r in diff_rows:
            print(f"   • {r[0]}: {r[1]} -> {r[2]}")
    print()

    if dry_run:
        print("🔍 Dry-run complete. No files were modified.\n")
        return True

    if not auto_confirm:
        try:
            choice = input("Confirm changes? [Y/n] ").strip().lower()
            if choice in ("n", "no"):
                print("❌ Aborted by user.\n")
                return False
        except EOFError:
            pass

    new_content = f"{fm_prefix}{updated_fm}{fm_suffix}{prose}"
    file_path.write_text(new_content, encoding="utf-8")
    print(f"✅ Successfully updated: {file_path.relative_to(root)}")

    if not no_sync:
        try:
            from canonforge.engines import sync_db
            sync_db.sync_world_db(root)
            print("🔄 Auto-synced changes to local database.")
        except Exception:
            pass

    print()
    return True

def main():
    parser = argparse.ArgumentParser(description="CanonForge Entity Frontmatter & Lore Updater")
    parser.add_argument("target", nargs="?", help="Entity name or slug (e.g. 'Corin Solen', 'Flame-Wyrm')")
    parser.add_argument("--role", help="Update role or title")
    parser.add_argument("--status", help="Update entity status (Active, Deceased, Missing, Ascended)")
    parser.add_argument("--phase", help="Update current phase")
    parser.add_argument("--house", help="Update house or lineage")
    parser.add_argument("--faction", help="Update faction affiliation")
    parser.add_argument("--set", dest="custom_sets", action="append", help="Generic key=value update (e.g. --set danger_level=4)")
    parser.add_argument("--add-tag", action="append", help="Add a tag or label")
    parser.add_argument("--remove-tag", action="append", help="Remove a tag or label")
    parser.add_argument("--yes", "-y", action="store_true", help="Auto-confirm without prompt")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--no-sync", action="store_true", help="Do not trigger auto-sync to database")
    args = parser.parse_args()

    if not args.target:
        print("\nUsage: cf update <target> [options]")
        print("Example: cf update \"Corin Solen\" --role \"Master Auror\" --status \"Active\"\n")
        return

    updates = {}
    if args.role:
        updates["role"] = args.role
    if args.status:
        updates["status"] = args.status
    if args.phase:
        updates["phase"] = args.phase
    if args.house:
        updates["house"] = args.house
    if args.faction:
        updates["faction"] = args.faction

    if args.custom_sets:
        for s in args.custom_sets:
            if "=" in s:
                k, v = s.split("=", 1)
                updates[k.strip()] = v.strip()

    update_entity(
        target=args.target,
        updates=updates,
        add_tags=args.add_tag,
        remove_tags=args.remove_tag,
        dry_run=args.dry_run,
        auto_confirm=args.yes,
        no_sync=args.no_sync,
    )

if __name__ == "__main__":
    main()
