"""
CanonForge Engine: Manuscript Pacing & Rhythm Analyzer (cf pacing)
--------------------------------------------------------------------------------
Deterministic calculation of narrative rhythm, dialogue-to-action ratios,
sentence variety cadence, and chapter word-count progression across books.
Strictly observational and non-destructive: zero automated prose alteration.
"""

import sys
import re
import json
import math
from pathlib import Path
from typing import Dict, List, Any, Optional

from canonforge.cli.groups import style
from canonforge.core.manifest import find_universe_root
from canonforge.core.resolver import resolve_chapter, get_all_chapters, get_active_draft

# Comprehensive dictionary of kinetic action and physical movement verbs
KINETIC_VERBS = {
    "struck", "strike", "strikes", "striking",
    "slammed", "slam", "slams", "slamming",
    "parried", "parry", "parries", "parrying",
    "lunged", "lunge", "lunges", "lunging",
    "shattered", "shatter", "shatters", "shattering",
    "leaped", "leapt", "leap", "leaps", "leaping",
    "severed", "sever", "severs", "severing",
    "swung", "swing", "swings", "swinging",
    "dragged", "drag", "drags", "dragging",
    "sprinted", "sprint", "sprints", "sprinting",
    "vaulted", "vault", "vaults", "vaulting",
    "collided", "collide", "collides", "colliding",
    "dodged", "dodge", "dodges", "dodging",
    "charged", "charge", "charges", "charging",
    "snapped", "snap", "snaps", "snapping",
    "stumbled", "stumble", "stumbles", "stumbling",
    "exploded", "explode", "explodes", "exploding",
    "plunged", "plunge", "plunges", "plunging",
    "twisted", "twist", "twists", "twisting",
    "wrenched", "wrench", "wrenches", "wrenching",
    "kicked", "kick", "kicks", "kicking",
    "dashed", "dash", "dashes", "dashing",
    "dropped", "drop", "drops", "dropping",
    "crawled", "crawl", "crawls", "crawling",
    "climbed", "climb", "climbs", "climbing",
    "heaved", "heave", "heaves", "heaving",
    "gripped", "grip", "grips", "gripping",
    "clutched", "clutch", "clutches", "clutching",
    "hurled", "hurl", "hurls", "hurling",
    "pushed", "push", "pushes", "pushing",
    "pulled", "pull", "pulls", "pulling",
    "tore", "tear", "tears", "tearing", "torn",
    "whipped", "whip", "whips", "whipping",
    "ducked", "duck", "ducks", "ducking",
    "rolled", "roll", "rolls", "rolling",
    "grappled", "grapple", "grapples", "grappling",
    "recoiled", "recoil", "recoils", "recoiling",
    "pierced", "pierce", "pierces", "piercing",
    "smashed", "smash", "smashes", "smashing",
    "bludgeoned", "sliced", "slice", "slices", "slicing",
    "gouged", "gouge", "gouges", "gouging",
    "battered", "batter", "batters", "battering",
    "cracked", "crack", "cracks", "cracking",
    "split", "splits", "splitting",
    "gasped", "staggered", "stagger", "staggers", "staggering"
}


