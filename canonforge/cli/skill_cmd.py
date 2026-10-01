"""
CanonForge CLI: Agent Skill & Invariants Exporter (cf skill)
--------------------------------------------------------------------------------
Exports standard agent instructions and rules for:
  - Cursor (.cursorrules)
  - Claude Code (CLAUDE.md)
  - Antigravity / Gemini (SKILL.md)
  - Standard Agent Manifest (AGENTS.md)
"""

import sys
from pathlib import Path
from typing import Optional
from canonforge.cli.groups import style
from canonforge.cli.dashboard import find_enclosing_universe, find_workspace_root

CURSORRULES_TEMPLATE = """# CanonForge Authoring & Invariants (.cursorrules)

You are operating within a CanonForge Git-Native Novel Workspace.
Follow these core invariants strictly:

## 1. Hierarchy & Manifest SSOT
- Level 1: Workspace root orchestrator (`./novel` or `cf`).
- Level 2: Universe manifest (`universe.yaml`).
- Level 3: Series manifest (`series.yaml`).
- Level 4: Book manifest (`toc.yaml`).
- Level 5: Chapter frontmatter conforming to OKF v0.3 (`schemas/chapter.schema.json`).

## 2. Zero Creative Hardcoding
- Never hardcode universe names, book titles, or chapter lists in Python scripts.
- Discover and parse dynamically from YAML manifests.

## 3. Deep 3rd Limited POV & 4-Sense Rule
- Deep 3rd Limited POV: Never head-hop. Express emotions via physicalized cues.
- Composable Sensory Radar: Every 500-word scene window must activate at least 3 distinct senses (Sight, Sound, Smell, Taste, Touch).

## 4. Verification Mandate
- Always verify with `cf audit` or `cf verify` before declaring tasks complete.
"""

CLAUDE_MD_TEMPLATE = """# CanonForge Workspace Directives (CLAUDE.md)

Welcome to the CanonForge Novel Studio. All agents operating within this repository must adhere to:

## Commands
- `cf` : View active universe dashboard and recommended next actions
- `cf prep` : Generate authoring brief and drafting pack
- `cf new chapter --title <title>` : Scaffold next chapter with OKF v0.3 frontmatter
- `cf audit` : Run multi-engine prose, sensory, and POV diagnostic audit
- `cf review [chapter]` : Generate literary scorecard (/10)
- `cf export [book]` : Export manuscript to EPUB, Shunn, or Markdown

## Quality Invariants
1. **Prose Preservation**: Never truncate, summarize, or alter author prose in markdown files.
2. **Anti-Slop**: Reject AI tricolons, robotic intros, and melodrama buzzwords.
3. **Deep POV**: Strict single-character focalization per scene section.
"""

SKILL_MD_TEMPLATE = """---
name: novel-studio
description: >-
  Standard operating procedure and governance engine for the CanonForge Multi-Universe Studio.
  Use whenever viewing, editing, or validating novel manuscripts, lore SSOT bibles,
  manifests (universe.yaml, series.yaml, toc.yaml), chapter frontmatter schemas (OKF v0.3),
  or running studio verification gates (cf audit, cf verify).
---

# CanonForge Multi-Universe Studio: Standard Operating Procedure (SOP)

This skill governs the entire authoring, worldbuilding, and automated integrity lifecycle across all fiction universes.

## Verification Gate
Before completing any manuscript editing or code change, run:
```bash
cf audit
cf verify
```
"""

def cmd_skill_export(args):
    """Export agent rules to target directory."""
    out_dir = Path(getattr(args, "out_dir", None) or Path.cwd()).resolve()
    target = getattr(args, "target", "all").lower()

    print(f"\n📦 Exporting CanonForge Agent Rules to: {style(str(out_dir), 'bold')}")

    if target in ("cursor", "all"):
        p = out_dir / ".cursorrules"
        p.write_text(CURSORRULES_TEMPLATE, encoding="utf-8")
        print(f"  ✓ Exported: {style('.cursorrules', 'green')}")

    if target in ("claude", "all"):
        p = out_dir / "CLAUDE.md"
        p.write_text(CLAUDE_MD_TEMPLATE, encoding="utf-8")
        print(f"  ✓ Exported: {style('CLAUDE.md', 'green')}")

    if target in ("gemini", "antigravity", "all"):
        skill_dir = out_dir / ".gemini" / "skills" / "novel-studio"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(SKILL_MD_TEMPLATE, encoding="utf-8")
        print(f"  ✓ Exported: {style('.gemini/skills/novel-studio/SKILL.md', 'green')}")

    if target in ("agents", "all"):
        p = out_dir / "AGENTS.md"
        p.write_text(CLAUDE_MD_TEMPLATE, encoding="utf-8")
        print(f"  ✓ Exported: {style('AGENTS.md', 'green')}")

    print("\n🎉 Agent rules successfully exported!\n")

def cmd_skill_show(args):
    """Display active CanonForge agent skill instructions."""
    print("\n" + style("=" * 80, "cyan"))
    print("CANONFORGE AGENT SKILL & GOVERNANCE INVARIANTS")
    print(style("=" * 80, "cyan"))
    print(CLAUDE_MD_TEMPLATE)
    print(style("=" * 80, "cyan") + "\n")
