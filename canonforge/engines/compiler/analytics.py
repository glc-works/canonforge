"""
Novel manuscript prose telemetry and analytics reporter.
"""
from typing import Dict, List, Any

try:
    from tabulate import tabulate
except ImportError:
    tabulate = lambda rows, headers, tablefmt: "\n".join(str(r) for r in rows)

WORDS_PER_MINUTE = 220

def generate_analytics_report(chapters: List[Dict[str, Any]], book_name: str):
    """Print storytelling pacing analytics and character presence index."""
    total_words = sum(c["actual_words"] for c in chapters)
    total_target = sum(c["target_words"] for c in chapters)
    total_reading_time = total_words / WORDS_PER_MINUTE

    print("\n" + "=" * 80)
    print(f"CANONFORGE NOVEL MANUSCRIPT REPORT: {book_name.upper()}")
    print("=" * 80)
    print(f"• Total Chapters Drafted : {len(chapters)}")
    print(f"• Total Manuscript Words : {total_words:,} words (Target: {total_target:,} words)")
    print(f"• Estimated Reading Time : {total_reading_time:.1f} minutes (~{total_reading_time/60:.2f} hours)")
    print("-" * 80)

    table_data = []
    for c in chapters:
        read_time = f"{c['actual_words'] / WORDS_PER_MINUTE:.1f}m"
        target = c.get("target_words", 3000)
        progress = f"{(c['actual_words'] / target) * 100:.0f}%" if target else "N/A"
        ch_tag = f"Act {c.get('act_num', '?')}.Ch {c.get('chapter_num', '?')}"
        table_data.append([
            ch_tag,
            c['title'][:28],
            c['pov'][:18],
            f"{c['actual_words']:,} w",
            read_time,
            progress
        ])

    print(tabulate(
        table_data,
        headers=["Placement", "Title", "POV", "Words", "Read Time", "Target %"],
        tablefmt="simple"
    ))

    # Character presence index
    char_appearances: Dict[str, List[str]] = {}
    for c in chapters:
        chap_label = f"Ch {c.get('chapter_num', '?')}"
        for cp in c["characters_present"]:
            char_appearances.setdefault(cp, []).append(chap_label)

    if char_appearances:
        print("\n" + "-" * 80)
        print("CHARACTER PRESENCE INDEX:")
        for char, appears in sorted(char_appearances.items(), key=lambda x: -len(x[1])):
            print(f"  • {char:<30} : {len(appears)} chapter(s) -> {', '.join(appears)}")
    print("=" * 80 + "\n")

import zipfile
import html