def analyze_chapter_pacing(ch_path: Path) -> Dict[str, Any]:
    """Calculate deterministic pacing, dialogue/kinetic ratios, and cadence metrics for a single chapter."""
    raw_text = ch_path.read_text(encoding="utf-8")

    # Strip YAML frontmatter
    body = raw_text
    fm_match = re.match(r"^---\n(.*?)\n---\n", raw_text, re.DOTALL)
    if fm_match:
        body = raw_text[fm_match.end():]

    # Clean markdown formatting for accurate word count
    clean_body = re.sub(r"^#+\s+.*$", "", body, flags=re.MULTILINE)
    clean_body = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", clean_body)

    all_words = re.findall(r"\b[\w'-]+\b", clean_body)
    total_words = max(1, len(all_words))

    # 1. Dialogue Extraction
    dialogue_blocks = re.findall(r'["“«][^"”»]+["”»]', clean_body)
    dialogue_words_list = []
    for block in dialogue_blocks:
        dialogue_words_list.extend(re.findall(r"\b[\w'-]+\b", block))
    dialogue_word_count = len(dialogue_words_list)
    dialogue_pct = round((dialogue_word_count / total_words) * 100, 1)

    # 2. Kinetic Action Density
    lower_tokens = [w.lower() for w in all_words]
    kinetic_hits = [w for w in lower_tokens if w in KINETIC_VERBS]
    kinetic_count = len(kinetic_hits)
    kinetic_pct = round((kinetic_count / total_words) * 100, 2)

    # 3. Narrative & Exposition
    narrative_word_count = max(0, total_words - dialogue_word_count)
    narrative_pct = round((narrative_word_count / total_words) * 100, 1)

    # 4. Cadence & Sentence Variety
    raw_sentences = [
        s.strip() for s in re.split(r"[.!?]+(?:\s+|\n+|$)", clean_body)
        if len(re.findall(r"\b[\w'-]+\b", s)) >= 2
    ]
    sentence_count = max(1, len(raw_sentences))
    sent_lengths = [len(re.findall(r"\b[\w'-]+\b", s)) for s in raw_sentences]

    avg_sent_len = round(sum(sent_lengths) / sentence_count, 1)
    if sentence_count > 1:
        variance = sum((x - avg_sent_len) ** 2 for x in sent_lengths) / (sentence_count - 1)
        stdev_sent_len = round(math.sqrt(variance), 1)
    else:
        stdev_sent_len = 0.0

    min_sent_len = min(sent_lengths) if sent_lengths else 0
    max_sent_len = max(sent_lengths) if sent_lengths else 0

    # Cadence Classification
    if stdev_sent_len >= 8.0:
        cadence_type = "Dynamic Flow"
    elif avg_sent_len < 10.0 and stdev_sent_len < 4.0:
        cadence_type = "Staccato Monotone"
    elif avg_sent_len > 24.0 and stdev_sent_len < 6.0:
        cadence_type = "Expository Run-on"
    else:
        cadence_type = "Steady Cadence"

    # Rhythm Archetype
    if dialogue_pct >= 50.0:
        archetype = "Dialogue-Driven"
    elif kinetic_pct >= 2.5:
        archetype = "High-Kinetic Action"
    elif narrative_pct >= 75.0 and kinetic_pct < 1.0:
        archetype = "Introspective / Worldbuilding"
    else:
        archetype = "Balanced Narrative"

    # Potential Pacing Friction Warnings
    warnings = []
    if dialogue_pct > 65.0:
        warnings.append("High dialogue concentration (>65%): risk of Talking Heads syndrome. Verify physical grounding.")
    if narrative_pct > 82.0 and kinetic_pct < 0.8:
        warnings.append("Exposition swamp (>82% narrative, <0.8% kinetic): consider breaking with spoken line or tactical movement.")
    if cadence_type == "Staccato Monotone":
        warnings.append("Sentence variety low (short staccato rhythm): consider blending compound clauses.")
    elif cadence_type == "Expository Run-on":
        warnings.append("Sentence variety low (long complex clauses): consider punching up with short sensory impacts.")

    return {
        "file": ch_path.name,
        "path": str(ch_path.resolve()),
        "word_count": total_words,
        "dialogue_words": dialogue_word_count,
        "dialogue_pct": dialogue_pct,
        "kinetic_words": kinetic_count,
        "kinetic_pct": kinetic_pct,
        "narrative_words": narrative_word_count,
        "narrative_pct": narrative_pct,
        "sentence_count": sentence_count,
        "avg_sentence_len": avg_sent_len,
        "stdev_sentence_len": stdev_sent_len,
        "min_sentence_len": min_sent_len,
        "max_sentence_len": max_sent_len,
        "cadence_type": cadence_type,
        "archetype": archetype,
        "warnings": warnings
    }


def _make_bar(value: float, max_val: float, width: int = 16) -> str:
    """Render a Unicode horizontal progress bar."""
    if max_val <= 0:
        return "░" * width
    fill = int(round((min(value, max_val) / max_val) * width))
    return "█" * fill + "░" * (width - fill)


def render_chapter_pacing_card(metrics: Dict[str, Any]):
    """Render a clean author-facing pacing telemetry card."""
    f_name = metrics["file"]
    w_count = metrics["word_count"]
    dlg_pct = metrics["dialogue_pct"]
    act_pct = metrics["kinetic_pct"]
    nar_pct = metrics["narrative_pct"]
    arch = metrics["archetype"]
    cadence = metrics["cadence_type"]

    print(f"\n{style('╭─ [PACING & RHYTHM REPORT]', 'cyan')} {style(f_name, 'bold')} ({w_count:,} words)")
    print(f"{style('│', 'cyan')} Archetype    : {style(arch, 'yellow')} | Cadence: {style(cadence, 'green')}")
    print(f"{style('│', 'cyan')}")
    
    # Ratios with visual bars
    bar_dlg = _make_bar(dlg_pct, 100.0, 14)
    bar_act = _make_bar(act_pct, 5.0, 14)  # 5% kinetic is peak action
    bar_nar = _make_bar(nar_pct, 100.0, 14)

    print(f"{style('│', 'cyan')} {style('Dialogue  :', 'bold')} {bar_dlg} {dlg_pct:5.1f}% ({metrics['dialogue_words']:,} words)")
    print(f"{style('│', 'cyan')} {style('Kinetic   :', 'bold')} {bar_act} {act_pct:5.2f}% ({metrics['kinetic_words']} action verbs)")
    print(f"{style('│', 'cyan')} {style('Narrative :', 'bold')} {bar_nar} {nar_pct:5.1f}% ({metrics['narrative_words']:,} words)")
    print(f"{style('│', 'cyan')}")
    print(f"{style('│', 'cyan')} {style('Cadence   :', 'bold')} {metrics['sentence_count']} sentences | avg: {metrics['avg_sentence_len']} w/s | ±{metrics['stdev_sentence_len']} dev (min: {metrics['min_sentence_len']}, max: {metrics['max_sentence_len']})")

    if metrics["warnings"]:
        print(f"{style('│', 'cyan')}")
        print(f"{style('│', 'cyan')} {style('⚡ Pacing Friction Warnings:', 'yellow')}")
        for w in metrics["warnings"]:
            print(f"{style('│', 'cyan')}   • {w}")
    else:
        print(f"{style('│', 'cyan')}   ✓ Healthy balance across dialogue, motion, and descriptive breathers.")

    print(f"{style('╰────────────────────────────────────────────────────────────────────────────', 'cyan')}\n")


