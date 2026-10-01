"""
CanonForge CLI: Comprehensive Feature & Anti-Deadend Test Suite
"""

import sys
import io
import shutil
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from canonforge.cli.groups import CAPABILITY_GROUPS, print_grouped_help
from canonforge.cli.dashboard import (
    discover_universes,
    find_workspace_root,
    render_dashboard,
    suggest_similar_command,
)
from canonforge.cli.audit_cmd import run_chapter_audit
from canonforge.cli.new_cmd import new_chapter, new_character
from canonforge.cli.skill_cmd import cmd_skill_export

class TestCliFeatures(unittest.TestCase):
    def test_capability_groups_integrity(self):
        expected_groups = {"PROJECT", "AUTHORING", "AUDITING", "WORLDBUILDING", "PUBLISHING", "AGENT"}
        self.assertEqual(set(CAPABILITY_GROUPS.keys()), expected_groups)
        
        # Verify print_grouped_help produces output without error
        captured = io.StringIO()
        sys.stdout = captured
        try:
            print_grouped_help()
        finally:
            sys.stdout = sys.__stdout__
        output = captured.getvalue()
        self.assertIn("CANONFORGE CLI (cf)", output)
        self.assertIn("[PROJECT]", output)
        self.assertIn("[AUDITING]", output)

    def test_typo_suggester(self):
        captured = io.StringIO()
        sys.stdout = captured
        try:
            suggest_similar_command("senosry", ["sensory", "pov", "prose", "audit"])
        finally:
            sys.stdout = sys.__stdout__
        output = captured.getvalue()
        self.assertIn("Unknown command", output)
        self.assertIn("sensory", output)

    def test_multi_engine_audit_diagnostics(self):
        ch_path = REPO_ROOT / "examples" / "aetheria" / "manuscript" / "skies-of-iron" / "book-01" / "chapters" / "ch01-the-iron-skiff.md"
        diags = run_chapter_audit(ch_path)
        # ch01 in Aetheria is high quality; verify no critical errors
        critical_errors = [d for d in diags if d["severity"] == "error"]
        self.assertEqual(len(critical_errors), 0)

    def test_skill_export(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            class DummyArgs:
                target = "all"
                out_dir = tmp_dir
            
            cmd_skill_export(DummyArgs())
            p_cursor = Path(tmp_dir) / ".cursorrules"
            p_claude = Path(tmp_dir) / "CLAUDE.md"
            p_skill = Path(tmp_dir) / ".gemini" / "skills" / "novel-studio" / "SKILL.md"
            p_agents = Path(tmp_dir) / "AGENTS.md"

            self.assertTrue(p_cursor.is_file())
            self.assertTrue(p_claude.is_file())
            self.assertTrue(p_skill.is_file())
            self.assertTrue(p_agents.is_file())

            self.assertIn("CanonForge", p_cursor.read_text(encoding="utf-8"))
            self.assertIn("cf audit", p_claude.read_text(encoding="utf-8"))

if __name__ == "__main__":
    unittest.main()
