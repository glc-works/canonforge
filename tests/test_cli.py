"""
CanonForge: Standard Library Test Suite
"""

import sys
import json
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from canonforge.cli import discover_universes, find_workspace_root
from canonforge.universe_cli import verify_universe
from canonforge.engines import sensory, sensory_dictionary, pov, prose

class TestCanonForge(unittest.TestCase):
    def test_discover_demo_universe(self):
        universes = discover_universes(REPO_ROOT)
        self.assertGreaterEqual(len(universes), 1)
        u = next((x for x in universes if x["id"] == "aetheria"), None)
        self.assertIsNotNone(u)
        self.assertEqual(u["chapter_count"], 2)

    def test_verify_demo_universe(self):
        u_dir = REPO_ROOT / "examples" / "aetheria"
        self.assertTrue(verify_universe(u_dir))

    def test_sensory_knowledge_graph_integrity(self):
        d = sensory_dictionary.get_dictionary()
        val = d.validate_graph_integrity()
        self.assertTrue(val["valid"])
        self.assertGreater(val["total_syn_links"], 0)
        self.assertGreater(val["total_ant_links"], 0)

    def test_sensory_audit_scoring(self):
        ch_path = REPO_ROOT / "examples" / "aetheria" / "manuscript" / "skies-of-iron" / "book-01" / "chapters" / "ch01-the-iron-skiff.md"
        text = ch_path.read_text(encoding="utf-8")
        res = sensory.analyze_text(text)
        self.assertGreaterEqual(res["immersion_score"], 85.0)
        self.assertGreaterEqual(res["four_sense_compliance_pct"], 80.0)

    def test_deep_pov_gate(self):
        ch_path = REPO_ROOT / "examples" / "aetheria" / "manuscript" / "skies-of-iron" / "book-01" / "chapters" / "ch01-the-iron-skiff.md"
        res = pov.audit_chapter_pov(ch_path)
        self.assertTrue(res["passed"])

    def test_prose_anti_slop_audit(self):
        ch_path = REPO_ROOT / "examples" / "aetheria" / "manuscript" / "skies-of-iron" / "book-01" / "chapters" / "ch01-the-iron-skiff.md"
        text = ch_path.read_text(encoding="utf-8")
        res = prose.audit_text(text, filename="ch01.md")
        self.assertGreaterEqual(res["purity_score"], 80.0)
        self.assertEqual(len(res["cliche_hits"]), 0)

    def test_json_serialization(self):
        ch_path = REPO_ROOT / "examples" / "aetheria" / "manuscript" / "skies-of-iron" / "book-01" / "chapters" / "ch01-the-iron-skiff.md"
        pov_res = pov.audit_chapter_pov(ch_path)
        json_str = json.dumps(pov_res)
        self.assertIn("ch01-the-iron-skiff.md", json_str)

if __name__ == "__main__":
    unittest.main()
