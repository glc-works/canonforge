"""
Tests for CanonForge Character Dossier, Obsidian Canvas Generator, and Chronology Query Engines.
"""

import unittest
import tempfile
import json
from pathlib import Path

from canonforge.engines import profile
from canonforge.engines import canvas
from canonforge.engines import timeline_query


class TestDossierCanvasTimeline(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        # Create minimal universe structure
        (self.root / "universe.yaml").write_text("slug: test-universe\ntitle: Test Universe\n", encoding="utf-8")
        data_dir = self.root / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        wiki_chars = self.root / "wiki" / "characters"
        wiki_chars.mkdir(parents=True, exist_ok=True)

        # 1. Sample character
        char_content = """---
title: "Captain Kira"
id: "char_captain_kira"
house: "Vanguard"
faction: "Alliance"
role: "Sky Captain"
birth_date: "1020-04-12"
biological_state: "Pure Flesh"
entity_status: "Active"
invariants:
  valid_eye_colors: ["cerulean blue", "blue"]
  forbidden_eye_colors: ["red", "amber"]
  signature_weapon: "Aether Saber"
---

# Captain Kira

Captain Kira is the daring commander of the Sky-Vessel Horizon.
She led the vanguard during the Siege of the Sunken Isles.
"""
        (wiki_chars / "captain-kira.md").write_text(char_content, encoding="utf-8")

        # 2. Sample timeline data
        timeline_data = {
            "calendar": {
                "system": "Solar Epoch",
                "crossing_anchor_year": 1050
            },
            "eras": [
                {"id": "era_0", "name": "Era I: Ancient Dawn", "range": "1000 - 1030"},
                {"id": "era_1", "name": "Era II: The Great Skywar", "range": "1030 - 1060"},
            ],
            "events": [
                {
                    "id": "evt_skywar_start",
                    "year_ao": 1035,
                    "title": "Outbreak of the Skywar",
                    "era": "era_1",
                    "region": "Upper Stratum",
                    "faction": "Alliance",
                    "characters": ["Captain Kira"],
                    "logline": "Hostilities flare across the northern boundary clouds."
                }
            ]
        }
        (data_dir / "timeline.json").write_text(json.dumps(timeline_data, indent=2), encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_character_profile_engine(self):
        res = profile.build_profile("Captain Kira", universe_dir=self.root, target_year=1055)
        self.assertIsNotNone(res)
        wiki = res["wiki"]
        self.assertEqual(wiki["title"], "Captain Kira")
        self.assertEqual(wiki["house"], "Vanguard")
        self.assertEqual(wiki["faction"], "Alliance")
        self.assertIn("cerulean blue", wiki["invariants"]["valid_eye_colors"])

        # Age calculation test
        age_str = profile.calculate_age(wiki["birth_date"], target_year=1055)
        self.assertIn("35 winters old", age_str)

    def test_canvas_generator_engine(self):
        out_canvas = self.root / "canvases" / "Test-Chronology.canvas"
        result_path = canvas.build_chronology_canvas(self.root, output_path=out_canvas)
        self.assertTrue(result_path.exists())

        canvas_data = json.loads(result_path.read_text(encoding="utf-8"))
        self.assertIn("nodes", canvas_data)
        self.assertIn("edges", canvas_data)
        self.assertGreater(len(canvas_data["nodes"]), 0)

        # Check era header
        header_texts = [n["text"] for n in canvas_data["nodes"] if n["id"].startswith("hdr_")]
        self.assertTrue(any("ANCIENT DAWN" in t for t in header_texts))

    def test_timeline_query_engine(self):
        timeline, chars = timeline_query.load_universe_chronology(self.root)
        self.assertEqual(len(chars), 1)
        self.assertEqual(chars[0]["name"], "Captain Kira")

        # Query year 1035
        year_res = timeline_query.query_year(1035, timeline, chars)
        self.assertEqual(year_res["year"], 1035)
        self.assertEqual(len(year_res["events"]), 1)
        self.assertEqual(year_res["events"][0]["title"], "Outbreak of the Skywar")
        self.assertEqual(len(year_res["living"]), 1)
        self.assertEqual(year_res["living"][0]["age"], 15)

        # Query character milestones
        char_res = timeline_query.query_character("Kira", timeline, chars)
        self.assertIsNotNone(char_res)
        self.assertEqual(char_res["character"]["name"], "Captain Kira")
        self.assertGreater(len(char_res["milestones"]), 0)


if __name__ == "__main__":
    unittest.main()
