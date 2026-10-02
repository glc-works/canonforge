"""
CanonForge Engine: Live In-Flight Companion Daemon (cf watch)
--------------------------------------------------------------------------------
Monitors the active chapter draft in real time. On file save (Cmd+S / Ctrl+S),
recomputes session word delta, sensory radar saturation, dialogue/kinetic ratios,
and anti-slop heads-up alerts in a split terminal pane without leaving the editor.
Strictly observational: zero automated alteration of manuscript prose.
"""

import os
import sys
import time
import re
from pathlib import Path
from typing import Dict, Any, Optional

from canonforge.cli.groups import style
from canonforge.core.manifest import find_universe_root
from canonforge.core.resolver import resolve_chapter, get_active_draft
from canonforge.engines.pacing import analyze_chapter_pacing, _make_bar
from canonforge.engines.metrics.calculator import compute_metrics
from canonforge.cli.audit_cmd import run_chapter_audit


def _clear_terminal():
    """Clear terminal screen and position cursor at top left."""
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def _format_sensory_bar(count: int, max_val: int = 15) -> str:
    """Render a compact 10-char bar for sensory radar."""
    return _make_bar(count, max_val, width=10)


def render_watch_hud(
    ch_path: Path,
    session_start_time: float,
    start_words: int,
    last_update_str: str,
    update_elapsed_ms: float
):
    """Render the full author cockpit HUD."""
    _clear_terminal()

    # Compute live metrics
    pacing = analyze_chapter_pacing(ch_path)
    metrics = compute_metrics(ch_path)
    diagnostics = run_chapter_audit(ch_path)

    current_words = pacing["word_count"]
    words_delta = current_words - start_words
    elapsed_sec = max(1.0, time.time() - session_start_time)
    elapsed_min = round(elapsed_sec / 60.0, 1)
    
    # Calculate writing velocity (words per hour)
    wph = int((words_delta / elapsed_sec) * 3600) if words_delta > 0 else 0

    delta_str = f"+{words_delta:,} words" if words_delta >= 0 else f"{words_delta:,} words"
    delta_styled = style(delta_str, "green" if words_delta >= 0 else "yellow")

    # Header
    print(f"{style('╔════════════════════════════════════════════════════════════════════════════╗', 'cyan')}")
    print(f"{style('║', 'cyan')}  {style('CANONFORGE COMPANION HUD', 'bold')} • {style(ch_path.name, 'yellow'):<43} {style('║', 'cyan')}")
    print(f"{style('║', 'cyan')}  {style('● LIVE WATCHING', 'green')} [Saved: {last_update_str}] ({update_elapsed_ms:.1f}ms)              {style('║', 'cyan')}")
    print(f"{style('╚════════════════════════════════════════════════════════════════════════════╝', 'cyan')}")

    # Telemetry Bar
    print(f" {style('Session :', 'bold')} {elapsed_min} mins  │  {style('Delta :', 'bold')} {delta_styled}  │  {style('Velocity :', 'bold')} {wph} wph")
    print(f" {style('Length  :', 'bold')} {current_words:,} words ({pacing['sentence_count']} sent)  │  {style('Reading Time :', 'bold')} ~{metrics['reading_time_min']} mins")
    print(f"{style('─'*78, 'gray')}")

    # Pacing & Rhythm HUD
    dlg_bar = _make_bar(pacing["dialogue_pct"], 100.0, 12)
    act_bar = _make_bar(pacing["kinetic_pct"], 5.0, 12)
    nar_bar = _make_bar(pacing["narrative_pct"], 100.0, 12)

    print(f" {style('[PACING RHYTHM]', 'bold')}  Archetype: {style(pacing['archetype'], 'yellow')}  |  Cadence: {style(pacing['cadence_type'], 'cyan')}")
    print(f"   • Dialogue  : {dlg_bar} {pacing['dialogue_pct']:>5.1f}% ({pacing['dialogue_words']:,} w)")
    print(f"   • Kinetic   : {act_bar} {pacing['kinetic_pct']:>5.2f}% ({pacing['kinetic_words']} action verbs)")
    print(f"   • Narrative : {nar_bar} {pacing['narrative_pct']:>5.1f}% ({pacing['narrative_words']:,} w)")
    print(f"{style('─'*78, 'gray')}")

    # Sensory Radar HUD
    sen_counts = metrics["sensory_summary"]["counts"]
    pass_pct = metrics["sensory_summary"]["pass_pct"]
    imm_score = metrics["immersion_score"]

    score_col = "green" if imm_score >= 80 else ("yellow" if imm_score >= 65 else "red")
    print(f" {style('[SENSORY RADAR]', 'bold')}  Immersion Score: {style(f'{imm_score:.1f}/100', score_col)}  |  4-Sense Windows: {pass_pct}%")

    sight_cnt = sen_counts.get("Sight", sen_counts.get("sight", 0))
    sound_cnt = sen_counts.get("Sound", sen_counts.get("sound", 0))
    smell_cnt = sen_counts.get("Smell", sen_counts.get("smell", 0))
    taste_cnt = sen_counts.get("Taste", sen_counts.get("taste", 0))
    touch_cnt = sen_counts.get("Touch", sen_counts.get("touch", 0))

    sight_bar = _format_sensory_bar(sight_cnt)
    sound_bar = _format_sensory_bar(sound_cnt)
    smell_bar = _format_sensory_bar(smell_cnt)
    taste_bar = _format_sensory_bar(taste_cnt)
    touch_bar = _format_sensory_bar(touch_cnt)

    print(f"   👁  Sight  {sight_bar} {sight_cnt:>3} hits    │   👃 Smell  {smell_bar} {smell_cnt:>3} hits")
    print(f"   👂 Sound  {sound_bar} {sound_cnt:>3} hits    │   👅 Taste  {taste_bar} {taste_cnt:>3} hits")
    print(f"   ✋ Touch  {touch_bar} {touch_cnt:>3} hits    │   Sensory Density: {metrics['sensory_summary']['density_pct']}%")
    print(f"{style('─'*78, 'gray')}")

    # Real-Time Heads-Up Diagnostics
    print(f" {style('[HEADS-UP LITERARY LINTER]', 'bold')}")
    if not diagnostics:
        print(f"   {style('✓ Zero POV telepathy leaks, AI clichés, or schema warnings in draft.', 'green')}")
    else:
        # Show top 4 diagnostic items
        shown = diagnostics[:4]
        for d in shown:
            sev = d.get("severity", "info")
            badge = style("WARN", "yellow") if sev == "warning" else (style("ERR", "red") if sev == "error" else style("INFO", "cyan"))
            msg = d.get("message", "")
            line = d.get("line", 1)
            print(f"   • [{badge}] L{line}: {msg[:64]}")
        if len(diagnostics) > 4:
            print(f"     {style(f'... and {len(diagnostics) - 4} more notes (run \"cf audit\" for full detail)', 'gray')}")

    print(f"{style('═'*78, 'cyan')}")
    print(f" {style('Press Ctrl+C to pause companion watch.', 'gray')}")


