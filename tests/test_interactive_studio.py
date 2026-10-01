"""
Tests for CanonForge Universal Interactive Studio & Verifier Engine.
"""

import unittest
import tempfile
from pathlib import Path

from canonforge.engines import interactive
from canonforge.engines import verifier


class TestInteractiveStudio(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        # Create minimal mock universe
        (self.root / "universe.yaml").write_text("""universe_id: "test-verse"
display_name: "Test Universe"
studio_presets:
  default_book: "book-test"
  default_player: "hero_char"
  default_monster: "monster_beast"
  default_origin: "Old Port"
  default_destination: "Crystal Peak"
""", encoding="utf-8")

        ms_dir = self.root / "manuscript" / "test-series" / "book-test" / "chapters"
        ms_dir.mkdir(parents=True, exist_ok=True)
        (ms_dir / "ch01-the-start.md").write_text("""---
okf_version: "0.3"
type: "Chapter Entity"
book: "book-test"
chapter: 1
act: 1
title: "The Start"
pov: "hero_char"
setting: "Old Port"
timeline: "100 AO"
characters: ["hero_char"]
---
The adventure begins at Old Port.
""", encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_detect_universe_context_with_presets(self):
        ctx = interactive.detect_universe_context(self.root)
        self.assertEqual(ctx["display_name"], "Test Universe")
        self.assertEqual(ctx["active_book"], "book-test")
        self.assertEqual(ctx["default_player"], "hero_char")
        self.assertEqual(ctx["default_monster"], "monster_beast")
        self.assertEqual(ctx["default_origin"], "Old Port")
        self.assertEqual(ctx["default_destination"], "Crystal Peak")
        self.assertEqual(ctx["active_chapter"], "ch01-the-start")

    def test_02_detect_universe_context_dynamic_inference(self):
        # Create second bare universe without presets
        bare_root = self.root / "bare-verse"
        bare_root.mkdir()
        (bare_root / "universe.yaml").write_text("""universe_id: "bare-verse"
display_name: "Bare Universe"
""", encoding="utf-8")

        ms_dir = bare_root / "manuscript" / "saga-one" / "book-alpha" / "chapters"
        ms_dir.mkdir(parents=True, exist_ok=True)
        (ms_dir / "ch01-alpha.md").write_text("""---
okf_version: "0.3"
type: "Chapter Entity"
book: "book-alpha"
chapter: 1
act: 1
title: "Alpha"
pov: "Scout Elena"
setting: "Sky Harbor, Platform 4"
timeline: "500 AO"
characters: ["Scout Elena"]
---
Sky Harbor was shrouded in fog.
""", encoding="utf-8")

        ctx = interactive.detect_universe_context(bare_root)
        self.assertEqual(ctx["display_name"], "Bare Universe")
        self.assertEqual(ctx["active_book"], "book-alpha")
        self.assertEqual(ctx["default_player"], "Scout Elena")
        self.assertEqual(ctx["default_origin"], "Sky Harbor")
        self.assertEqual(ctx["active_chapter"], "ch01-alpha")

    def test_03_render_menu_buffer(self):
        ctx = interactive.detect_universe_context(self.root)
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            interactive.render_menu(ctx)

        output = buf.getvalue()
        self.assertIn("TEST UNIVERSE STUDIO: MASTER DEVELOPER DASHBOARD", output)
        self.assertIn("[1]  🚀 Master Novel Pipeline", output)
        self.assertIn("[10] 🧪 Master CI/CD Test Suite", output)
        self.assertIn("[18] 📑 Chapter Appearance & Citation Index", output)
        self.assertIn("[0]  🚪 Exit Studio", output)
