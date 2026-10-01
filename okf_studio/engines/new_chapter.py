#!/usr/bin/env python3
"""
CONVERGENCE STUDIO: CHAPTER SCAFFOLD GENERATOR
------------------------------------------------------------------------------
Generates standardized OKF v0.3 chapter markdown files with valid YAML
frontmatter, SSOT metadata, and authoring guidelines to ensure zero-friction
compliance with audit_prose.py and audit_sensory.py.
------------------------------------------------------------------------------
"""

import sys
import re
import argparse
from pathlib import Path

CONVERGENCE_DIR = Path(__file__).resolve().parent.parent
MANUSCRIPT_DIR = CONVERGENCE_DIR / "manuscript"

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")

def main():
    parser = argparse.ArgumentParser(description="Generate a standardized Convergence novel chapter scaffold.")
    parser.add_argument("--book", required=True, help="Book slug (e.g. the-sun-sanctum-disciple)")
    parser.add_argument("--act", type=int, required=True, help="Act number (1, 2, 3, 4)")
    parser.add_argument("--chapter", type=int, required=True, help="Chapter number (1..25)")
    parser.add_argument("--title", required=True, help="Chapter title")
    parser.add_argument("--pov", default="Vaelin of Mist-Hollow", help="POV character name")
    parser.add_argument("--setting", default="High Sanctum", help="Primary setting/location")
    parser.add_argument("--timeline", default="1068 AO", help="Timeline anchor")
    parser.add_argument("--characters", nargs="*", default=["Vaelin of Mist-Hollow", "Corin Solen", "Lyra"], help="Characters present")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite if file exists")

    args = parser.parse_args()

    # Resolve book dir
    book_path = MANUSCRIPT_DIR / args.book
    if not book_path.exists():
        candidates = list(MANUSCRIPT_DIR.glob(f"*/{args.book}")) + list(MANUSCRIPT_DIR.glob(f"*/*{args.book}*"))
        if candidates:
            book_path = candidates[0]
    book_dir = book_path / "chapters"
    book_dir.mkdir(parents=True, exist_ok=True)

    slug = slugify(args.title)
    filename = f"{slug}.md"
    target_path = book_dir / filename

    if target_path.exists() and not args.overwrite:
        print(f"❌ Error: {target_path} already exists. Pass --overwrite to replace.")
        sys.exit(1)

    char_list_yaml = "\n".join(f"  - {c.strip()}" for c in args.characters)

    content = f"""---
okf_version: "0.3"
title: "{args.title}"
type: "Chapter Entity"
mode: "manuscript"
status: "draft"
authority: "canon-lead"
book: "{args.book}"
act: {args.act}
chapter: {args.chapter}
pov: "{args.pov}"
setting: "{args.setting}"
timeline: "{args.timeline}"
characters:
{char_list_yaml}
tags:
  - act-{args.act}
  - {slug}
---

<!--
  AUTHORING GUIDELINES:
  1. DEEP POV: Avoid cognitive filter words (saw, heard, felt, realized) in narrative prose. Characters speak naturally in dialogue.
  2. SENSORY IMMERSION: Adhere to the Three-Sense Rule (at least 3 distinct senses per 500-word scene window). Never force artificial sensory hacks (no copper/bile or artificial taste in non-food scenes).
  3. ACTION BEATS: Use physical actions instead of repetitive speech tags ('whispered', 'hissed').
  4. SINGLE VISCERAL SCENT: Use one sharp, memorable scent rather than listing three generic smells.
  5. CLOSING HOOK: End the chapter with a sensory-grounded beat (aroma, physical touch, acoustic reverb) to anchor the scene.
-->

The morning broke over...

"""

    target_path.write_text(content.strip() + "\n", encoding="utf-8")
    print(f"✅ Created chapter scaffold: {target_path.relative_to(CONVERGENCE_DIR)}")
    print(f"• Title: {args.title}")
    print(f"• Book: {args.book} (Act {args.act}, Chapter {args.chapter})")
    print(f"• POV: {args.pov}")

if __name__ == "__main__":
    main()
