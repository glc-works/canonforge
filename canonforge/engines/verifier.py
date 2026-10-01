"""
Universe Verification Engine
--------------------------------------------------------------------------------
Executes the comprehensive, multi-engine verification gates across any novel
universe: manifests, TOC integrity, chapter frontmatter schemas, sensory radar,
sensory knowledge graph, deep POV, continuity, relations, compiler pacing,
secrets, timeline, dialogue trees, and database integrity.
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False


def _find_sample_chapter(universe_dir: Path) -> Optional[str]:
    """Find a representative chapter file for single-chapter audits."""
    chapters = list(universe_dir.glob("manuscript/*/*/chapters/*.md"))
    if not chapters:
        chapters = list(universe_dir.glob("manuscript/*/*.md"))
    if chapters:
        # Prefer a known benchmark or the first chapter
        for ch in chapters:
            if "anvil" in ch.name.lower() or "ch01" in ch.name.lower():
                return ch.name
        return chapters[0].name
    return None


def verify_universe(universe_dir: Path) -> bool:
    """Run all applicable verification gates on a universe directory."""
    u_dir = universe_dir.resolve()
    print("\n" + "=" * 72)
    print(f"CANONFORGE: VERIFYING UNIVERSE '{u_dir.name}'")
    print("=" * 72)

    # 1. Manifest existence
    u_manifest = u_dir / "universe.yaml"
    if not u_manifest.is_file():
        print(f"❌ Missing universe.yaml in {u_dir}")
        return False

    sample_ch = _find_sample_chapter(u_dir) or "ch01.md"
    py_exec = sys.executable

    # Define test suite specifications
    suites: List[Dict[str, Any]] = []

    # 1. SSOT Lore & Cross-Reference Audit
    if (u_dir / "wiki").is_dir():
        suites.append({
            "name": "SSOT Lore & Cross-Reference Audit",
            "cmd": [py_exec, "-m", "canonforge.engines.sync_db", "--validate"],
            "critical": True,
        })

    # 2. Local Game Database Seeder & SQL Engine
    if (u_dir / "data").is_dir() or (u_dir / "db").is_dir():
        suites.append({
            "name": "Local Game Database Seeder & SQL Engine",
            "cmd": [py_exec, "-m", "canonforge.engines.init_db", "--seed"],
            "critical": True,
        })

    # 3. Ink Dialogue Tree & Branch Validator
    if list(u_dir.glob("dialogue/*.ink")):
        suites.append({
            "name": "Ink Dialogue Tree & Branch Validator",
            "cmd": [py_exec, "-m", "canonforge.engines.dialogue", "--validate"],
            "critical": True,
        })

    # 4. Character Continuity & Physical Invariants Audit
    if list(u_dir.glob("wiki/terms/characters/*.md")) or list(u_dir.glob("wiki/characters/*.md")):
        suites.append({
            "name": "Character Continuity & Physical Invariants Audit (All Books)",
            "cmd": [py_exec, "-m", "canonforge.engines.continuity", "--all"],
            "critical": True,
        })

    # 5. Character Relationship Graph & Dynamic Continuity Suite
    rel_test = u_dir / "scripts" / "test_character_relations.py"
    if rel_test.is_file():
        suites.append({
            "name": "Character Relationship Graph & Dynamic Continuity Suite",
            "cmd": [py_exec, str(rel_test)],
            "critical": True,
        })
    elif (u_dir / "wiki" / "database" / "relationships.json").is_file() or (u_dir / "data" / "character_relationships.json").is_file() or (u_dir / "relationships.json").is_file():
        suites.append({
            "name": "Character Relationship Graph & Dynamic Continuity Suite",
            "cmd": [py_exec, "-m", "canonforge.engines.relations", "audit", sample_ch],
            "critical": True,
        })

    # 6. Authoring Tools Suite (Scene Prep & Unified Polish)
    auth_test = u_dir / "scripts" / "test_authoring_tools.py"
    if auth_test.is_file():
        suites.append({
            "name": "Authoring Tools Suite (Scene Prep & Unified Polish)",
            "cmd": [py_exec, str(auth_test)],
            "critical": True,
        })
    else:
        suites.append({
            "name": "Authoring Tools Suite (Scene Prep & Unified Polish)",
            "cmd": [py_exec, "-m", "canonforge.engines.polish", sample_ch],
            "critical": True,
        })

    # 7. Two-Way TOC & Orphan Chapter Integrity Gate
    suites.append({
        "name": "Two-Way TOC & Orphan Chapter Integrity Gate",
        "cmd": [py_exec, "-m", "canonforge.engines.toc"],
        "critical": True,
    })

    # 8. Chapter Frontmatter Schema Integrity Gate (OKF v0.3)
    suites.append({
        "name": "Chapter Frontmatter Schema Integrity Gate (OKF v0.3)",
        "cmd": [py_exec, "-m", "canonforge.engines.schemas"],
        "critical": True,
    })

    # 9. Sensory Profile & 5-Senses Radar Integrity Gate
    suites.append({
        "name": "Sensory Profile & 5-Senses Radar Integrity Gate",
        "cmd": [py_exec, "-m", "canonforge.engines.sensory.radar", sample_ch],
        "critical": True,
    })

    # 10. Sensory Knowledge Graph & Thesaurus Integrity Gate
    suites.append({
        "name": "Sensory Knowledge Graph & Thesaurus Integrity Gate",
        "cmd": [py_exec, "-m", "canonforge.engines.sensory_dictionary", "--validate-graph"],
        "critical": True,
    })

    # 11. Section-Level Deep POV & Head-Hopping Gate
    suites.append({
        "name": "Section-Level Deep POV & Head-Hopping Gate",
        "cmd": [py_exec, "-m", "canonforge.engines.pov", sample_ch],
        "critical": True,
    })

    # 12. Novel Manuscript Compiler & Pacing (All Books)
    suites.append({
        "name": "Novel Manuscript Compiler & Pacing (All Books)",
        "cmd": [py_exec, "-m", "canonforge.engines.compiler", "--all"],
        "critical": True,
    })

    # 13. Epistemic State & Narrative Secrets Gate
    if list(u_dir.glob("wiki/lore/secrets.yaml")) or list(u_dir.glob("wiki/secrets.yaml")):
        suites.append({
            "name": "Epistemic State & Narrative Secrets Gate",
            "cmd": [py_exec, "-m", "canonforge.engines.secrets", "--all"],
            "critical": True,
        })

    # 14. Chronology & Travel Physics Gate
    if (u_dir / "timeline.json").is_file() or list(u_dir.glob("data/timeline*.json")):
        suites.append({
            "name": "Chronology & Travel Physics Gate",
            "cmd": [py_exec, "-m", "canonforge.engines.timeline", "--all"],
            "critical": True,
        })

    results = []
    all_passed = True

    for suite in suites:
        suite_name = suite["name"]
        print(f"\n▶ Running: {suite_name}...")
        res = subprocess.run(suite["cmd"], cwd=str(u_dir), capture_output=True, text=True)

        status = "PASSED" if res.returncode == 0 else "FAILED"
        if res.returncode != 0:
            if suite["critical"]:
                all_passed = False
            print(f"❌ {suite_name} output:\n{res.stdout}\n{res.stderr}")
        else:
            lines = [line for line in res.stdout.strip().splitlines() if line.strip()]
            summary_snippet = lines[-1] if lines else "OK"
            print(f"  ✓ {summary_snippet}")

        results.append([suite_name, "Critical" if suite["critical"] else "Standard", status])

    print("\n" + "=" * 72)
    print(f"CANONFORGE: VERIFICATION REPORT FOR '{u_dir.name}'")
    print("=" * 72)
    if HAS_TABULATE:
        print(tabulate(results, headers=["Test Suite", "Type", "Status"], tablefmt="psql"))
    else:
        for r in results:
            print(f"  • [{r[2]}] {r[0]} ({r[1]})")
    print("-" * 72)

    if all_passed:
        print(f"🎉 ALL SYSTEMS GO: Universe '{u_dir.name}' is 100% verified and in sync!\n")
        return True
    else:
        print(f"💥 CRITICAL FAILURES DETECTED in '{u_dir.name}'. Review logs above.\n")
        return False
