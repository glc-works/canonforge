# CanonForge (`cf`)

[![CI](https://github.com/glc-works/canonforge/actions/workflows/ci.yml/badge.svg)](https://github.com/glc-works/canonforge/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Spec: OKF v0.3](https://img.shields.io/badge/Spec-OKF%20v0.3-green.svg)](https://github.com/glc-works/canonforge)

> **The Git-Native Literary Engineering Studio & Multi-Universe Canon Orchestrator for Novelists.**

---

## 📖 Overview

**CanonForge** (`cf`) is an open-source, deterministic command-line environment and quality enforcement framework for long-form fiction. Built for novelists, epic series architects, and narrative game designers, CanonForge treats storytelling with the same engineering rigor as mission-critical software: **zero token costs, <10ms deterministic execution, and 100% reproducible literary gates**.

Whether you are writing a standalone fantasy novel or managing a sprawling multi-series universe with dozens of books, CanonForge ensures:
- **Zero Head-Hopping**: Section-level Deep 3rd Limited POV auditing.
- **Sensory Immersion**: 5-Senses Radar enforcing the Three-Sense Rule across 500-word scene windows.
- **Relational Sensory Knowledge Graph**: 697-lemma lexicon with irregular English inflections, compound n-grams (`blast furnace`, `wood smoke`), intensity scales (1-3), counter-polarities, and in-universe lore aliases.
- **Anti-Slop Linter**: Automated detection of AI prose clichés, cognitive filter words, purple tricolons, and flat sentence cadence.
- **Chronological Physics**: Travel distance, transit velocity, and temporal regression checking.
- **Epistemic State Tracking**: Plot-secret leak prevention.
- **Interactive Storytelling**: Integrated Ink dialogue tree runner and turn-based combat simulation.

---

## 🏛️ The 5-Tier OKF Hierarchy (OKF v0.3 Specification)

CanonForge enforces a strict Single Source of Truth (SSOT) hierarchy:

```
Level 1: Workspace Root Orchestrator (cf or canonforge CLI)
   │
   └── Level 2: Universe Manifest (<universe>/universe.yaml)
          │
          └── Level 3: Series Manifest (<universe>/manuscript/<series>/series.yaml)
                 │
                 └── Level 4: Book TOC Manifest (<universe>/manuscript/<series>/<book>/toc.yaml)
                        │
                        └── Level 5: Chapter Frontmatter (<book>/chapters/ch01.md)
```

Every chapter markdown file validates against `schemas/chapter.schema.json`:

```yaml
---
okf_version: "0.3"
chapter: 1
act: 1
title: "The Iron Skiff"
pov: "Lyra Valen"
timeline: "412 SSC"
setting: "Spire Rim Dock Forty"
word_count: 520
characters:
  - "Lyra Valen"
  - "Captain Orlov"
sensory_focus:
  - "Sight: Amber lantern glow on wet copper plating"
  - "Sound: Low hydraulic groan of the davit arm"
  - "Smell: Pungent whale grease and machine oil"
  - "Taste: Bitter chicory dregs in an iron mug"
  - "Touch: Freezing iron railing through leather gloves"
status: "completed"
---
```

---

## ⚡ Quickstart

### 1. Installation

Choose your preferred package manager:

#### Option A: Homebrew (macOS / Linux)
```bash
brew tap glc-works/tap
brew install canonforge
```

#### Option B: `uv` / `uvx` by Astral (Recommended for fast CLI / Python)
```bash
# Run instantly without installing anything:
uvx --from git+https://github.com/glc-works/canonforge.git cf --help

# Or install globally in an isolated sandbox:
uv tool install git+https://github.com/glc-works/canonforge.git
```

#### Option C: From Source (Developers & Contributors)
```bash
git clone https://github.com/glc-works/canonforge.git
cd canonforge
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

---

### 2. Discover Registered Universes

```bash
cf list
```

Output:
```text
================================================================================
CANONFORGE: MULTI-UNIVERSE WORKSPACE DISCOVERY
Workspace Root: /path/to/canonforge
================================================================================
• [aetheria] Aetheria: Skies of Iron | Dieselpunk, Aetheric Fantasy | 1 series, 1 books, 2 ch (933 w)
================================================================================
```

---

### 3. Verify Universe Integrity Gates

```bash
cf verify aetheria
```

Runs all 6 core integrity checks:
1. Manifest validity (`universe.yaml`)
2. JSON Schema conformance (OKF v0.3)
3. Two-Way TOC and chapter file synchronization
4. 5-Senses Radar immersion scoring
5. Section-level Deep 3rd Limited POV audit
6. Relational Sensory Knowledge Graph integrity

---

### 4. Scaffold a Brand New Universe (`cf init`)

```bash
cf init "Chronicles of Eldoria" --genre "Epic Fantasy"
```

Generates an entire OKF v0.3 universe scaffold in seconds.

---

## 🛠️ Tactical Authoring Engines

### 1. Sensory Radar & Thesaurus Graph (`cf sensory`)

```bash
# Run 5-senses radar audit on a chapter:
cf sensory ch01-the-iron-skiff.md

# Output structured JSON for editor/Obsidian integration:
cf sensory ch01-the-iron-skiff.md --format json

# Lookup sensory synonyms and antonyms in the graph:
cf thesaurus "freezing" --theme tactile
```

### 2. Deep POV & Head-Hopping Auditor (`cf pov`)

```bash
cf pov ch01-the-iron-skiff.md
```

### 3. Anti-Slop & AI Cadence Linter (`cf prose`)

```bash
cf prose ch01-the-iron-skiff.md
```

### 4. Unified Literary Health Scorecard (`cf polish`)

```bash
cf polish ch01-the-iron-skiff.md
```

---

## 🚀 Starter Universe: *Aetheria: Skies of Iron*

Included in `examples/aetheria/` is a complete, self-contained public demo universe:
- **Genre**: Dieselpunk / Aetheric Fantasy
- **Contents**: 1 Series (*Skies of Iron*), 1 Book (*The Iron Skiff*), 2 verified chapters (*The Iron Skiff*, *The Cloud Furnace*), character sheets, and factions.
- Run tests on the starter universe:
  ```bash
  python3 -m unittest discover tests
  ```

---

## 🔒 Creative Work Protection & Licensing

- **The Software & Tooling**: Licensed under the **[MIT License](LICENSE)**.
- **Your Creative Writing**: All literary manuscripts, fictional world bibles, lore documents, and creative characters authored using CanonForge remain the **100% exclusive copyright and intellectual property of their respective author(s)**.

---

## 🤝 Community & Contributing

Contributions are welcome from authors, editors, and software engineers alike!

- **[Contributing Guide](CONTRIBUTING.md)**: Development setup with `uv`, architecture overview, and test instructions.
- **[Code of Conduct](CODE_OF_CONDUCT.md)**: Community standards and pledge.
- **[Report a Bug](https://github.com/glc-works/canonforge/issues/new?template=bug_report.yml)**: Submit structured bug reports with chapter snippets.
- **[Request a Feature](https://github.com/glc-works/canonforge/issues/new?template=feature_request.yml)**: Propose new sensory engines, dictionary expansion, or editor integrations.

Built with passion by **[GLC Works](https://github.com/glc-works)** for storytellers everywhere.
