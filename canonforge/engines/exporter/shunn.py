"""
CanonForge Exporter: Shunn Manuscript Formatter
--------------------------------------------------------------------------------
Generates industry-standard manuscript format (William Shunn standard)
for agent and editor submissions:
- Standard Courier font, fixed-width spacing
- Scene breaks indicated by centered '#'
- Word count rounded to nearest 100/1000
"""

import re
from pathlib import Path
from typing import Dict, List, Any, Optional

def format_shunn_manuscript(
    book_title: str,
    author_name: str,
    chapters_data: List[Dict[str, Any]],
    contact_info: Optional[str] = None
) -> str:
    """Format full manuscript text into William Shunn traditional submission format."""
    total_words = sum(c.get("word_count", 0) for c in chapters_data)
    # Industry standard rounded word count
    rounded_words = round(total_words, -2) if total_words < 10000 else round(total_words, -3)

    contact = contact_info or f"{author_name}\n[Author Contact Email]\n[Author Agency / Phone]"
    lines = [
        contact.strip(),
        f"{' ' * 45}About {rounded_words:,} words\n\n\n\n",
        f"{' ' * 20}{book_title.upper()}",
        f"{' ' * 24}by {author_name}\n\n\n",
    ]

    for ch in chapters_data:
        title = ch.get("title", "Chapter")
        body = ch.get("raw_body") or ch.get("html_body", "")

        # Clean tags from body
        clean_text = re.sub(r"<[^>]+>", " ", body)
        clean_text = re.sub(r"<!--\s*pov:[^>]+-->", "", clean_text)
        # Convert scene breaks (*** or ---) to centered #
        clean_text = re.sub(r"^\s*(\*\*\*|---|___|\*\s+\*\s+\*)\s*$", "\n\n        #\n\n", clean_text, flags=re.MULTILINE)

        lines.append(f"\n\n\n        {title.upper()}\n\n")

        # Format paragraphs with standard 4-space indent
        for para in clean_text.split("\n\n"):
            p = para.strip()
            if not p:
                continue
            if p == "#":
                lines.append("        #\n\n")
            elif p.startswith("# "):
                continue # Skip redundant markdown header
            else:
                lines.append(f"    {p}\n\n")

    lines.append("\n\n        ### END ###\n")
    return "".join(lines)

def export_shunn_file(
    out_path: Path,
    book_title: str,
    author_name: str,
    chapters_data: List[Dict[str, Any]]
) -> Path:
    """Write Shunn manuscript to text file."""
    content = format_shunn_manuscript(book_title, author_name, chapters_data)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    return out_path
