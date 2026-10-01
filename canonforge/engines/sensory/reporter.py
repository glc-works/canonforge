"""
reporter.py

Terminal reporting and ANSI radar visualization for 5-senses audits.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

SENSE_ICONS = {
    "Sight": "👁️ ",
    "Sound": "👂",
    "Smell": "👃",
    "Taste": "👅",
    "Touch": "✋"
}

def print_sensory_report(filename: str, res: Dict[str, Any], comp: Dict[str, Any], show_windows: bool = False, harvest_words: Optional[List[Tuple[str, int]]] = None):
    score = res["immersion_score"]
    color = "🟢" if score >= 85 else ("🟡" if score >= 70 else "🔴")

    print("\n" + "=" * 80)
    print(f"COMPOSABLE 5-SENSES & ATMOSPHERIC RADAR: {filename}")
    print("=" * 80)
    print(f"• Active Profiles (OR)     : {', '.join(res['profiles'])}")
    print(f"• Total Words              : {res['total_words']:,} words")
    print(f"• Total Sensory Hits       : {res['total_sensory_hits']:,} ({res['sensory_density_pct']}% of text)")
    print(f"• Three-Sense Pass Rate    : {res['four_sense_compliance_pct']}% of scene windows")
    print("-" * 80)
    print(f"🏆 SENSORY IMMERSION SCORE : {color} {score}/100")
    print("-" * 80)

    # 1. 5-Senses Distribution
    print("\nSENSORY SPECTRUM DISTRIBUTION:")
    total_hits = max(1, res["total_sensory_hits"])
    for sense_name in ["Sight", "Sound", "Smell", "Taste", "Touch"]:
        cnt = res["sense_counts"][sense_name]
        pct = (cnt / total_hits) * 100
        bar_len = int(round((pct / 100) * 26))
        bar = "█" * bar_len + "░" * (26 - bar_len)
        icon = SENSE_ICONS[sense_name]
        samples = ", ".join(res["sense_samples"][sense_name][:4])
        print(f"  {icon} {sense_name:<6}: [{bar}] {pct:>5.1f}% ({cnt:>3}) | e.g. {samples}")

    # 2. Thematic Mixin Blend
    if res["theme_counts"]:
        print("\nTHEMATIC ATMOSPHERE MIXIN BLEND:")
        active_themes = sorted([(th, c) for th, c in res["theme_counts"].items() if c > 0], key=lambda x: -x[1])
        if active_themes:
            for th, cnt in active_themes:
                bar_len = min(20, cnt * 2)
                bar = "█" * bar_len
                print(f"  🌀 {th:<22}: {bar} ({cnt} hits)")
        else:
            print("  (No specific thematic flavor tags matched in active chapter)")

    # 3. Atmospheric Vectors
    print("\nATMOSPHERIC VECTORS (POLARITY BALANCE):")
    t_v = res["thermal_vector"]
    tac_v = res["tactile_vector"]
    print(f"  🔥 Thermal Vector: Warm: {t_v['warm']:<3} | Cold: {t_v['cold']:<3}")
    print(f"  🧱 Tactile Vector: Hard: {tac_v['hard']:<3} | Soft: {tac_v['soft']:<3}")

    # 4. Windows breakdown
    if show_windows:
        print("\n500-WORD SCENE SEQUENCE WINDOWS (FOUR-SENSE RULE):")
        for win in res["windows"]:
            idx = win["window_index"]
            w_start = win["word_start"]
            w_end = win["word_end"]
            count = win["active_count"]
            status = "✅ PASS" if win["compliant"] else "❌ DEFICIT"
            senses_str = ", ".join(win["active_senses"]) if win["active_senses"] else "None"
            missing_str = ", ".join(win["missing_senses"]) if win["missing_senses"] else "None"
            themes_str = f" [Themes: {', '.join(win['active_themes'])}]" if win.get("active_themes") else ""
            print(f"  [{idx:02d}] Words {w_start:>4}–{w_end:<4}: {status} ({count}/5 senses activated){themes_str}")
            print(f"       Active : {senses_str}")
            if not win["compliant"]:
                print(f"       Missing: \033[93m{missing_str}\033[0m")
            print()

    # 5. Forbidden words
    if res["forbidden_hits"]:
        print(f"\n⚠️  FORBIDDEN FILTER WORDS DETECTED: {len(res['forbidden_hits'])}")
        print(f"   Hits: {', '.join(res['forbidden_hits'])}")

    print("\n" + "=" * 80 + "\n")
