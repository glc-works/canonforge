#!/usr/bin/env python3
"""
CANONFORGE STUDIO: EPISTEMIC STATE & SECRET TRACKING AUDITOR
------------------------------------------------------------------------------
Protects narrative tension by verifying that plot secrets and revelations
are not prematurely leaked or discussed by characters prior to their canonical
reveal chapters.
------------------------------------------------------------------------------
"""

import sys
import re
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from canonforge.core.manifest import find_universe_root

UNIVERSE_DIR = find_universe_root()
MANUSCRIPT_DIR = UNIVERSE_DIR / "manuscript"
SECRETS_FILE = UNIVERSE_DIR / "data" / "narrative_secrets.yaml"

def load_secrets() -> List[Dict[str, Any]]:
    if not SECRETS_FILE.is_file():
        return []
    try:
        import yaml
        data = yaml.safe_load(SECRETS_FILE.read_text(encoding="utf-8")) or {}
        return data.get("secrets", [])
    except Exception:
        return []

def get_chronological_chapter_order() -> List[Path]:
    """Return all manuscript chapters in canonical TOC reading order."""
    chapters = []
    # Discover all tocs
    for toc in sorted(MANUSCRIPT_DIR.glob("*/*/toc.yaml")):
        try:
            import yaml
            data = yaml.safe_load(toc.read_text(encoding="utf-8")) or {}
            for act in data.get("acts", []):
                for ch in act.get("chapters", []):
                    f_name = ch if isinstance(ch, str) else (ch.get("file") if isinstance(ch, dict) else None)
                    if f_name:
                        f_path = toc.parent / "chapters" / f_name
                        if f_path.is_file():
                            chapters.append(f_path)
        except Exception:
            pass
    return chapters

def audit_secrets_for_chapter(chapter_path: Path, secret_definitions: List[Dict[str, Any]], chapter_order: List[Path]) -> List[Dict[str, Any]]:
    violations = []
    text = chapter_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Determine index of current chapter
    ch_name = chapter_path.name
    try:
        current_idx = [c.name for c in chapter_order].index(ch_name)
    except ValueError:
        current_idx = -1

    for s in secret_definitions:
        reveal_file = s.get("reveal_chapter")
        try:
            reveal_idx = [c.name for c in chapter_order].index(reveal_file)
        except ValueError:
            reveal_idx = -1

        # Only audit chapters strictly before the reveal chapter
        if reveal_idx != -1 and current_idx != -1 and current_idx >= reveal_idx:
            continue

        token_groups = s.get("sensitive_token_groups", [])
        for line_no, line in enumerate(lines, start=1):
            line_lower = line.lower()
            for group in token_groups:
                # Check if all tokens in the sensitive group occur in this line
                if all(re.search(rf"\b{re.escape(t.lower())}\b", line_lower) for t in group):
                    violations.append({
                        "file": ch_name,
                        "line": line_no,
                        "secret_id": s.get("id"),
                        "secret_name": s.get("name"),
                        "reveal_chapter": reveal_file,
                        "snippet": line.strip(),
                        "matched_group": group
                    })

    return violations

def main():
    parser = argparse.ArgumentParser(description="CanonForge Epistemic State & Secret Tracking Auditor")
    parser.add_argument("chapter", nargs="?", help="Chapter file or slug to audit")
    parser.add_argument("--all", action="store_true", help="Audit all chapters across the manuscript")
    args = parser.parse_args()

    secrets = load_secrets()
    if not secrets:
        print("⚠️ No narrative secrets defined in data/narrative_secrets.yaml.")
        sys.exit(0)

    order = get_chronological_chapter_order()

    if args.all or not args.chapter:
        target_files = order
    else:
        matches = list(MANUSCRIPT_DIR.rglob(f"*{args.chapter}*"))
        target_files = [m for m in matches if m.is_file() and m.suffix == ".md" and "_build" not in m.parts]

    all_violations = []
    for ch in target_files:
        viols = audit_secrets_for_chapter(ch, secrets, order)
        all_violations.extend(viols)

    print("\n" + "=" * 80)
    print(f"EPISTEMIC STATE & SECRET TRACKING AUDIT ({len(target_files)} chapters)")
    print("=" * 80)
    print(f"• Active Secrets Monitored: {len(secrets)}")

    if not all_violations:
        print("🎉 100% EPISTEMIC INTEGRITY: Zero premature narrative leaks or plot-secret spoilers detected!\n")
        sys.exit(0)

    print(f"⚠️ DETECTED {len(all_violations)} PREMATURE REVELATION SPOILERS:")
    for v in all_violations:
        snip = v["snippet"][:60] + "..." if len(v["snippet"]) > 60 else v["snippet"]
        print(f"  • {v['file']}:{v['line']} -> Secret [{v['secret_name']}]")
        print(f"    Snippet: '{snip}'")
        print(f"    💡 Canonical Reveal is in: {v['reveal_chapter']}! Remove premature disclosure.\n")

    sys.exit(1)

if __name__ == "__main__":
    main()
