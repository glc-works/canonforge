"""
CanonForge Exporter: Chapter-Level Serial Exporter
--------------------------------------------------------------------------------
Exports individual chapters for web serialization platforms:
Substack, Patreon, Royal Road, Wattpad, and clean Markdown/HTML.
Strips YAML frontmatter and formats scene breaks cleanly.
"""

import re
import html
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

def parse_chapter_content(text: str) -> Tuple[Dict[str, Any], str]:
    """Extract YAML frontmatter and clean body prose."""
    meta: Dict[str, Any] = {}
    body = text

    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            raw_fm = parts[1]
            body = parts[2].strip()
            if HAS_YAML:
                try:
                    meta = yaml.safe_load(raw_fm) or {}
                except Exception:
                    pass
            if not meta:
                # Regex fallback
                for line in raw_fm.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        meta[k.strip()] = v.strip().strip('"').strip("'")

    # Strip HTML comment tags like <!-- pov: Protagonist -->
    body = re.sub(r"<!--\s*pov:[^>]+-->", "", body)
    return meta, body

def format_chapter_for_platform(
    title: str,
    body: str,
    meta: Dict[str, Any],
    platform: str = "clean",
    author_note: Optional[str] = None
) -> str:
    """Format body text according to target serialization platform."""
    # Standardize scene breaks
    body = re.sub(r"^\s*(\*\*\*|---|___|\*\s+\*\s+\*)\s*$", "\n* * *\n", body, flags=re.MULTILINE)

    if platform == "substack":
        header = f"# {title}\n\n"
        if meta.get("pov"):
            header += f"*{meta.get('pov')} | {meta.get('setting', '')}*\n\n---\n\n"
        footer = ""
        if author_note:
            footer = f"\n\n---\n\n*Author's Note:*\n{author_note}\n"
        return header + body + footer

    elif platform == "royalroad":
        header = f"# {title}\n\n"
        footer = ""
        if author_note:
            footer = f"\n\n* * *\n\n**Author Note:**\n{author_note}\n"
        return header + body + footer

    elif platform == "patreon":
        header = f"# [EARLY ACCESS] {title}\n\n"
        if meta.get("pov"):
            header += f"**POV:** {meta.get('pov')} | **Timeline:** {meta.get('timeline', '')}\n\n"
        footer = ""
        if author_note:
            footer = f"\n\n---\n\n**Patron Note:**\n{author_note}\n"
        return header + body + footer

    # clean / default
    if not body.startswith("# "):
        return f"# {title}\n\n" + body
    return body

def export_chapter_file(
    chapter_path: Path,
    platform: str = "clean",
    output_format: str = "markdown",
    out_dir: Optional[Path] = None,
    author_note: Optional[str] = None
) -> Dict[str, Any]:
    """Export an individual chapter to clean Markdown or standalone HTML."""
    if not chapter_path.is_file():
        raise FileNotFoundError(f"Chapter file not found: {chapter_path}")

    raw_text = chapter_path.read_text(encoding="utf-8")
    meta, body = parse_chapter_content(raw_text)

    title = meta.get("title")
    if not title:
        m = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        title = m.group(1).strip() if m else chapter_path.stem.replace("-", " ").title()

    formatted_text = format_chapter_for_platform(
        title=title,
        body=body,
        meta=meta,
        platform=platform,
        author_note=author_note
    )

    word_count = len(formatted_text.split())
    reading_time_min = max(1, round(word_count / 225))

    target_dir = out_dir or (chapter_path.parent.parent / "_build" / "export" / "chapters")
    target_dir.mkdir(parents=True, exist_ok=True)

    slug = chapter_path.stem
    if output_format == "html":
        # Convert markdown paragraphs to HTML
        paras = formatted_text.split("\n\n")
        html_paras = []
        for p in paras:
            p_strip = p.strip()
            if not p_strip:
                continue
            if p_strip.startswith("# "):
                html_paras.append(f"<h1>{html.escape(p_strip[2:])}</h1>")
            elif p_strip == "* * *" or p_strip == "---":
                html_paras.append('<hr class="scene-break" />')
            elif p_strip.startswith("*") and p_strip.endswith("*"):
                html_paras.append(f"<p class=\"italic\">{html.escape(p_strip.strip('*'))}</p>")
            else:
                html_paras.append(f"<p>{html.escape(p_strip)}</p>")

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>
body {{ max-width: 680px; margin: 40px auto; padding: 0 20px; font-family: Georgia, serif; line-height: 1.6; color: #222; }}
h1 {{ font-size: 1.8em; margin-bottom: 0.3em; }}
p {{ margin-bottom: 1.2em; text-indent: 1.5em; }}
p:first-of-type {{ text-indent: 0; }}
hr.scene-break {{ border: 0; text-align: center; margin: 2em 0; }}
hr.scene-break:before {{ content: "* * *"; color: #888; font-size: 1.2em; }}
</style>
</head>
<body>
{"".join(html_paras)}
</body>
</html>"""
        out_file = target_dir / f"{slug}.html"
        out_file.write_text(html_content, encoding="utf-8")
    else:
        out_file = target_dir / f"{slug}.md"
        out_file.write_text(formatted_text, encoding="utf-8")

    return {
        "title": title,
        "filename": chapter_path.name,
        "word_count": word_count,
        "reading_time_min": reading_time_min,
        "platform": platform,
        "format": output_format,
        "out_file": out_file
    }
