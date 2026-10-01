"""
CanonForge Asset Management Engine (cf new asset)
--------------------------------------------------------------------------------
Scaffolds and registers creative visual assets (maps, concept art, character art)
with standardized metadata sidecars (.md) conforming to wiki/assets/ conventions.
"""

import sys
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

def resolve_wiki_assets_dir(start_dir: Optional[Path] = None) -> Path:
    """Locate wiki/assets directory in active universe or workspace."""
    curr = (start_dir or Path.cwd()).resolve()
    for cand in [curr, *curr.parents]:
        wiki_assets = cand / "wiki" / "assets"
        if wiki_assets.is_dir():
            return wiki_assets
        if (cand / "universe.yaml").is_file():
            wiki_assets = cand / "wiki" / "assets"
            wiki_assets.mkdir(parents=True, exist_ok=True)
            return wiki_assets
    # Fallback to local
    p = curr / "wiki" / "assets"
    p.mkdir(parents=True, exist_ok=True)
    return p

def create_asset_entry(
    name: str,
    asset_type: str = "concept",
    source_file: Optional[Path] = None,
    prompt: Optional[str] = None,
    model: str = "Midjourney / FLUX",
    lore_reference: Optional[str] = None,
    notes: Optional[str] = None,
    base_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """Create asset file and sidecar metadata .md file."""
    assets_root = resolve_wiki_assets_dir(base_dir)

    # Normalize folder category
    cat_map = {
        "map": "maps",
        "maps": "maps",
        "battlemap": "maps",
        "vtt": "maps",
        "concept": "concepts",
        "concepts": "concepts",
        "character": "characters",
        "item": "items",
        "place": "places",
        "artwork": "artwork"
    }
    sub_folder = cat_map.get(asset_type.lower(), "concepts")
    target_dir = assets_root / sub_folder
    target_dir.mkdir(parents=True, exist_ok=True)

    slug = re.sub(r"[^a-zA-Z0-9_-]", "-", name.lower()).strip("-")
    ext = source_file.suffix.lower() if source_file else ".png"

    dest_image = target_dir / f"{slug}{ext}"
    if source_file and source_file.is_file():
        shutil.copy2(source_file, dest_image)

    # Sidecar metadata markdown
    sidecar_path = target_dir / f"{slug}.md"
    today_str = datetime.now().strftime("%Y-%m-%d")

    clean_prompt = (prompt or "N/A").replace('"', '\\"')
    clean_lore = lore_reference or slug

    sidecar_content = f"""---
asset_name: "{name}"
asset_type: "{sub_folder}"
model: "{model}"
lore_reference: "{clean_lore}"
created_at: "{today_str}"
tags:
  - "asset"
  - "{sub_folder}"
---

# Asset: {name}

## Visual Preview
![[{dest_image.name}]]

## Generation Metadata
- **Prompt**: "{clean_prompt}"
- **Model**: {model}
- **Lore Reference**: [[{clean_lore}]]
- **Created**: {today_str}

## Usage & Continuity Notes
{notes or "Primary visual reference for authoring and character continuity."}
"""
    sidecar_path.write_text(sidecar_content, encoding="utf-8")

    # If lore reference provided, try linking to wiki entity
    linked_entity = None
    if lore_reference:
        wiki_root = assets_root.parent
        for md in wiki_root.glob(f"**/*{lore_reference}*.md"):
            if "assets" not in md.parts and md.is_file():
                try:
                    text = md.read_text(encoding="utf-8")
                    if "## Visual Assets" not in text:
                        text += f"\n\n## Visual Assets\n- ![[{dest_image.name}]]\n"
                    else:
                        text += f"- ![[{dest_image.name}]]\n"
                    md.write_text(text, encoding="utf-8")
                    linked_entity = md
                    break
                except Exception:
                    pass

    return {
        "name": name,
        "slug": slug,
        "type": sub_folder,
        "image_file": dest_image,
        "sidecar_file": sidecar_path,
        "linked_entity": linked_entity
    }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="CanonForge Asset Manager")
    parser.add_argument("name", help="Asset display name or slug")
    parser.add_argument("--type", "-t", choices=["map", "concept", "character", "item", "place", "artwork"], default="concept", help="Asset category")
    parser.add_argument("--file", "-f", help="Source image file to import")
    parser.add_argument("--prompt", "-p", help="Generation prompt used")
    parser.add_argument("--model", "-m", default="FLUX / Midjourney", help="Model used")
    parser.add_argument("--lore", "-l", help="Wiki entity name/slug to link")
    parser.add_argument("--notes", help="Usage notes")
    args = parser.parse_args()

    src = Path(args.file) if args.file else None
    res = create_asset_entry(
        name=args.name,
        asset_type=args.type,
        source_file=src,
        prompt=args.prompt,
        model=args.model,
        lore_reference=args.lore,
        notes=args.notes
    )

    print(f"\n🎨 Asset Created: {res['name']} [{res['slug']}]")
    print(f"   Category : {res['type'].title()}")
    print(f"   Image    : {res['image_file']}")
    print(f"   Sidecar  : {res['sidecar_file']}")
    if res["linked_entity"]:
        print(f"   Linked To: {res['linked_entity'].name}")
    print()

if __name__ == "__main__":
    main()
