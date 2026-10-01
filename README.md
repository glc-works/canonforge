# OKF Studio: Open Knowledge Fiction Studio

[![CI](https://github.com/glc-works/okf-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/glc-works/okf-studio/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Spec: OKF v0.3](https://img.shields.io/badge/Spec-OKF%20v0.3-green.svg)](https://github.com/glc-works/okf-studio)

> **The Git-Native, Multi-Universe Authoring, Sensory Radar & Integrity Studio for Novelists and Worldbuilders.**

---

## 📖 Overview

**OKF Studio** is an open-source, deterministic command-line environment and quality enforcement framework for long-form fiction. Built for novelists, epic series architects, and narrative game designers, OKF Studio treats storytelling with the same engineering rigor as mission-critical software: **zero token costs, <10ms deterministic execution, and 100% reproducible literary gates**.

Whether you are writing a standalone fantasy novel or managing a sprawling multi-series universe with dozens of books, OKF Studio ensures:
- **Zero Head-Hopping**: Section-level Deep 3rd Limited POV auditing.
- **Sensory Immersion**: 5-Senses Radar enforcing the Three-Sense Rule across 500-word scene windows.
- **Relational Sensory Knowledge Graph**: 697-lemma lexicon with irregular English inflections, compound n-grams (`blast furnace`, `wood smoke`), intensity scales (1-3), counter-polarities, and in-universe lore aliases.
- **Anti-Slop Linter**: Automated detection of AI prose cliches, filter words, purple tricolons, and flat sentence cadence.
- **Chronological Physics**: Travel distance, transit velocity, and temporal regression checking.
- **Epistemic State Tracking**: Plot-secret leak prevention.
- **Interactive Storytelling**: Integrated Ink dialogue tree runner and turn-based combat simulation.

---

## 🏛️ The 5-Tier OKF Hierarchy (OKF v0.3 Specification)

OKF Studio enforces a strict Single Source of Truth (SSOT) hierarchy:

```
Level 1: Workspace Root Orchestrator (okf or novel CLI)
   │
   └── Level 2: Universe Manifest (<universe>/universe.yaml)
          │
          └── Level 3: Series Manifest (<universe>/manuscript/<series>/series.yaml)
                 │
                 └── Level 4: Book TOC Manifest (<universe>/manuscript/<series>/<book>/toc.yaml)
                        │
                        └── Level 5: Chapter Frontmatter (<book>/chapters/ch01.md)
```

Every chapter markdown file must validate against `schemas/chapter.schema.json`:

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
brew install okf
```

#### Option B: `uv` / `uvx` by Astral (Recommended for fast CLI / Python)
```bash
# Run instantly without installing anything:
uvx --from git+https://github.com/glc-works/okf-studio.git okf --help

# Or install globally in an isolated sandbox:
uv tool install git+https://github.com/glc-works/okf-studio.git
```

#### Option C: From Source (Developers & Contributors)
```bash
git clone https://github.com/glc-works/okf-studio.git
cd okf-studio
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

### 2. Discover Registered Universes

```bash
okf list
```

Output:
```text
================================================================================
OKF STUDIO: MULTI-UNIVERSE WORKSPACE DISCOVERY
Workspace Root: /path/to/okf-studio
================================================================================
• [aetheria] Aetheria: Skies of Iron | Dieselpunk, Aetheric Fantasy | 1 series, 1 books, 2 ch (933 w)
================================================================================
```

### 3. Verify Universe Integrity Gates

```bash
okf verify
```

Runs all critical integrity gates:
- Manifest hierarchy (Universe $\rightarrow$ Series $\rightarrow$ TOC $\rightarrow$ Chapter)
- Chapter frontmatter validation against JSON Schema
- 5-Senses Radar & Three-Sense scene window compliance
- Deep 3rd POV & head-hopping audit
- Sensory Knowledge Graph resolution (zero dangling references)

### 4. Scaffold a Brand New Universe

```bash
okf scaffold neon-drift --title "Neon Drift: Sub-Level Nine" --genre "Cyberpunk" --sensory-profile "cyberpunk_scifi"
```

Generates a complete, compliant 5-tier directory structure ready for immediate drafting:
```bash
cd neon-drift
./ax verify
```

---

## 👃 The Sensory Radar & Knowledge Graph

Unlike flat wordlists, OKF Studio includes a **Relational Sensory Knowledge Graph**:
- **Compound N-Grams**: Maximal Munch sliding window matcher recognizes open and hyphenated terms (`blast furnace`, `wood smoke`, `frazil ice`, `machine oil`, `death rattle`) without double-counting constituent words.
- **Intensity Scales**: Categorizes sensory lexemes from `1: Subtle/Mild` to `3: Visceral/Severe`.
- **Atmospheric Polarities**: Balances thermal (*Warm vs. Cold*) and tactile (*Hard vs. Soft*) vectors.
- **Lore Aliases**: Maps fictional worldbuilding jargon (`frost-bind`, `rime-lock`, `cinder-bark`) directly to foundational sensory profiles.

### Querying the Thesaurus Graph

```bash
ax thesaurus "freeze" --theme "industrial_foundry"
```

Output:
```text
📚 SENSORY THESAURUS GRAPH: 'freeze'
  • Canonical Lemma : freeze (Intensity: 3/3)
  • Primary Senses  : sight, touch
  • Vectors         : Thermal: cold | Tactile: hard
  • In-Universe Lore: frost-bind, rime-lock

  🔍 SYNONYMS (Thematic & Intensity Clustered):
     • [1:Mild]     chill            (Senses: touch        | Themes: [core, grimdark])
     • [3:Severe]   frazil ice       (Senses: touch, sight | Themes: [grimdark_military])
     • [3:Severe]   numb             (Senses: touch        | Themes: [core, grimdark_military])

  ⚖️  COUNTER-POLARITY / ANTONYMS (Dynamic Contrast):
     • burn         (Thermal: warm  | Tactile: Neutral | Themes: [core, foundry, hearth])
     • scald        (Thermal: warm  | Tactile: Neutral | Themes: [foundry, hearth])
     • thaw         (Thermal: warm  | Tactile: Neutral | Themes: [core, cozy_hearth])
```

---

## 🔍 Core Literary Gates

### 1. Section-Level Deep POV Auditor (`ax pov`)
Detects head-hopping, non-POV telepathy (*"He didn't realize she was angry"*), and internal sensory leaks from non-POV cast members in 3rd-person limited fiction.

```bash
ax pov ch01-the-iron-skiff.md
```

### 2. Anti-Slop & AI Cadence Linter (`ax prose`)
Highlights filter words (*noticed, felt, heard, watched*), modern anachronisms, purple tricolons, and passive sentence cadence.

```bash
ax prose ch01-the-iron-skiff.md
```

### 3. Single-Pass Literary Reviewer (`ax polish`)
Generates a comprehensive **10-point Literary Health Scorecard** combining pacing, anti-slop, sensory density, and continuity invariants.

```bash
ax polish ch01-the-iron-skiff.md
```

---

## 🚀 Starter Universe: *Aetheria: Skies of Iron*

Included in `examples/aetheria/` is a complete, self-contained public demo universe:
- **Genre**: Dieselpunk / Aetheric Fantasy
- **Contents**: 1 Series (*Skies of Iron*), 1 Book (*The Iron Skiff*), 2 verified chapters (*The Iron Skiff*, *The Cloud Furnace*), character sheets, and factions.
- Run tests on the starter universe:
  ```bash
  python -m unittest discover -s tests
  ```

---

## 🔒 Creative Work Protection & Licensing

- **The Software & Tooling**: Licensed under the **[MIT License](LICENSE)**.
- **Your Creative Writing**: All literary manuscripts, fictional world bibles, lore documents, and creative characters authored using OKF Studio remain the **100% exclusive copyright and intellectual property of their respective author(s)**.

---

## 🤝 Community & Contributing

Contributions are welcome from authors, editors, and software engineers alike!

- **[Contributing Guide](CONTRIBUTING.md)**: Development setup with `uv`, architecture overview, and test instructions.
- **[Code of Conduct](CODE_OF_CONDUCT.md)**: Community standards and pledge.
- **[Report a Bug](https://github.com/glc-works/okf-studio/issues/new?template=bug_report.yml)**: Submit structured bug reports with chapter snippets.
- **[Request a Feature](https://github.com/glc-works/okf-studio/issues/new?template=feature_request.yml)**: Propose new sensory engines, dictionary expansion, or editor integrations.

Built with passion by **[GLC Works](https://github.com/glc-works)** for storytellers everywhere.

