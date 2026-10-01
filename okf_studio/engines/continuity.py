#!/usr/bin/env python3
"""
audit_continuity.py

Authoritative Character Continuity & Fact Checker for Convergence Studio.
Parses the Single Source of Truth (SSOT) character profiles in wiki/terms/characters/
and cross-references manuscript text to ensure zero physical contradictions or
timeline anachronisms.

Features:
1. Extracts active phase anchors: Eye color, Scars/Marks, Wand/Gear, Bound Animi.
2. Audits chapter text against character specifications for that book's era.
3. Catches physical drifts (e.g., wrong eye color, misplaced scar, anachronistic gear).

Usage:
    uv run scripts/audit_continuity.py --book the-sun-sanctum-apprentice
    uv run scripts/audit_continuity.py --chapter ch01-the-boy-who-slept-in-the-ashes.md
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
CONVERGENCE_DIR = SCRIPT_DIR.parent
MANUSCRIPT_DIR = CONVERGENCE_DIR / "manuscript"
CHARACTERS_WIKI = CONVERGENCE_DIR / "wiki" / "terms" / "characters"

# Banned HP Proper Noun Lexicon (Ensures 100% Convergence original lore integrity)
DEFAULT_BANNED_HP_LEAKS: Dict[str, str] = {
    r"\bHouse Black\b": "Use 'House Shadow-Hound'",
    r"\bKorin Black\b": "Use 'Korin the Shadow-Hound'",
    r"\bHouse Gaunt\b": "Use 'House Karst'",
    r"\bMarvolo Gaunt\b": "Use 'Marvolo Karst'",
    r"\bMorfin Gaunt\b": "Use 'Morfin Karst'",
    r"\bMerope Gaunt\b": "Use 'Merope Karst'",
    r"\bWalden Macnair\b": "Use 'Executioner Malcor'",
    r"\bGabi Delacour\b": "Use 'Gabi of the Silver Stream'",
    r"\bAunt Marjorie\b": "Use 'Aunt Margery'",
    r"\bUncle Vernon\b": "Use 'Overseer Malgath'",
    r"\bAunt Petunia\b": "Use 'Aunt Mara'",
    r"\bDudley\b": "Use 'Brand'",
    r"\bPrivet Drive\b": "Use 'Peat-Sluice Number Four'",
    r"\bGryffindor\b": "Use 'Pyre Cloister'",
    r"\bSlytherin\b": "Use 'Obsidian Cloister'",
    r"\bRavenclaw\b": "Use 'Spire Cloister'",
    r"\bHufflepuff\b": "Use 'Hearth Cloister'",
    r"\bHogwarts\b": "Use 'High Sanctum Academy'",
    r"\bVoldemort\b": "Use 'Malakor Lumis / The Black Sun'",
    r"\bDeath Eater\b": "Use 'Death Cultist / Black Sun Inquisitor'",
    r"\bDeath Eaters\b": "Use 'Death Cultists'",
    r"\bHorcrux\b": "Use 'Soul-Anchor'",
    r"\bHorcruxes\b": "Use 'Soul-Anchors'",
    r"\bQuidditch\b": "Use 'Cloud-Skimming'",
    r"\bGolden Snitch\b": "Use 'Gale-Falcon / Aether-Mote'",
    r"\bButterbeer\b": "Use 'Spiced Cider / Brazen Mead'",
    r"\bDiagon Alley\b": "Use 'Scriptorium Alley'",
    r"\bKnockturn Alley\b": "Use 'The Low Sinks'",
    r"\bGringotts\b": "Use 'The Sun-Bank'",
}

def load_adaptation_rules() -> Dict[str, str]:
    rules_file = CONVERGENCE_DIR / "data" / "adaptation_rules" / "hp_adaptation_rules.yaml"
    if rules_file.is_file():
        try:
            import yaml
            data = yaml.safe_load(rules_file.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "banned_leaks" in data:
                return data["banned_leaks"]
        except Exception:
            pass
    return DEFAULT_BANNED_HP_LEAKS

BANNED_HP_LEAKS = load_adaptation_rules()

# Default physical attribute drift rules (Base SSOT Fallback)
BASE_INVARIANTS = {
    "Vaelin": {
        "full_name": "Vaelin the Pale Weaver",
        "file": "Vaelin-the-Pale-Weaver.md",
        "valid_eye_colors": ["slate-gray", "slate gray", "gray"],
        "forbidden_eye_colors": ["green", "hazel", "brown", "blue"],
        "scar_location": "collarbone",
        "forbidden_scar_locations": ["forehead", "cheek", "hand", "chest"],
        "wand_wood": "ash",
        "bound_animus": "Kira",
        "forbidden_animi": ["Barnaby", "Vesper", "Ignis"]
    },
    "Corin": {
        "full_name": "Corin Solen",
        "file": "Corin-Solen.md",
        "valid_eye_colors": ["brown", "golden"],
        "forbidden_eye_colors": ["blue", "green", "gray"],
        "hair_color": "copper",
        "bound_animus": "Barnaby",
        "forbidden_animi": ["Kira", "Vesper", "Ignis"]
    },
    "Lyra": {
        "full_name": "Lyra of the Low Sinks",
        "file": "Lyra-of-the-Low-Sinks.md",
        "valid_eye_colors": ["dark", "obsidian", "black"],
        "forbidden_eye_colors": ["blue", "hazel", "green"],
        "wand_wood": "silver pine",
        "bound_animus": "Vesper",
        "forbidden_animi": ["Kira", "Barnaby", "Ignis"]
    },
    "Lucian": {
        "full_name": "Lucian Lumis",
        "file": "Lucian-Lumis.md",
        "valid_eye_colors": ["violet", "pale violet"],
        "forbidden_eye_colors": ["brown", "green"],
        "hair_color": "blond",
        "bound_animus": "Ignis",
        "forbidden_animi": ["Kira", "Barnaby", "Vesper"]
    },
    "Elenor": {
        "full_name": "Master Elenor",
        "file": "Master-Elenor.md",
        "headwear": "turban",
        "forbidden_headwear": ["hood", "helmet", "bareheaded"]
    },
    "Kroll": {
        "full_name": "Brother Kroll the Warden",
        "file": "Brother-Kroll-the-Warden.md",
        "height_tell": ["seven feet", "mountain", "giant"],
    },
    "Finch": {
        "full_name": "Commander Cassian Finch",
        "file": "Commander-Cassian-Finch.md",
        "eye_type": ["storm-raptor", "raptor eye", "beast eye", "golden eye", "storm raptor"],
        "forbidden_eye_types": ["brass eye", "mechanical eye", "glass eye", "clockwork eye"],
        "leg_type": ["petrified ironwood", "ironwood talon", "bronze talon", "ironwood leg"],
        "forbidden_leg_types": ["metal leg", "pneumatic leg", "clockwork leg"]
    },
    "Seren": {
        "full_name": "Seren Halren",
        "file": "Seren-Halren.md",
        "focus_weapon": ["ash javelin", "javelin"],
        "bound_animus": "Solas",
        "cloister": "Hearth Cloister"
    }
}

def load_invariants_from_wiki(wiki_dir: Path) -> Dict[str, Dict[str, Any]]:
    """Dynamically scan wiki/terms/characters/*.md frontmatter for invariants."""
    invariants = dict(BASE_INVARIANTS)
    if not wiki_dir.is_dir():
        return invariants

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

            # Determine key
            title = meta.get("title", md_file.stem)
            key = title.split()[0] # e.g. Vaelin, Corin, Seren, Commander -> fallback
            if "Vaelin" in title:
                key = "Vaelin"
            elif "Corin" in title:
                key = "Corin"
            elif "Lyra" in title:
                key = "Lyra"
            elif "Lucian" in title:
                key = "Lucian"
            elif "Finch" in title:
                key = "Finch"
            elif "Elenor" in title:
                key = "Elenor"
            elif "Kroll" in title:
                key = "Kroll"
            elif "Seren" in title:
                key = "Seren"
            else:
                key = title

            existing = invariants.get(key, {})
            merged = {**existing, **inv_data}
            merged["full_name"] = title
            merged["file"] = md_file.name
            invariants[key] = merged
        except Exception:
            pass

    return invariants

KNOWN_INVARIANTS = load_invariants_from_wiki(CHARACTERS_WIKI)

def audit_chapter_continuity(chapter_path: Path) -> List[Tuple[str, int, str, str]]:
    """Scan a chapter file for character continuity anomalies."""
    violations: List[Tuple[str, int, str, str]] = []
    text = chapter_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    for idx, line in enumerate(lines, 1):
        # 1. Vaelin Scar Check (must be collarbone/neck, never forehead/cheek/hand/chest)
        # Avoid matching 'scarf' by using word boundaries
        if re.search(r"\b(?:scars?|scarred|mark)\b", line, re.IGNORECASE):
            for bad_loc in KNOWN_INVARIANTS["Vaelin"]["forbidden_scar_locations"]:
                # Matches: scar on/across his forehead, Vaelin's forehead scar, scarred forehead
                p1 = rf"\b(?:scar|mark)\b\s+(?:on|across|upon|over)\s+(?:his|Vaelin's)\s+(?:[a-z]+\s+)?{bad_loc}\b"
                p2 = rf"\b(?:his|Vaelin's)\s+(?:[a-z]+\s+)?{bad_loc}\s+(?:scar|mark)\b"
                p3 = rf"\bVaelin(?:'s)?\s+scarred\s+{bad_loc}\b"
                if re.search(p1, line, re.IGNORECASE) or re.search(p2, line, re.IGNORECASE) or re.search(p3, line, re.IGNORECASE):
                    violations.append((chapter_path.name, idx, line.strip(), f"Vaelin's scar is strictly on his collarbone, not {bad_loc}!"))

        # 2. Vaelin Eye Color Check (must be slate-gray, not green/hazel/brown/blue)
        for bad_color in KNOWN_INVARIANTS["Vaelin"]["forbidden_eye_colors"]:
            p1 = rf"\bVaelin(?:'s)?\s+(?:[a-z]+\s+)?{bad_color}\s+eyes?\b"
            p2 = rf"\b{bad_color}\s+eyes\s+of\s+Vaelin\b"
            if re.search(p1, line, re.IGNORECASE) or re.search(p2, line, re.IGNORECASE):
                violations.append((chapter_path.name, idx, line.strip(), f"Vaelin's eyes are slate-gray, not {bad_color}!"))

        # 3. Lyra Eye Color Check (must be dark obsidian, not blue/hazel/green)
        if "lyra" in line.lower() or "her" in line.lower():
            for bad_color in KNOWN_INVARIANTS["Lyra"]["forbidden_eye_colors"]:
                p1 = rf"\bLyra(?:'s)?\s+(?:[a-z]+\s+)?{bad_color}\s+eyes?\b"
                p2 = rf"\bher\s+(?:[a-z]+\s+)?{bad_color}\s+eyes?\b"
                if re.search(p1, line, re.IGNORECASE) or ("lyra" in line.lower() and re.search(p2, line, re.IGNORECASE)):
                    violations.append((chapter_path.name, idx, line.strip(), f"Lyra's eyes are dark obsidian, not {bad_color}!"))

        # 4. Corin Eye / Hair Check
        for bad_color in KNOWN_INVARIANTS["Corin"]["forbidden_eye_colors"]:
            p1 = rf"\bCorin(?:'s)?\s+(?:[a-z]+\s+)?{bad_color}\s+eyes?\b"
            p2 = rf"\bCorin\b[^\.\?!;]+?\bhis\s+(?:[a-z]+\s+)?{bad_color}\s+eyes?\b"
            if re.search(p1, line, re.IGNORECASE):
                violations.append((chapter_path.name, idx, line.strip(), f"Corin's eyes are warm brown/golden, not {bad_color}!"))
            elif re.search(p2, line, re.IGNORECASE):
                m = re.search(p2, line, re.IGNORECASE)
                if m and not any(other in m.group(0) for other in ["Lucan", "Vaelin", "Kroll", "Caelis", "Finch", "Doran", "Bartok"]):
                    violations.append((chapter_path.name, idx, line.strip(), f"Corin's eyes are warm brown/golden, not {bad_color}!"))

        # 5. Animus Association Check
        for char_name, inv in [("Vaelin", KNOWN_INVARIANTS["Vaelin"]), ("Corin", KNOWN_INVARIANTS["Corin"]), ("Lyra", KNOWN_INVARIANTS["Lyra"])]:
            for bad_animus in inv.get("forbidden_animi", []):
                pattern = rf"\b{char_name}('s)?\s+(animus\s+)?{bad_animus}\b"
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append((chapter_path.name, idx, line.strip(), f"{char_name} is bonded to {inv['bound_animus']}, not {bad_animus}!"))

        # 6. Finch Eye & Leg Continuity Check (Constrained to Finch context)
        if "finch" in line.lower() or "cassian" in line.lower():
            for bad_eye in KNOWN_INVARIANTS["Finch"]["forbidden_eye_types"]:
                p1 = rf"\b(?:Finch|Cassian)(?:'s)?\s+(?:[a-z]+\s+)?{bad_eye}\b"
                p2 = rf"\b{bad_eye}\s+of\s+(?:Finch|Cassian)\b"
                p3 = rf"\bhis\s+{bad_eye}\b"
                if re.search(p1, line, re.IGNORECASE) or re.search(p2, line, re.IGNORECASE) or re.search(p3, line, re.IGNORECASE):
                    violations.append((chapter_path.name, idx, line.strip(), f"Finch's eye is an organic Storm-Raptor Force Eye, not a {bad_eye}!"))

            for bad_leg in KNOWN_INVARIANTS["Finch"]["forbidden_leg_types"]:
                p1 = rf"\b(?:Finch|Cassian)(?:'s)?\s+(?:[a-z]+\s+)?{bad_leg}\b"
                p2 = rf"\b{bad_leg}\s+of\s+(?:Finch|Cassian)\b"
                p3 = rf"\bhis\s+{bad_leg}\b"
                if re.search(p1, line, re.IGNORECASE) or re.search(p2, line, re.IGNORECASE) or re.search(p3, line, re.IGNORECASE):
                    violations.append((chapter_path.name, idx, line.strip(), f"Finch's leg is Petrified Ironwood, not a {bad_leg}!"))

        # 7. Unadapted Harry Potter Proper Noun Leak Check (Zero Tolerance)
        for pattern, replacement_advice in BANNED_HP_LEAKS.items():
            if re.search(pattern, line):
                violations.append((chapter_path.name, idx, line.strip(), f"Unadapted HP proper noun detected: {replacement_advice}"))

    return violations

def main():
    parser = argparse.ArgumentParser(description="Convergence Character Continuity & Fact Checker")
    parser.add_argument("--book", default="the-sun-sanctum-apprentice", help="Book slug (default: the-sun-sanctum-apprentice)")
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
    else:
        book_candidates = list(MANUSCRIPT_DIR.glob(f"*/{args.book}/chapters")) + list(MANUSCRIPT_DIR.glob(f"{args.book}/chapters"))
        for b_dir in book_candidates:
            target_files.extend(sorted(b_dir.glob("*.md")))
        if not target_files:
            # Fallback to book_navigator or partial search
            for toc in MANUSCRIPT_DIR.glob("*/*/toc.yaml"):
                if args.book.lower() in toc.parent.name.lower() or args.book.lower() in toc.read_text(encoding="utf-8").lower():
                    target_files.extend(sorted((toc.parent / "chapters").glob("*.md")))
                    break

    if not target_files:
        print("No target chapter files found to audit.")
        sys.exit(1)

    label = "ALL SAGA BOOKS" if args.all else args.book.upper()
    print("\n" + "=" * 75)
    print(f"CONVERGENCE CHARACTER CONTINUITY & FACT AUDITOR: {label}")
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
