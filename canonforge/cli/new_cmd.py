"""
CanonForge CLI: Hierarchical Scaffolding Engine (cf new)
--------------------------------------------------------------------------------
Provides first-class noun/verb scaffolding commands:
  cf new universe <slug>
  cf new series <slug>
  cf new book <slug>
  cf new chapter [--title ...]
  cf new character <name>
"""

import sys
import re
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from canonforge.cli.groups import style
from canonforge.cli.dashboard import find_workspace_root, find_enclosing_universe

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = PACKAGE_ROOT / "schemas"

def _resolve_universe_dir(universe_arg: Optional[str]) -> Path:
    if universe_arg:
        root = find_workspace_root()
        u_dir = root / universe_arg
        if u_dir.is_dir() and (u_dir / "universe.yaml").is_file():
            return u_dir
        # Check subdirectories
        for item in root.iterdir():
            if item.is_dir() and (item / "universe.yaml").is_file():
                if item.name.lower() == universe_arg.lower():
                    return item
        print(f"❌ Error: Universe '{universe_arg}' not found under {root}")
        sys.exit(1)
    
    enclosing = find_enclosing_universe()
    if enclosing:
        return enclosing

    root = find_workspace_root()
    # Check if there is only 1 universe in workspace
    cand = [d for d in root.iterdir() if d.is_dir() and (d / "universe.yaml").is_file()]
    if len(cand) == 1:
        return cand[0]

    print("❌ Error: Must specify --universe or run inside a universe directory.")
    sys.exit(1)

def new_universe(args):
    """Scaffold a brand new universe repository with full 5-tier OKF hierarchy."""
    slug = re.sub(r"[^a-zA-Z0-9_-]", "-", args.slug.lower()).strip("-")
    root = find_workspace_root()
    u_dir = root / slug
    if u_dir.exists():
        print(f"❌ Error: Directory '{slug}' already exists at {u_dir}")
        sys.exit(1)

    display_name = getattr(args, "title", None) or slug.replace("-", " ").title()
    genre = getattr(args, "genre", None) or "Speculative Fiction"
    sensory = getattr(args, "sensory_profile", None) or "high_fantasy"

    print(f"\n🏗️  Scaffolding New Universe: {style(display_name, 'bold')} [{slug}]...")

    # Directory Structure
    (u_dir / "manuscript" / "series-01" / "book-01" / "chapters").mkdir(parents=True, exist_ok=True)
    (u_dir / "manuscript" / "_build" / "compiled").mkdir(parents=True, exist_ok=True)
    (u_dir / "wiki" / "terms" / "characters").mkdir(parents=True, exist_ok=True)
    (u_dir / "wiki" / "terms" / "factions").mkdir(parents=True, exist_ok=True)
    (u_dir / "wiki" / "terms" / "places").mkdir(parents=True, exist_ok=True)
    (u_dir / "wiki" / "systems").mkdir(parents=True, exist_ok=True)
    (u_dir / "data" / "sensory_profiles").mkdir(parents=True, exist_ok=True)
    (u_dir / "schemas").mkdir(parents=True, exist_ok=True)

    # 1. universe.yaml
    u_content = f"""universe_id: "{slug}"
display_name: "{display_name}"
version: "1.0.0"
authority: "canon-lead"
status: "in-development"

genre:
  - "{genre}"

sensory_profile: "{sensory}"

metaphysics:
  primary_source: "Quantum Resonance / Living Force"
  core_conflict: "Ancient Legacy vs Modern Exploitation"

series_catalog:
  - id: "series-01"
    title: "{display_name} - Series One"
    path: "manuscript/series-01"
    status: "in-progress"
"""
    (u_dir / "universe.yaml").write_text(u_content, encoding="utf-8")

    # 2. series.yaml
    s_content = f"""series_id: "series-01"
title: "{display_name} - Series One"
universe: "{slug}"
status: "in-progress"
author: "Author"

books:
  - book_number: 1
    directory: "book-01"
    title: "Book 1: Awakening"
    status: "in-progress"
"""
    (u_dir / "manuscript" / "series-01" / "series.yaml").write_text(s_content, encoding="utf-8")

    # 3. toc.yaml
    t_content = f"""book:
  id: "book-01"
  book_number: 1
  series_id: "series-01"
  title: "Book 1: Awakening"
  status: "in-progress"
  act_structure: "3-act"

acts:
  - act: 1
    title: "The Descent"
    chapters:
      - file: "ch01-the-first-signal.md"
        title: "The First Signal"
        chapter_number: 1
        pov: "Protagonist"
"""
    (u_dir / "manuscript" / "series-01" / "book-01" / "toc.yaml").write_text(t_content, encoding="utf-8")

    # 4. First chapter
    ch_content = f"""---
okf_version: "0.3"
chapter: 1
act: 1
title: "The First Signal"
pov: "Protagonist"
timeline: "Year 1"
setting: "District Sector"
word_count: 500
characters:
  - "Protagonist"
sensory_focus:
  - "Sight: Cold neon amber on wet stone"
  - "Sound: Low rhythmic vibration of steam valves"
  - "Smell: Singed pine resin and machine oil"
  - "Taste: Bitter ration tea"
  - "Touch: Rough granite lintel"
status: "draft"
---

# Chapter 1: The First Signal

The neon beacon over the alleyway flickered with a quiet, persistent buzz, casting cold shadows across the wet deck.
"""
    (u_dir / "manuscript" / "series-01" / "book-01" / "chapters" / "ch01-the-first-signal.md").write_text(ch_content, encoding="utf-8")

    # 5. Copy schema
    if SCHEMAS_DIR.is_dir():
        for sf in SCHEMAS_DIR.glob("*.json"):
            shutil.copy(sf, u_dir / "schemas" / sf.name)

    # 6. ax wrapper script
    ax_content = """#!/usr/bin/env bash
set -e
if command -v cf >/dev/null 2>&1; then
    exec cf "$@"
else
    python3 -m canonforge.cli "$@"
fi
"""
    u_ax = u_dir / "ax"
    u_ax.write_text(ax_content, encoding="utf-8")
    u_ax.chmod(0o755)

    print(f"✅ Successfully scaffolded universe '{slug}' at: {u_dir}")
    print(f"💡 Get started:")
    print(f"   cd {slug}")
    print(f"   cf prep\n")

