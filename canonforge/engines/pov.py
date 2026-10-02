#!/usr/bin/env python3
"""
CANONFORGE STUDIO: SECTION-LEVEL POV & HEAD-HOPPING INTEGRITY AUDITOR
------------------------------------------------------------------------------
Protects Deep Third-Person Limited POV across chapters and sections.
1. Parses primary POV from frontmatter and section breaks: <!-- pov: Character -->
2. Detects 'Head-Hopping' (internal epistemic leakage of non-POV characters).
3. Enforces that non-POV characters are perceived purely via external senses
   (sight, sound, voice, posture) rather than telepathic emotion declarations.
------------------------------------------------------------------------------
"""

import sys
import re
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

from canonforge.core.manifest import find_universe_root

UNIVERSE_DIR = find_universe_root()
MANUSCRIPT_DIR = UNIVERSE_DIR / "manuscript"

# Verbs declaring internal mental state (Forbidden for non-POV characters in 3rd-person limited)
INTERNAL_STATE_VERBS = [
    "felt", "thought", "knew", "believed", "realized", "remembered",
    "wished", "feared", "wondered", "decided", "hated", "loved",
    "regretted", "yearned", "dreamed", "concluded"
]

INTERNAL_NOUN_PATTERNS = [
    r"\bin (?:his|her|their) (?:heart|mind|thoughts|soul|batin)\b",
    r"\bto (?:himself|herself|themselves)\b",
]

def split_sections(text: str, default_pov: str) -> List[Dict[str, Any]]:
    """Split chapter text into distinct POV sections based on HTML comments or scene breaks."""
    lines = text.splitlines()
    sections = []
    
    current_pov = default_pov
    current_lines = []
    start_line_no = 1
    sec_idx = 1

    for line_no, line in enumerate(lines, start=1):
        # Match <!-- pov: Name --> or *** <!-- pov: Name -->
        pov_match = re.search(r"<!--\s*pov:\s*([a-zA-Z\s_-]+?)\s*-->", line, re.IGNORECASE)
        if pov_match:
            new_pov = pov_match.group(1).strip()
            if current_lines:
                sections.append({
                    "section_index": sec_idx,
                    "pov": current_pov,
                    "start_line": start_line_no,
                    "end_line": line_no - 1,
                    "text": "\n".join(l[1] for l in current_lines),
                    "lines": list(current_lines)
                })
                sec_idx += 1
                current_lines = []
            current_pov = new_pov
            start_line_no = line_no
            continue
        
        current_lines.append((line_no, line))

    if current_lines:
        sections.append({
            "section_index": sec_idx,
            "pov": current_pov,
            "start_line": start_line_no,
            "end_line": len(lines),
            "text": "\n".join(l[1] for l in current_lines),
            "lines": list(current_lines)
        })

    return sections

def audit_section_head_hopping(section: Dict[str, Any], cast_names: List[str]) -> List[Tuple[int, str, str, str]]:
    """Audit a section for unauthorized internal mental intrusion of non-POV characters."""
    violations = []
    pov_char = section["pov"].strip()
    pov_first_name = pov_char.split()[0].lower()

    # Other cast characters in this scene that should NOT have their minds read
    other_chars = [c for c in cast_names if c.lower() != pov_first_name and len(c) >= 3]

    for line_no, line in section["lines"]:
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "---", ">", "<!--")):
            continue
        
        # Don't flag quoted dialogue!
        non_dialogue = re.sub(r'"[^"]*"', '', stripped)
        non_dialogue = re.sub(r'“[^”]*”', '', non_dialogue)

        for other in other_chars:
            # Check pattern: "Character [felt|thought|knew|...]"
            for verb in INTERNAL_STATE_VERBS:
                pattern = rf"\b{re.escape(other)}\s+{verb}\b"
                if re.search(pattern, non_dialogue, re.IGNORECASE):
                    advice = (f"POV is '{pov_char}'. '{other} {verb}' is a head-hop into non-POV mind. "
                              f"Physicalize the perception (e.g. observe their expression, posture, or tone).")
                    violations.append((line_no, other, stripped, advice))

            # Check pattern: "OtherCharacter wondered / decided in his heart"
            for noun_pat in INTERNAL_NOUN_PATTERNS:
                if re.search(rf"\b{re.escape(other)}\b", non_dialogue, re.IGNORECASE) and re.search(noun_pat, non_dialogue, re.IGNORECASE):
                    advice = (f"POV is '{pov_char}'. Private interiority of '{other}' detected. "
                              f"Observe via external physical senses instead.")
                    violations.append((line_no, other, stripped, advice))

    return violations

