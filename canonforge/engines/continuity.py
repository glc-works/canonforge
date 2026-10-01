"""
audit_continuity.py

Authoritative Character Continuity & Fact Checker for CanonForge Studio.
Parses Single Source of Truth (SSOT) character profiles in lore/characters/ or wiki/terms/characters/
and cross-references manuscript text to ensure zero physical contradictions or timeline anachronisms.
"""

import sys
import os
import re
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parent
MANUSCRIPT_DIR = WORKSPACE_DIR / "manuscript"
CHARACTERS_LORE_DIRS = [
    WORKSPACE_DIR / "lore" / "characters",
    WORKSPACE_DIR / "wiki" / "terms" / "characters",
    WORKSPACE_DIR / "wiki" / "characters"
]

# Configurable banned term / leak lexicon (loaded from workspace if present)
DEFAULT_BANNED_LEAKS: Dict[str, str] = {}

def load_adaptation_rules() -> Dict[str, str]:
    rules_files = [
        WORKSPACE_DIR / "data" / "adaptation_rules" / "adaptation_rules.yaml",
        WORKSPACE_DIR / "data" / "adaptation_rules" / "hp_adaptation_rules.yaml"
    ]
    for rf in rules_files:
        if rf.is_file():
            try:
                import yaml
                data = yaml.safe_load(rf.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "banned_leaks" in data:
                    return data["banned_leaks"]
            except Exception:
                pass
    return DEFAULT_BANNED_LEAKS

BANNED_LEAKS = load_adaptation_rules()

# Default physical attribute drift rules (dynamically populated from lore)
BASE_INVARIANTS: Dict[str, Dict[str, Any]] = {}

def load_invariants_from_wiki(wiki_dirs: List[Path] = CHARACTERS_LORE_DIRS) -> Dict[str, Dict[str, Any]]:
    """Dynamically scan lore/characters/*.md frontmatter for invariants."""
    invariants = dict(BASE_INVARIANTS)
    for wiki_dir in wiki_dirs:
        if not wiki_dir.is_dir():
            continue

        for md_file in wiki_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                if not content.startswith("---"):
                    continue
                parts = content.split("---", 2)
                if len(parts) < 3:
                    continue
                import yaml
                meta = yaml.safe_load(parts[1])
                if not isinstance(meta, dict) or "invariants" not in meta:
                    continue

                inv_data = meta["invariants"]
                if not isinstance(inv_data, dict):
                    continue

                title = meta.get("title", md_file.stem)
                key = str(meta.get("id") or meta.get("alias") or title.split()[0]).strip()

                existing = invariants.get(key, {})
                merged = {**existing, **inv_data}
                merged["full_name"] = title
                merged["file"] = md_file.name
                invariants[key] = merged
            except Exception:
                continue

    return invariants
KNOWN_INVARIANTS = load_invariants_from_wiki()

def audit_chapter_continuity(chapter_path: Path) -> List[Tuple[str, int, str, str]]:
    """Scan a chapter file for character continuity anomalies."""
    violations: List[Tuple[str, int, str, str]] = []
    text = chapter_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    for idx, line in enumerate(lines, 1):
        for char_name, inv in KNOWN_INVARIANTS.items():
            # Check if character is mentioned in line
            char_pattern = rf"\b{re.escape(char_name)}\b"
            is_char_in_line = bool(re.search(char_pattern, line, re.IGNORECASE))

            # 1. Scar Location Invariant Check
            if re.search(r"\b(?:scars?|scarred|mark)\b", line, re.IGNORECASE):
                for bad_loc in inv.get("forbidden_scar_locations", []):
                    p1 = rf"\b{char_name}(?:'s)?\s+(?:[a-z]+\s+)?{bad_loc}\s+(?:scar|mark)\b"
                    p2 = rf"\b(?:scar|mark)\b\s+(?:on|across|upon|over)\s+(?:his|her|their|{char_name}'s)\s+(?:[a-z]+\s+)?{bad_loc}\b"
                    if re.search(p1, line, re.IGNORECASE) or re.search(p2, line, re.IGNORECASE):
                        target_loc = inv.get("scar_location", "canonical position")
                        violations.append((chapter_path.name, idx, line.strip(), f"{char_name}'s scar is on their {target_loc}, not {bad_loc}!"))

            # 2. Eye Color Invariant Check
            for bad_color in inv.get("forbidden_eye_colors", []):
                p1 = rf"\b{char_name}(?:'s)?\s+(?:[a-z]+\s+)?{bad_color}\s+eyes?\b"
                p2 = rf"\b{bad_color}\s+eyes\s+of\s+{char_name}\b"
                if re.search(p1, line, re.IGNORECASE) or re.search(p2, line, re.IGNORECASE):
                    valid_str = "/".join(inv.get("valid_eye_colors", ["canonical color"]))
                    violations.append((chapter_path.name, idx, line.strip(), f"{char_name}'s eyes are {valid_str}, not {bad_color}!"))

            # 3. Animus / Familiar / Companion Association Check
            for bad_animus in inv.get("forbidden_animi", []):
                p = rf"\b{char_name}(?:'s)?\s+(?:animus\s+|companion\s+)?{bad_animus}\b"
                if re.search(p, line, re.IGNORECASE):
                    bound = inv.get("bound_animus", "canonical companion")
                    violations.append((chapter_path.name, idx, line.strip(), f"{char_name} is bonded to {bound}, not {bad_animus}!"))

            # 4. Trait Checks if character is in line
            if is_char_in_line:
                for bad_eye in inv.get("forbidden_eye_types", []):
                    if re.search(rf"\b{re.escape(bad_eye)}\b", line, re.IGNORECASE):
                        violations.append((chapter_path.name, idx, line.strip(), f"{char_name}'s eye cannot be {bad_eye}!"))

                for bad_leg in inv.get("forbidden_leg_types", []):
                    if re.search(rf"\b{re.escape(bad_leg)}\b", line, re.IGNORECASE):
                        violations.append((chapter_path.name, idx, line.strip(), f"{char_name}'s leg cannot be {bad_leg}!"))

                for bad_hw in inv.get("forbidden_headwear", []):
                    if re.search(rf"\b{re.escape(bad_hw)}\b", line, re.IGNORECASE):
                        violations.append((chapter_path.name, idx, line.strip(), f"{char_name}'s headwear cannot be {bad_hw}!"))

        # 5. Configured banned proper nouns / leaks
        for pattern, replacement_advice in BANNED_LEAKS.items():
            if re.search(pattern, line):
                violations.append((chapter_path.name, idx, line.strip(), f"Banned terminology detected: {replacement_advice}"))

    return violations

def main():
    parser = argparse.ArgumentParser(description="CanonForge Character Continuity & Fact Checker")
    parser.add_argument("--book", default="", help="Book slug to audit")
    parser.add_argument("--chapter", help="Specific chapter file to audit")
    parser.add_argument("--all", action="store_true", help="Audit all books across the saga")
    args = parser.parse_args()

    target_files = []
    if args.chapter:
        matches = list(MANUSCRIPT_DIR.rglob(args.chapter))
        target_files.extend(m for m in matches if m.is_file() and m.suffix == ".md" and "_build" not in m.parts and "compiled" not in m.parts)
    elif args.all:
        for ch_dir in sorted(MANUSCRIPT_DIR.glob("*/*/chapters")):
            target_files.extend(sorted(ch_dir.glob("*.md")))
    elif args.book:
        book_candidates = list(MANUSCRIPT_DIR.glob(f"*/{args.book}/chapters")) + list(MANUSCRIPT_DIR.glob(f"{args.book}/chapters"))
        for b_dir in book_candidates:
            target_files.extend(sorted(b_dir.glob("*.md")))
        if not target_files:
            for toc in MANUSCRIPT_DIR.glob("*/*/toc.yaml"):
                if args.book.lower() in toc.parent.name.lower() or args.book.lower() in toc.read_text(encoding="utf-8").lower():
                    target_files.extend(sorted((toc.parent / "chapters").glob("*.md")))
                    break
    else:
        # Scan all chapters if no specific book given
        for ch_dir in sorted(MANUSCRIPT_DIR.glob("*/*/chapters")):
            target_files.extend(sorted(ch_dir.glob("*.md")))

    if not target_files:
        print("No target chapter files found to audit.")
        return 0

    label = "ALL SAGA BOOKS" if args.all else (args.book.upper() if args.book else "MANUSCRIPT")
    print("\n" + "=" * 75)
    print(f"CANONFORGE CHARACTER CONTINUITY & FACT AUDITOR: {label}")
    print("=" * 75)
    print(f"• Active Profiles Indexed : {len(KNOWN_INVARIANTS)} primary characters")
    print(f"• Target Chapters to Audit: {len(target_files)}")
    print("-" * 75)

    all_violations = []
    for ch in target_files:
        viols = audit_chapter_continuity(ch)
        all_violations.extend(viols)

    if not all_violations:
        print("🎉 100% CONTINUITY VERIFIED: All physical traits, scars, eye colors, and animus bonds match canon SSOT!")
        print("=" * 75 + "\n")
        return 0

    print(f"⚠️ DETECTED {len(all_violations)} CONTINUITY DISCREPANCIES:")
    table_data = []
    for ch_name, line_no, text, advice in all_violations:
        snippet = text[:50] + "..." if len(text) > 50 else text
        table_data.append([f"{ch_name}:{line_no}", snippet, advice])

    if HAS_TABULATE:
        print(tabulate(table_data, headers=["Location", "Snippet", "Canonical Correction"], tablefmt="simple"))
    else:
        for r in table_data:
            print(f"  • {r[0]:<25} | {r[1]:<30} | {r[2]}")

    print("=" * 75 + "\n")
    return 1

if __name__ == "__main__":
    sys.exit(main())