def render_book_pacing_overview(chapters: List[Path]) -> List[Dict[str, Any]]:
    """Render a visual rhythm curve across all chapters in a book volume."""
    records = [analyze_chapter_pacing(ch) for ch in chapters]
    if not records:
        print("No chapters found.")
        return []

    total_book_words = sum(r["word_count"] for r in records)
    avg_words = total_book_words / len(records)
    max_words = max(r["word_count"] for r in records)

    print(f"\n{style('================================================================================', 'cyan')}")
    print(f"{style('CANONFORGE PACING & RHYTHM AUDIT (BOOK VOLUME OVERVIEW)', 'bold')}")
    print(f"Chapters: {len(records)} | Total Words: {total_book_words:,} | Avg/Chapter: {int(avg_words):,} words")
    print(f"{style('================================================================================', 'cyan')}")
    print(f"{style('CH #', 'bold'):<5} {style('FILENAME', 'bold'):<30} {style('WORDS', 'bold'):<8} {style('DISTRIBUTION', 'bold'):<12} {style('DLG %', 'bold'):<8} {style('ACT %', 'bold'):<8} {style('ARCHETYPE', 'bold')}")
    print(f"{'─'*5} {'─'*30} {'─'*8} {'─'*12} {'─'*8} {'─'*8} {'─'*20}")

    for idx, r in enumerate(records, start=1):
        bar = _make_bar(r["word_count"], max_words, 10)
        arch_col = "green" if "Balanced" in r["archetype"] else ("yellow" if "Dialogue" in r["archetype"] else "cyan")
        print(f"{idx:<5} {r['file'][:30]:<30} {r['word_count']:<8} {bar} {r['dialogue_pct']:>5.1f}%  {r['kinetic_pct']:>5.2f}%  {style(r['archetype'], arch_col)}")

    # Volume-level insights
    outliers = [r for r in records if r["word_count"] > avg_words * 1.8 or r["word_count"] < avg_words * 0.4]
    print(f"{'─'*94}")
    if outliers:
        print(f"{style('⚡ Volume Pacing Outliers:', 'yellow')}")
        for o in outliers:
            print(f"  • {o['file']} ({o['word_count']:,} words) deviates significantly from the book average of {int(avg_words):,} words.")
    else:
        print(f"✓ Chapter length distribution is harmoniously calibrated across the volume.")
    print(f"{style('================================================================================', 'cyan')}\n")

    return records


def main():
    """CLI Entrypoint for 'cf pacing'."""
    u_dir = find_universe_root()
    target_arg = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else None
    
    # Check flags
    as_json = "--json" in sys.argv or "--format=json" in sys.argv
    export_idx = -1
    export_path = None
    for flag in ("--export", "-e"):
        if flag in sys.argv:
            export_idx = sys.argv.index(flag)
            if export_idx + 1 < len(sys.argv):
                export_path = Path(sys.argv[export_idx + 1])

    # Case 1: Specific target chapter or shorthand given
    if target_arg:
        resolved = resolve_chapter(target_arg, universe_dir=u_dir)
        if resolved and resolved.is_file():
            metrics = analyze_chapter_pacing(resolved)
            if as_json:
                print(json.dumps(metrics, indent=2))
            else:
                render_chapter_pacing_card(metrics)
            if export_path:
                export_path.write_text(json.dumps(metrics, indent=2) if as_json else str(metrics), encoding="utf-8")
                print(f"Exported pacing metrics to: {export_path}")
            return

    # Case 2: Book filter or multi-chapter volume
    book_arg = None
    for i, arg in enumerate(sys.argv):
        if arg in ("--book", "-b") and i + 1 < len(sys.argv):
            book_arg = sys.argv[i + 1]
            break

    chapters = get_all_chapters(u_dir, book_filter=book_arg)
    if not chapters:
        # Fallback to active draft
        active = get_active_draft(u_dir)
        if active:
            metrics = analyze_chapter_pacing(active)
            if as_json:
                print(json.dumps(metrics, indent=2))
            else:
                render_chapter_pacing_card(metrics)
            return
        print("❌ No chapter or manuscript files located for pacing audit.")
        sys.exit(1)

    # If only 1 chapter resolved, render card; if multiple, render book overview
    if len(chapters) == 1:
        metrics = analyze_chapter_pacing(chapters[0])
        if as_json:
            print(json.dumps(metrics, indent=2))
        else:
            render_chapter_pacing_card(metrics)
    else:
        results = render_book_pacing_overview(chapters)
        if as_json:
            print(json.dumps(results, indent=2))
        if export_path:
            export_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
            print(f"Exported book pacing report to: {export_path}")


if __name__ == "__main__":
    main()