def audit_chapter_pov(file_path: Path) -> Dict[str, Any]:
    """Audit an individual chapter markdown file for POV structure and integrity."""
    raw_text = file_path.read_text(encoding="utf-8")
    
    # 1. Parse frontmatter
    default_pov = "Unknown"
    cast = []
    
    if raw_text.startswith("---"):
        parts = raw_text.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            try:
                import yaml
                data = yaml.safe_load(fm_text) or {}
                if isinstance(data, dict):
                    pov_meta = data.get("pov")
                    if isinstance(pov_meta, dict):
                        default_pov = pov_meta.get("primary", default_pov)
                    elif isinstance(pov_meta, str):
                        default_pov = pov_meta
                    if "characters" in data and isinstance(data["characters"], list):
                        cast = [c.split()[0] for c in data["characters"] if isinstance(c, str)]
            except Exception:
                pass

            # Robust fallback if yaml module is missing or failed
            if default_pov == "Unknown":
                pov_match = re.search(r"^pov:\s*(.*?)$", fm_text, re.MULTILINE)
                if pov_match:
                    p_val = pov_match.group(1).strip().strip('"').strip("'")
                    if p_val and not p_val.startswith("{"):
                        default_pov = p_val
            body_text = parts[2]
        else:
            body_text = raw_text
    else:
        body_text = raw_text

    # Dynamic fallback: scan lore/characters directory if no frontmatter characters specified
    if not cast and file_path.is_file():
        u_root = file_path.parent
        for _ in range(5):
            if (u_root / "universe.yaml").is_file():
                break
            u_root = u_root.parent
        for char_dir in [u_root / "lore" / "characters", u_root / "wiki" / "terms" / "characters"]:
            if char_dir.is_dir():
                for cf in char_dir.glob("*.md"):
                    first_name = cf.stem.split("-")[0].title()
                    if first_name not in cast:
                        cast.append(first_name)

    sections = split_sections(body_text, default_pov)
    all_violations = []

    for sec in sections:
        viols = audit_section_head_hopping(sec, cast)
        for line_no, other, line_text, advice in viols:
            all_violations.append({
                "line": line_no,
                "section": sec["section_index"],
                "pov": sec["pov"],
                "intruder": other,
                "text": line_text,
                "advice": advice
            })

    return {
        "file": file_path.name,
        "default_pov": default_pov,
        "section_count": len(sections),
        "sections": [{"index": s["section_index"], "pov": s["pov"], "lines": f"{s['start_line']}-{s['end_line']}"} for s in sections],
        "violations": all_violations,
        "passed": len(all_violations) == 0
    }

def print_pov_report(res: Dict[str, Any]):
    print("\n" + "=" * 80)
    print(f"DEEP LIMITED POV & HEAD-HOPPING AUDIT: {res['file']}")
    print("=" * 80)
    print(f"• Primary POV: {res['default_pov']} | Sections: {res['section_count']}")
    for s in res["sections"]:
        print(f"  └─ Section {s['index']} [Lines {s['lines']}]: POV -> {s['pov']}")
    print("-" * 80)

    if res["passed"]:
        print("🎉 100% DEEP POV INTEGRITY: Zero head-hopping or non-POV telepathy detected!\n")
    else:
        print(f"⚠️ DETECTED {len(res['violations'])} HEAD-HOPPING / INTERIORITY LEAKS:")
        for v in res["violations"]:
            snip = v["text"][:60] + "..." if len(v["text"]) > 60 else v["text"]
            print(f"  • Line {v['line']:>4} [Sec {v['section']} - POV: {v['pov']}]: '{snip}'")
            print(f"    💡 Fix: {v['advice']}")
        print()

def main():
    parser = argparse.ArgumentParser(description="CanonForge Deep POV & Head-Hopping Auditor")
    parser.add_argument("chapter", nargs="?", default="the-iron-on-the-anvil.md", help="Chapter file or slug")
    parser.add_argument("--all", action="store_true", help="Audit all manuscript chapters")
    args = parser.parse_args()

    if args.all:
        mds = sorted(MANUSCRIPT_DIR.glob("*/*/chapters/*.md"))
        print(f"\n🎭 Running Deep POV & Head-Hopping Audit across {len(mds)} chapters...\n")
        failed = 0
        for ch in mds:
            res = audit_chapter_pov(ch)
            if not res["passed"]:
                failed += 1
                print_pov_report(res)
        if failed == 0:
            print(f"🎉 100% DEEP POV COMPLIANCE across all {len(mds)} manuscript chapters!\n")
            return 0
        else:
            print(f"⚠️ {failed} chapters had head-hopping warnings.\n")
            return 1

    matches = list(MANUSCRIPT_DIR.rglob(f"*{args.chapter}*"))
    files = [m for m in matches if m.is_file() and m.suffix == ".md" and "_build" not in m.parts]
    if not files:
        print(f"❌ File not found: {args.chapter}")
        sys.exit(1)

    all_ok = True
    for f in files:
        res = audit_chapter_pov(f)
        print_pov_report(res)
        if not res["passed"]:
            all_ok = False

    sys.exit(0 if all_ok else 1)

if __name__ == "__main__":
    main()
