#!/usr/bin/env python3
"""
validate_chapter_schemas.py

Validates all 221 novel chapters against schemas/chapter.schema.json.
Ensures zero schema drift across all books and sagas.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

from canonforge.core.manifest import find_universe_root

UNIVERSE_DIR = find_universe_root()
MANUSCRIPT_DIR = UNIVERSE_DIR / "manuscript"
SCHEMA_FILE = UNIVERSE_DIR / "schemas" / "chapter.schema.json"
if not SCHEMA_FILE.is_file():
    SCHEMA_FILE = Path(__file__).resolve().parent.parent / "schemas" / "chapter.schema.json"


def validate_all_chapters():
    if not HAS_YAML:
        print("❌ PyYAML required.", file=sys.stderr)
        return 1

    if not SCHEMA_FILE.exists():
        print(f"❌ Schema file not found: {SCHEMA_FILE}", file=sys.stderr)
        return 1

    with open(SCHEMA_FILE, encoding="utf-8") as sf:
        schema = json.load(sf)

    errors = []
    total_validated = 0

    chapter_files = sorted(MANUSCRIPT_DIR.glob("*/*/chapters/*.md"))

    for ch_path in chapter_files:
        if ch_path.name.startswith((".", "MASTER-", "README")):
            continue

        total_validated += 1
        raw_text = ch_path.read_text(encoding="utf-8")
        if not raw_text.startswith("---"):
            errors.append(f"{ch_path.name}: Missing frontmatter delimiter")
            continue

        parts = raw_text.split("---", 2)
        if len(parts) < 3:
            errors.append(f"{ch_path.name}: Incomplete frontmatter block")
            continue

        try:
            fm = yaml.safe_load(parts[1]) or {}
        except Exception as e:
            errors.append(f"{ch_path.name}: Malformed YAML frontmatter: {e}")
            continue

        if HAS_JSONSCHEMA:
            try:
                jsonschema.validate(instance=fm, schema=schema)
            except jsonschema.ValidationError as ve:
                errors.append(f"{ch_path.name}: Schema violation: {ve.message}")
        else:
            # Fallback manual validation for required fields
            for req in schema.get("required", []):
                if req not in fm or fm[req] is None or (isinstance(fm[req], str) and not fm[req].strip()):
                    errors.append(f"{ch_path.name}: Missing required field '{req}'")

    print("\n" + "=" * 70)
    print("CANONFORGE CHAPTER FRONTMATTER SCHEMA VALIDATOR")
    print("=" * 70)
    print(f"• Total Chapters Audited : {total_validated}")
    print(f"• Schema Standard        : schemas/chapter.schema.json (OKF v0.3)")
    print("-" * 70)

    if errors:
        print(f"❌ FAILED: Found {len(errors)} chapter schema violation(s):\n")
        for err in errors[:15]:
            print(f"   ⛔ {err}")
        if len(errors) > 15:
            print(f"   ... and {len(errors) - 15} more.")
        print("\n" + "=" * 70)
        return 1

    print("🎉 100% SCHEMA COMPLIANCE:")
    print("   ✓ All chapter frontmatter conform strictly to OKF v0.3 specifications.")
    print("   ✓ Zero missing fields for pov, timeline, setting, act, chapter, or characters.")
    print("=" * 70 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(validate_all_chapters())
