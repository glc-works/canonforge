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

    def test_chapter_and_book_export(self):
        from canonforge.engines.exporter.chapter_export import export_chapter_file
        from canonforge.engines.exporter.cli import export_single_book
        from canonforge.engines.exporter.series_export import export_series_omnibus

        ch_path = REPO_ROOT / "examples" / "aetheria" / "manuscript" / "skies-of-iron" / "book-01" / "chapters" / "ch01-the-iron-skiff.md"
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_p = Path(tmp_dir)
            # 1. Chapter export
            res_ch = export_chapter_file(ch_path, platform="substack", out_dir=tmp_p)
            self.assertTrue(res_ch["out_file"].is_file())
            self.assertIn("The Iron Skiff", res_ch["out_file"].read_text(encoding="utf-8"))

            # 2. Book export
            ms_dir = REPO_ROOT / "examples" / "aetheria" / "manuscript"
            ok = export_single_book("skies-of-iron/book-01", output_format="all", base_dir=ms_dir)
            self.assertTrue(ok)

            # 3. Series Omnibus export
            res_series = export_series_omnibus("skies-of-iron", base_dir=REPO_ROOT / "examples" / "aetheria")
            self.assertEqual(res_series["total_chapters"], 2)
            self.assertTrue(res_series["markdown_file"].is_file())

    def test_asset_scaffolding(self):
        from canonforge.engines.assets import create_asset_entry
        with tempfile.TemporaryDirectory() as tmp_dir:
            res = create_asset_entry("test-map", asset_type="map", prompt="Fantasy map", base_dir=Path(tmp_dir))
            self.assertTrue(res["sidecar_file"].is_file())
            self.assertIn("Fantasy map", res["sidecar_file"].read_text(encoding="utf-8"))

    def test_obsidian_plugin_install(self):
        from canonforge.engines.obsidian import install_obsidian_plugin
        with tempfile.TemporaryDirectory() as tmp_dir:
            p_dir = install_obsidian_plugin(Path(tmp_dir))
            self.assertTrue((p_dir / "manifest.json").is_file())
    def test_search_and_update(self):
        from canonforge.engines.search import search_entities
        from canonforge.engines.updater import update_entity

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_p = Path(tmp_dir)
            wiki_dir = tmp_p / "wiki" / "characters"
            wiki_dir.mkdir(parents=True)
            char_file = wiki_dir / "captain-elena.md"
            char_file.write_text(
                "---\nname: Captain Elena\nrole: Airship Pilot\nstatus: Active\ntags:\n  - hero\n---\n\nCaptain Elena navigates the cloud-sea.\n",
                encoding="utf-8"
            )

            # 1. Test search
            results, suggestions = search_entities("Elena", root_dir=tmp_p)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["name"], "Captain Elena")

            # 2. Test fuzzy typo search
            results_typo, suggestions_typo = search_entities("Elana", root_dir=tmp_p)
            self.assertIn("Captain Elena", suggestions_typo)

            # 3. Test update
            updated = update_entity(
                "Captain Elena",
                updates={"role": "Fleet Admiral", "status": "Veteran"},
                add_tags=["legend"],
                auto_confirm=True,
                no_sync=True,
                root_dir=tmp_p,
            )
            self.assertTrue(updated)

            # Verify file contents
            content = char_file.read_text(encoding="utf-8")
            self.assertIn("role: Fleet Admiral", content)
            self.assertIn("status: Veteran", content)
            self.assertIn("- legend", content)
            self.assertIn("Captain Elena navigates the cloud-sea.", content)

    def test_scanner_and_linker(self):
        from canonforge.engines.scanner import run_entity_scan
        from canonforge.engines.linker import link_chapter_text

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_p = Path(tmp_dir)
            wiki_dir = tmp_p / "wiki" / "characters"
            wiki_dir.mkdir(parents=True)
            (wiki_dir / "captain-elena.md").write_text("---\ntitle: Captain Elena\n---\n", encoding="utf-8")

            ms_dir = tmp_p / "manuscript" / "series-01" / "book-01" / "chapters"
            ms_dir.mkdir(parents=True)
            ch_file = ms_dir / "ch01.md"
            ch_file.write_text("Captain Elena boarded the airship. She met [[Unknown Lord]].", encoding="utf-8")

            # 1. Test scan
            res = run_entity_scan(root_dir=tmp_p, scaffold=True)
            self.assertIn("Unknown Lord", res["unregistered"])
            self.assertEqual(len(res["scaffolded"]), 1)

            # 2. Test linker
            linked, count = link_chapter_text("Captain Elena shouted orders to Elena.", [("Captain Elena", "captain-elena", "Captain Elena")])
            self.assertEqual(count, 1)
            self.assertIn("[[captain-elena|Captain Elena]]", linked)

    def test_git_hook(self):
        from canonforge.engines.hooks import install_git_hook, uninstall_git_hook, check_hook_status

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_p = Path(tmp_dir)
            (tmp_p / ".git").mkdir()

            h_file = install_git_hook(tmp_p)
            self.assertTrue(h_file.is_file())
            self.assertTrue(check_hook_status(tmp_p))

            uninstalled = uninstall_git_hook(tmp_p)
            self.assertTrue(uninstalled)
    def test_pacing_engine(self):
        from canonforge.engines.pacing import analyze_chapter_pacing
        ch_path = REPO_ROOT / "examples" / "aetheria" / "manuscript" / "skies-of-iron" / "book-01" / "chapters" / "ch01-the-iron-skiff.md"
        res = analyze_chapter_pacing(ch_path)
        self.assertEqual(res["file"], "ch01-the-iron-skiff.md")
        self.assertGreater(res["word_count"], 300)
        self.assertIn("dialogue_pct", res)
        self.assertIn("kinetic_pct", res)
        self.assertIn("narrative_pct", res)
        self.assertIn("archetype", res)
        self.assertIn("cadence_type", res)

    def test_watch_engine_hud(self):
        from canonforge.engines.watch import render_watch_hud
        ch_path = REPO_ROOT / "examples" / "aetheria" / "manuscript" / "skies-of-iron" / "book-01" / "chapters" / "ch01-the-iron-skiff.md"
        captured = io.StringIO()
        sys.stdout = captured
        try:
            render_watch_hud(ch_path, session_start_time=100.0, start_words=300, last_update_str="12:00:00", update_elapsed_ms=5.0)
        finally:
            sys.stdout = sys.__stdout__
        out = captured.getvalue()
        self.assertIn("CANONFORGE COMPANION HUD", out)
        self.assertIn("[PACING RHYTHM]", out)
        self.assertIn("[SENSORY RADAR]", out)
        self.assertIn("[HEADS-UP LITERARY LINTER]", out)

    def test_entities_and_alias_resolver(self):
        from canonforge.core.entities import build_universe_entity_index, resolve_wikilink, validate_chapter_wikilinks
        aetheria_dir = REPO_ROOT / "examples" / "aetheria"
        index = build_universe_entity_index(aetheria_dir)

        # 1. Resolve exact title / stem
        valid, ent, sugg = resolve_wikilink("captain-orlov", index)
        self.assertTrue(valid)
        self.assertIsNotNone(ent)

        # 2. Resolve name or title
        valid, ent, sugg = resolve_wikilink("Captain Orlov", index)
        self.assertTrue(valid)

        # 3. Resolve chapter
        valid, ent, sugg = resolve_wikilink("ch01-the-iron-skiff", index)
        self.assertTrue(valid)

        # 4. Resolve typo with fuzzy match
        valid, ent, sugg = resolve_wikilink("captain-orlovv", index)
        self.assertFalse(valid)
        self.assertIn("captain-orlov", sugg.lower())

        # 5. Validate markdown with broken link
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test_ch.md"
            test_file.write_text("She looked at [[captain-orlov|Orlov]] and [[captain-orlovv|the pilot]].", encoding="utf-8")
            diags = validate_chapter_wikilinks(test_file, index=index)
            self.assertEqual(len(diags), 1)
            self.assertEqual(diags[0]["code"], "LNK001")
            self.assertIn("captain-orlov", diags[0]["suggestion"])

if __name__ == "__main__":
    unittest.main()