def new_series(args):
    """Scaffold a new series under a universe."""
    u_dir = _resolve_universe_dir(getattr(args, "universe", None))
    slug = re.sub(r"[^a-zA-Z0-9_-]", "-", args.slug.lower()).strip("-")
    s_dir = u_dir / "manuscript" / slug
    if s_dir.exists():
        print(f"❌ Error: Series directory '{slug}' already exists at {s_dir}")
        sys.exit(1)

    title = getattr(args, "title", None) or slug.replace("-", " ").title()
    s_dir.mkdir(parents=True, exist_ok=True)
    (s_dir / "book-01" / "chapters").mkdir(parents=True, exist_ok=True)

    s_content = f"""series_id: "{slug}"
title: "{title}"
universe: "{u_dir.name}"
status: "in-progress"
author: "Author"

books:
  - book_number: 1
    directory: "book-01"
    title: "Book 1: Inception"
    status: "in-progress"
"""
    (s_dir / "series.yaml").write_text(s_content, encoding="utf-8")

    t_content = f"""book:
  id: "book-01"
  book_number: 1
  series_id: "{slug}"
  title: "Book 1: Inception"
  status: "in-progress"
  act_structure: "3-act"

acts:
  - act: 1
    title: "Beginning"
    chapters: []
"""
    (s_dir / "book-01" / "toc.yaml").write_text(t_content, encoding="utf-8")
    print(f"✅ Created series '{slug}' in universe '{u_dir.name}' at: {s_dir}")

def new_book(args):
    """Scaffold a new book under a series."""
    u_dir = _resolve_universe_dir(getattr(args, "universe", None))
    series_slug = getattr(args, "series", None)
    ms_dir = u_dir / "manuscript"

    if not series_slug:
        series_dirs = [d for d in ms_dir.iterdir() if d.is_dir() and (d / "series.yaml").is_file()]
        if len(series_dirs) == 1:
            series_slug = series_dirs[0].name
        else:
            print("❌ Error: Multiple series found. Please specify --series <slug>")
            sys.exit(1)

    s_dir = ms_dir / series_slug
    if not s_dir.is_dir():
        print(f"❌ Error: Series directory '{series_slug}' not found at {s_dir}")
        sys.exit(1)

    book_slug = re.sub(r"[^a-zA-Z0-9_-]", "-", args.slug.lower()).strip("-")
    b_dir = s_dir / book_slug
    if b_dir.exists():
        print(f"❌ Error: Book directory '{book_slug}' already exists at {b_dir}")
        sys.exit(1)

    (b_dir / "chapters").mkdir(parents=True, exist_ok=True)
    title = getattr(args, "title", None) or book_slug.replace("-", " ").title()

    t_content = f"""book:
  id: "{book_slug}"
  book_number: 1
  series_id: "{series_slug}"
  title: "{title}"
  status: "in-progress"
  act_structure: "3-act"

acts:
  - act: 1
    title: "Act I"
    chapters: []
"""
    (b_dir / "toc.yaml").write_text(t_content, encoding="utf-8")
    print(f"✅ Created book '{book_slug}' under series '{series_slug}' at: {b_dir}")

