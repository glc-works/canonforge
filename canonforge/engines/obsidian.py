"""
canonforge/engines/obsidian.py

CanonForge Obsidian Integration Engine (cf obsidian install)
--------------------------------------------------------------------------------
Installs and activates CanonForge Studio plugin in any Obsidian vault:
- @mention omni-entity autocomplete
- Sidebar Lore & Cast Inspector with live 5-senses radar
- Auto-scaffolds standard OKF v0.3 note templates (_templates/)
100% Free of Universe-Specific Hardcoding.
"""

import sys
import os
import json
import shutil
from pathlib import Path
from typing import Optional, Dict, Any

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
OBSIDIAN_DATA_DIR = PACKAGE_ROOT / "data" / "obsidian"
TEMPLATES_DIR = PACKAGE_ROOT / "templates"

def resolve_vault_dir(vault_arg: Optional[str] = None) -> Path:
    """Locate target Obsidian vault directory."""
    if vault_arg:
        p = Path(vault_arg).resolve()
        if p.is_dir():
            return p
        print(f"❌ Error: Specified vault directory not found: {vault_arg}")
        sys.exit(1)

    curr = Path.cwd().resolve()
    for cand in [curr, *curr.parents]:
        if (cand / ".obsidian").is_dir():
            return cand
    return curr

def install_obsidian_plugin(vault_dir: Path, install_templates: bool = True) -> Path:
    """Install and enable CanonForge Studio plugin and OKF templates in vault."""
    obsidian_dir = vault_dir / ".obsidian"
    obsidian_dir.mkdir(parents=True, exist_ok=True)

    plugin_dir = obsidian_dir / "plugins" / "canonforge-studio"
    plugin_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy plugin files from data/obsidian
    if OBSIDIAN_DATA_DIR.exists():
        for f in OBSIDIAN_DATA_DIR.glob("*.*"):
            shutil.copy(f, plugin_dir / f.name)
    else:
        # Fallback minimal plugin if data directory is missing
        (plugin_dir / "manifest.json").write_text(json.dumps({
            "id": "canonforge-studio",
            "name": "CanonForge Studio",
            "version": "1.1.0",
            "minAppVersion": "1.0.0",
            "isDesktopOnly": True
        }, indent=2), encoding="utf-8")
        (plugin_dir / "main.js").write_text("const { Plugin } = require('obsidian'); module.exports = class extends Plugin {};", encoding="utf-8")

    # 2. Enable in community-plugins.json
    cp_path = obsidian_dir / "community-plugins.json"
    enabled_plugins = []
    if cp_path.is_file():
        try:
            enabled_plugins = json.loads(cp_path.read_text(encoding="utf-8"))
        except Exception:
            enabled_plugins = []

    if "canonforge-studio" not in enabled_plugins:
        enabled_plugins.append("canonforge-studio")
        cp_path.write_text(json.dumps(enabled_plugins, indent=2), encoding="utf-8")

    # 3. Install OKF v0.3 Markdown Templates (_templates/)
    if install_templates and TEMPLATES_DIR.exists():
        vault_templates = vault_dir / "_templates"
        vault_templates.mkdir(parents=True, exist_ok=True)
        for t_file in TEMPLATES_DIR.glob("*.md"):
            dest_file = vault_templates / f"{t_file.stem.title()}-Template.md"
            if not dest_file.exists():
                shutil.copy(t_file, dest_file)

    return plugin_dir

def main():
    import argparse
    parser = argparse.ArgumentParser(description="CanonForge Obsidian Integration")
    parser.add_argument("action", nargs="?", default="install", help="Action (install)")
    parser.add_argument("--vault", "-v", help="Path to Obsidian vault (defaults to active workspace)")
    parser.add_argument("--no-templates", action="store_true", help="Do not scaffold _templates folder")

    args = parser.parse_args()
    vault = resolve_vault_dir(getattr(args, "vault", None))
    p_dir = install_obsidian_plugin(vault, install_templates=not getattr(args, "no_templates", False))

    print(f"\n🔮 CanonForge Obsidian Studio Installed!")
    print(f"   Vault Location   : {vault}")
    print(f"   Plugin Directory : {p_dir}")
    print(f"   Plugin Status    : Enabled in community-plugins.json")
    if (vault / "_templates").is_dir():
        print(f"   OKF Templates    : Ready in {vault / '_templates'}")
    print("\n💡 Open Obsidian and press Cmd+R (or reload community plugins) to activate.\n")

if __name__ == "__main__":
    main()
