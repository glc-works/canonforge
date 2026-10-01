const { Plugin, EditorSuggest, ItemView, Notice } = require("obsidian");

const VIEW_TYPE_LORE = "canonforge-lore-inspector";

const SENSORY_KEYWORDS = {
  sight: ["glint", "gleam", "crimson", "amber", "shadow", "flicker", "silhouette", "pale", "dark", "glow", "violet", "emerald"],
  sound: ["whisper", "creak", "thrum", "echo", "groan", "click", "clatter", "snap", "murmur", "rumble", "rattle", "whistle"],
  smell: ["smoke", "ozone", "sulfur", "tallow", "peat", "cedar", "vinegar", "chicory", "damp", "musk", "ash", "pine"],
  taste: ["salt", "copper", "bitter", "sweet", "bile", "sour", "iron", "metallic", "tang", "honey", "char", "parched"],
  touch: ["cold", "coarse", "frost", "rough", "slick", "granite", "grit", "stiff", "sharp", "numb", "damp", "flint"]
};

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

    this.registerEditorSuggest(new OmniEntitySuggest(this.app, this));
    this.registerView(VIEW_TYPE_LORE, (leaf) => new CanonForgeLoreView(leaf, this));

    this.addRibbonIcon("book-open", "CanonForge Studio Inspector", () => {
      this.activateLoreView();
    });

    this.addCommand({
      id: "cf-open-inspector",
      name: "Open Lore & Cast Inspector (Sidebar)",
      callback: () => this.activateLoreView()
    });

    this.addCommand({
      id: "cf-reindex-lore",
      name: "Re-index All Canon Entities",
      callback: () => {
        this.buildLoreIndex();
        new Notice(`✨ CanonForge: Indexed ${this.entities.length} canonical lore entities.`);
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
      if (file.path.includes("wiki/") || file.path.includes("terms/") || file.path.includes("database/")) {
        const basename = file.basename;
        if (basename.toLowerCase() === "readme" || basename.toLowerCase() === "index") continue;

        const cache = this.app.metadataCache.getFileCache(file);
        const fm = cache?.frontmatter || {};
        const title = fm.title || fm.name || basename.replace(/-/g, " ");

        // Determine category from path
        let category = "lore";
        if (file.path.includes("character")) category = "character";
        else if (file.path.includes("place") || file.path.includes("location")) category = "place";
        else if (file.path.includes("bestiary") || file.path.includes("monster")) category = "monster";
        else if (file.path.includes("item") || file.path.includes("equipment")) category = "item";
        else if (file.path.includes("faction")) category = "faction";

        const entity = {
          id: fm.id || fm.char_id || fm.place_id || basename,
          name: title,
          category: category,
          file: file,
          role: fm.role || fm.classification || fm.location_kind || "Entity",
          faction: fm.faction || fm.governing_faction || "Neutral",
          aliases: Array.isArray(fm.aliases) ? fm.aliases : [title, basename.replace(/-/g, " ")]
        };

        this.entities.push(entity);
        this.entityMap.set(entity.name.toLowerCase(), entity);
        this.entityMap.set(basename.toLowerCase(), entity);
        for (const a of entity.aliases) {
          if (typeof a === "string" && a.trim()) {
            this.entityMap.set(a.toLowerCase().trim(), entity);
          }
        }
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

class OmniEntitySuggest extends EditorSuggest {
  constructor(app, plugin) {
    super(app);
    this.plugin = plugin;
  }

  onTrigger(cursor, editor, file) {
    const line = editor.getLine(cursor.line);
    const sub = line.substring(0, cursor.ch);
    const match = sub.match(/(?:@|\[\[)([a-zA-Z0-9_\-\s]{2,})$/);
    if (!match) return null;

    return {
      start: { line: cursor.line, ch: cursor.ch - match[1].length - (match[0].startsWith("[[") ? 2 : 1) },
      end: cursor,
      query: match[1]
    };
  }

  getSuggestions(context) {
    const q = context.query.toLowerCase();
    return this.plugin.entities
      .filter(e => e.name.toLowerCase().includes(q) || e.aliases.some(a => a.toLowerCase().includes(q)))
      .slice(0, 10);
  }

  renderSuggestion(entity, el) {
    el.createEl("strong", { text: entity.name });
    el.createEl("small", { text: ` [${entity.category.toUpperCase()} • ${entity.role}]`, cls: "u-muted" });
  }

  selectSuggestion(entity, evt) {
    const activeView = this.app.workspace.getActiveViewOfType(ItemView);
    if (!this.context) return;
    const editor = this.context.editor;
    const replacement = `[[${entity.file.basename}|${entity.name}]]`;
    editor.replaceRange(replacement, this.context.start, this.context.end);
  }
}

class CanonForgeLoreView extends ItemView {
  constructor(leaf, plugin) {
    super(leaf);
    this.plugin = plugin;
  }

  getViewType() { return VIEW_TYPE_LORE; }
  getDisplayText() { return "CanonForge Studio"; }
  getIcon() { return "book-open"; }

  async onOpen() {
    this.renderView();
    this.registerEvent(this.app.workspace.on("active-leaf-change", () => this.renderView()));
    this.registerEvent(this.app.workspace.on("editor-change", () => this.renderView()));
  }

  renderView() {
    const container = this.containerEl.children[1];
    container.empty();
    container.addClass("canonforge-lore-inspector");

    // Header
    const header = container.createDiv({ cls: "canonforge-header" });
    header.createEl("h3", { text: "📖 CanonForge Studio" });
    header.createEl("small", { text: `Indexed: ${this.plugin.entities.length} entities` });

    const activeFile = this.app.workspace.getActiveFile();
    if (!activeFile) {
      container.createEl("p", { text: "Open a manuscript chapter or wiki dossier to inspect.", cls: "u-muted" });
      return;
    }

    // Active Document Section
    const activeSec = container.createDiv({ cls: "canonforge-section" });
    activeSec.createEl("div", { text: "ACTIVE DOCUMENT", cls: "canonforge-section-title" });
    activeSec.createEl("strong", { text: activeFile.basename });

    // Word Count & Sensory Radar for markdown notes
    this.app.vault.read(activeFile).then(content => {
      const words = content.trim().split(/\s+/).filter(Boolean).length;
      activeSec.createEl("p", { text: `Word Count: ${words.toLocaleString()} words (~${(words / 220).toFixed(1)} min)` });

      // 5-Senses Radar
      const sensorySec = container.createDiv({ cls: "canonforge-section" });
      sensorySec.createEl("div", { text: "5-SENSES RADAR", cls: "canonforge-section-title" });
      const grid = sensorySec.createDiv({ cls: "canonforge-radar-grid" });

      const textLower = content.toLowerCase();
      for (const [sense, keywords] of Object.entries(SENSORY_KEYWORDS)) {
        let count = 0;
        for (const kw of keywords) {
          const matches = textLower.match(new RegExp(`\\b${kw}`, "g"));
          if (matches) count += matches.length;
        }
        const cell = grid.createDiv({ cls: "canonforge-radar-cell" });
        cell.createDiv({ text: String(count), cls: "canonforge-radar-value" });
        cell.createDiv({ text: sense.toUpperCase(), cls: "canonforge-radar-label" });
      }

      // Detected Entities in Active File
      const entitySec = container.createDiv({ cls: "canonforge-section" });
      entitySec.createEl("div", { text: "DETECTED CANON ENTITIES", cls: "canonforge-section-title" });
      const detected = [];
      for (const ent of this.plugin.entities) {
        if (textLower.includes(ent.name.toLowerCase())) {
          detected.push(ent);
        }
      }

      if (detected.length === 0) {
        entitySec.createEl("span", { text: "No registered entities detected in current text.", cls: "u-muted" });
      } else {
        const pillContainer = entitySec.createDiv();
        for (const d of detected.slice(0, 15)) {
          const pill = pillContainer.createEl("span", { text: `${d.name} (${d.role})`, cls: "canonforge-entity-pill" });
          pill.onclick = () => this.app.workspace.openLinkText(d.file.path, "", false);
        }
      }
    });
  }
}

module.exports = CanonForgeStudioPlugin;