def new_chapter(args):
    """Scaffold a new chapter with OKF v0.3 frontmatter and register in toc.yaml."""
    u_dir = _resolve_universe_dir(getattr(args, "universe", None))
    ms_dir = u_dir / "manuscript"

    # Locate target book
    book_arg = getattr(args, "book", None)
    target_book_dir = None
    if book_arg:
        cands = list(ms_dir.glob(f"*/{book_arg}"))
        if cands:
            target_book_dir = cands[0]
    if not target_book_dir:
        tocs = sorted(list(ms_dir.glob("*/*/toc.yaml")))
        if tocs:
            target_book_dir = tocs[0].parent
        else:
            print("❌ Error: No book found. Run 'cf new book <slug>' first.")
            sys.exit(1)

    chapters_dir = target_book_dir / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)

    existing = sorted(list(chapters_dir.glob("*.md")))
    ch_num = len(existing) + 1

    title = getattr(args, "title", None) or f"Chapter {ch_num}"
    slug = re.sub(r"[^a-zA-Z0-9_-]", "-", title.lower()).strip("-")
    filename = f"ch{ch_num:02d}-{slug}.md"
    ch_path = chapters_dir / filename

    act_num = getattr(args, "act", 1) or 1
    pov = getattr(args, "pov", "Protagonist") or "Protagonist"
    setting = getattr(args, "setting", "Unknown Location") or "Unknown Location"

    content = f"""---
okf_version: "0.3"
chapter: {ch_num}
act: {act_num}
title: "{title}"
pov: "{pov}"
timeline: "Standard Year"
setting: "{setting}"
word_count: 0
characters:
  - "{pov}"
sensory_focus:
  - "Sight: "
  - "Sound: "
  - "Smell: "
  - "Taste: "
  - "Touch: "
status: "draft"
---

# Chapter {ch_num}: {title}

The morning mist hung low over the ridges...
"""
    ch_path.write_text(content, encoding="utf-8")
    print(f"✅ Created chapter {ch_num}: {style(filename, 'bold')} at: {ch_path}")

def new_character(args):
    """Scaffold a new canonical character file under wiki/terms/characters/."""
    u_dir = _resolve_universe_dir(getattr(args, "universe", None))
    chars_dir = u_dir / "wiki" / "terms" / "characters"
    chars_dir.mkdir(parents=True, exist_ok=True)

    name = args.name.strip()
    slug = re.sub(r"[^a-zA-Z0-9_-]", "-", name.lower()).strip("-")
    c_path = chars_dir / f"{slug}.md"
    if c_path.exists():
        print(f"❌ Error: Character '{slug}' already exists at {c_path}")
        sys.exit(1)

    faction = getattr(args, "faction", "Independent") or "Independent"
    role = getattr(args, "role", "Protagonist") or "Protagonist"
    pov_capable = getattr(args, "pov", True)

    content = f"""---
char_id: "{slug}"
name: "{name}"
faction: "{faction}"
role: "{role}"
pov_capable: {str(pov_capable).lower()}
status: "active"
sensory_signature:
  - "Sight: Distinct silhouette and posture"
  - "Sound: Measured speech cadence"
  - "Smell: Woodsmoke and rain"
---

# {name}

## Profile
- **Faction**: {faction}
- **Role**: {role}
- **POV Capable**: {'Yes' if pov_capable else 'No'}

## Backstory & Motivation
Detail character background, internal wounds, and narrative desire here.
"""
    c_path.write_text(content, encoding="utf-8")
    print(f"✅ Created character profile: {style(name, 'bold')} [{slug}] at: {c_path}")

def new_asset(args):
    """Scaffold a new visual asset with metadata sidecar."""
    from canonforge.engines.assets import create_asset_entry
    u_dir = _resolve_universe_dir(getattr(args, "universe", None))
    src = Path(args.file) if getattr(args, "file", None) else None
    res = create_asset_entry(
        name=args.name,
        asset_type=getattr(args, "type", "concept"),
        source_file=src,
        prompt=getattr(args, "prompt", None),
        model=getattr(args, "model", "FLUX / Midjourney"),
        lore_reference=getattr(args, "lore", None),
        notes=getattr(args, "notes", None),
        base_dir=u_dir
    )
    print(f"\n🎨 Asset Created: {style(res['name'], 'bold')} [{res['slug']}]")
    print(f"   Category : {res['type'].title()}")
    print(f"   Image    : {res['image_file']}")
    print(f"   Sidecar  : {res['sidecar_file']}")
    if res["linked_entity"]:
        print(f"   Linked To: {res['linked_entity'].name}")
    print()