def watch_chapter(ch_path: Path):
    """Run interactive polling watch loop on the target chapter file."""
    if not ch_path.exists():
        print(f"❌ Error: Chapter file does not exist: {ch_path}")
        sys.exit(1)

    session_start_time = time.time()
    
    # Read initial state
    try:
        p_init = analyze_chapter_pacing(ch_path)
        start_words = p_init["word_count"]
    except Exception:
        start_words = 0

    last_mtime = ch_path.stat().st_mtime
    update_str = time.strftime("%H:%M:%S")
    
    # First HUD render
    render_watch_hud(ch_path, session_start_time, start_words, update_str, 0.0)

    try:
        while True:
            time.sleep(0.8)
            try:
                curr_mtime = ch_path.stat().st_mtime
            except FileNotFoundError:
                continue

            if curr_mtime != last_mtime:
                last_mtime = curr_mtime
                t0 = time.perf_counter()
                update_str = time.strftime("%H:%M:%S")
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                render_watch_hud(ch_path, session_start_time, start_words, update_str, elapsed_ms)

    except KeyboardInterrupt:
        _clear_terminal()
        elapsed_sec = max(1.0, time.time() - session_start_time)
        try:
            final_pacing = analyze_chapter_pacing(ch_path)
            net_delta = final_pacing["word_count"] - start_words
        except Exception:
            net_delta = 0

        print(f"\n{style('✨ CanonForge Watch Session Completed!', 'green')}")
        print(f"• Active Draft : {style(ch_path.name, 'bold')}")
        print(f"• Elapsed Time : {round(elapsed_sec / 60.0, 1)} minutes")
        print(f"• Net Delta    : {style(f'{net_delta:+,} words', 'bold')}")
        print("Ready for next writing sprint!\n")


def main():
    """CLI Entrypoint for 'cf watch'."""
    u_dir = find_universe_root()
    target_arg = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else None

    if target_arg:
        resolved = resolve_chapter(target_arg, universe_dir=u_dir)
        if resolved:
            watch_chapter(resolved)
            return
        print(f"❌ Error: Chapter matching '{target_arg}' not found.")
        sys.exit(1)

    active = get_active_draft(u_dir)
    if active:
        watch_chapter(active)
        return

    print("❌ Error: No active draft found. Please specify a chapter to watch:")
    print("   cf watch <shorthand|filename>")
    sys.exit(1)


if __name__ == "__main__":
    main()
