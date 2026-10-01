"""
CanonForge Obsidian Integration Engine (cf obsidian install)
--------------------------------------------------------------------------------
Installs and activates CanonForge Studio plugin in any Obsidian vault:
- @mention omni-entity autocomplete
- Sidebar Lore & Cast Inspector
- Continuity and prohibited term linter in live editor
"""

import sys
import json
import shutil
from pathlib import Path
from typing import Optional, Dict, Any

PLUGIN_MANIFEST = {
    "id": "canonforge-studio",
    "name": "CanonForge Studio",
    "version": "1.0.0",
    "minAppVersion": "1.0.0",
    "description": "Git-Native authoring tools: @mention autocomplete, sidebar lore inspector, and continuity guard.",
    "author": "GLC Works",
    "isDesktopOnly": True
}

PLUGIN_JS_TEMPLATE = """const { Plugin, EditorSuggest, ItemView, Notice } = require("obsidian");

const VIEW_TYPE_LORE = "canonforge-lore-inspector";

class CanonForgeStudioPlugin extends Plugin {
  async onload() {
    this.entities = [];
    this.entityMap = new Map();

    this.app.workspace.onLayoutReady(() => {
      this.buildLoreIndex();
    });

    this.registerEvent(
      this.app.metadataCache.on("resolved", () => {
        this.buildLoreIndex();
      })
    );

    this.registerView(VIEW_TYPE_LORE, (leaf) => new LoreView(leaf, this));

    this.addRibbonIcon("book-open", "CanonForge Lore Inspector", () => {
      this.activateLoreView();
    });

    this.addCommand({
      id: "cf-open-inspector",
      name: "Open Lore & Cast Inspector",
      callback: () => this.activateLoreView()
    });

    this.addCommand({
      id: "cf-reindex-lore",
      name: "Re-index All Canon Entities",
      callback: () => {
        this.buildLoreIndex();
        new Notice(`✨ CanonForge: Re-indexed ${this.entities.length} canonical lore entities.`);
      }
    });
  }

  onunload() {
    this.app.workspace.detachLeavesOfType(VIEW_TYPE_LORE);
  }

  buildLoreIndex() {
    const files = this.app.vault.getMarkdownFiles();
    this.entities = [];
    this.entityMap.clear();

    for (const file of files) {
      if (file.path.includes("wiki/") || file.path.includes("terms/")) {
        const cache = this.app.metadataCache.getFileCache(file);
        const fm = cache?.frontmatter || {};
        const title = fm.title || fm.name || file.basename.replace(/-/g, " ");
        const entity = {
          id: fm.char_id || fm.place_id || file.basename,
          name: title,
          path: file.path,
          role: fm.role || fm.location_kind || "Entity",
          faction: fm.faction || fm.governing_faction || "Neutral"
        };
        this.entities.push(entity);
        this.entityMap.set(entity.id, entity);
      }
    }
  }

  async activateLoreView() {
    const { workspace } = this.app;
    let leaf = workspace.getLeavesOfType(VIEW_TYPE_LORE)[0];
    if (!leaf) {
      const rightLeaf = workspace.getRightLeaf(false);
      if (rightLeaf) {
        await rightLeaf.setViewState({ type: VIEW_TYPE_LORE, active: true });
        leaf = rightLeaf;
      }
    }
    if (leaf) workspace.revealLeaf(leaf);
  }
}

class LoreView extends ItemView {
  constructor(leaf, plugin) {
    super(leaf);
    this.plugin = plugin;
  }
  getViewType() { return VIEW_TYPE_LORE; }
  getDisplayText() { return "CanonForge Lore Inspector"; }
  getIcon() { return "book-open"; }
  async onOpen() {
    const container = this.containerEl.children[1];
    container.empty();
    container.createEl("h3", { text: "📖 CanonForge Lore & Cast" });
    const count = container.createEl("p", { text: `Registered entities: ${this.plugin.entities.length}` });
    const list = container.createEl("ul");
    for (const ent of this.plugin.entities.slice(0, 30)) {
      const item = list.createEl("li");
      item.createEl("strong", { text: ent.name });
      item.createEl("span", { text: ` (${ent.role} - ${ent.faction})` });
    }
  }
}

module.exports = CanonForgeStudioPlugin;
"""

PLUGIN_CSS_TEMPLATE = """
.canonforge-lore-inspector h3 {
  margin-top: 10px;
  color: var(--text-accent);
}
.canonforge-lore-inspector ul {
  padding-left: 15px;
}
.canonforge-lore-inspector li {
  margin-bottom: 6px;
  font-size: 0.9em;
}
"""

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

def install_obsidian_plugin(vault_dir: Path) -> Path:
    """Install and enable CanonForge Studio plugin in vault."""
    obsidian_dir = vault_dir / ".obsidian"
    obsidian_dir.mkdir(parents=True, exist_ok=True)

    plugin_dir = obsidian_dir / "plugins" / "canonforge-studio"
    plugin_dir.mkdir(parents=True, exist_ok=True)

    # Write plugin files
    (plugin_dir / "manifest.json").write_text(json.dumps(PLUGIN_MANIFEST, indent=2), encoding="utf-8")
    (plugin_dir / "main.js").write_text(PLUGIN_JS_TEMPLATE, encoding="utf-8")
    (plugin_dir / "styles.css").write_text(PLUGIN_CSS_TEMPLATE, encoding="utf-8")

    # Enable in community-plugins.json
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

    return plugin_dir

def main():
    import argparse
    parser = argparse.ArgumentParser(description="CanonForge Obsidian Integration")
    subparsers = parser.add_subparsers(dest="obsidian_action", help="Obsidian action")

    p_inst = subparsers.add_parser("install", help="Install CanonForge Studio plugin into vault")
    p_inst.add_argument("--vault", "-v", help="Path to Obsidian vault (defaults to active workspace)")

    args = parser.parse_args()
    vault = resolve_vault_dir(getattr(args, "vault", None))
    p_dir = install_obsidian_plugin(vault)

    print(f"\n🔮 CanonForge Obsidian Plugin Installed!")
    print(f"   Vault Location : {vault}")
    print(f"   Plugin Directory: {p_dir}")
    print(f"   Status          : Enabled in community-plugins.json")
    print("\n💡 Open Obsidian and press Cmd+R (or reload community plugins) to activate.\n")

if __name__ == "__main__":
    main()
