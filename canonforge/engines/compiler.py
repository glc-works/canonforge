#!/usr/bin/env python3
"""
compile_novel.py

Authoritative Novel Manuscript Compiler & Analytics Engine for Convergence.
Supports modern decoupled TOC/Manifest architecture (`toc.yaml`),
automatic dynamic chapter & act numbering, clean reader compilation,
and storytelling pacing analytics.

Usage:
    uv run scripts/compile_novel.py
    uv run scripts/compile_novel.py --book "book-1-the-stone-child"
    uv run scripts/compile_novel.py --book "book-2-the-iron-pilgrimage"
    uv run scripts/compile_novel.py --all
"""

import os
import sys
import re
import yaml
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
from tabulate import tabulate

SCRIPT_DIR = Path(__file__).resolve().parent
CONVERGENCE_DIR = SCRIPT_DIR.parent
MANUSCRIPT_DIR = CONVERGENCE_DIR / "manuscript"
COMPILED_DIR = MANUSCRIPT_DIR / "_build" / "compiled"
COMPILED_DIR.mkdir(parents=True, exist_ok=True)

WORDS_PER_MINUTE = 225

def parse_scene_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """Parse scene file, extracting frontmatter metadata and body prose."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return None

    meta: Dict[str, Any] = {}
    body = content

    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if fm_match:
        yaml_text = fm_match.group(1)
        body = content[fm_match.end():]
        try:
            meta = yaml.safe_load(yaml_text) or {}
        except Exception:
            # Fallback regex parser if PyYAML fails on complex frontmatter
            meta = {}

    clean_body = re.sub(r"^>.*$\n?", "", body, flags=re.MULTILINE)
    clean_body = re.sub(r"^---\s*$\n?", "", clean_body, flags=re.MULTILINE)
    # Strip any hardcoded markdown headings at the top like '# ACT 1' or '## Chapter 1: Foo'
    clean_body = re.sub(r"^#\s+ACT\s+.*$\n?", "", clean_body, flags=re.MULTILINE)
    clean_body = re.sub(r"^##\s+Chapter\s+.*$\n?", "", clean_body, flags=re.MULTILINE)
    clean_body = re.sub(r"^\*POV:.*$\n?", "", clean_body, flags=re.MULTILINE)
    clean_body = clean_body.strip()

    # Extract and resolve Obsidian/Wiki cross-links:
    # During writing: [[Kazan-the-Faithful-Blade|Kazan]] or [[Orynite]] links to lore
    # During compilation: resolves to clean text ("Kazan", "Orynite")
    auto_entities = []
    wikilink_matches = re.findall(r"\[\[(.*?)\]\]", body)
    for wl in wikilink_matches:
        target = wl.split("|")[0].split("#")[0].strip()
        if target:
            entity_label = target.replace("-", " ").title()
            if entity_label not in auto_entities:
                auto_entities.append(entity_label)

    def resolve_wikilink(match):
        full = match.group(1)
        if "|" in full:
            return full.split("|", 1)[1]
        target = full.split("#", 1)[0].strip()
        return target.replace("-", " ")

    clean_body = re.sub(r"\[\[(.*?)\]\]", resolve_wikilink, clean_body)

    words = len(re.findall(r"\b\w+\b", clean_body))

    title = meta.get("title")
    if not title:
        raw_name = file_path.stem
        # Remove any leading chXX- if present
        raw_name = re.sub(r"^ch\d+-", "", raw_name)
        title = raw_name.replace("-", " ").title()
    else:
        title = str(title).strip('"').strip("'")

    pov = meta.get("pov") or meta.get("pov_character") or "Omniscient"
    setting = meta.get("location") or meta.get("setting") or "Unknown"
    timeline = meta.get("timeline") or meta.get("timeline_anchor") or "Unknown"
    characters = meta.get("characters") or meta.get("characters_present") or []
    if not isinstance(characters, list):
        characters = [characters]
    for ent in auto_entities:
        if ent not in characters:
            characters.append(ent)

    return {
        "path": file_path,
        "filename": file_path.name,
        "title": title,
        "pov": pov,
        "setting": setting,
        "timeline_anchor": timeline,
        "characters_present": characters,
        "target_words": meta.get("target_words", 3000),
        "actual_words": words,
        "raw_body": body,
        "clean_body": clean_body,
        "meta": meta
    }

def load_from_manifest(book_dir: Path) -> Optional[Dict[str, Any]]:
    """Load and assemble chapters dynamically from toc.yaml."""
    toc_path = book_dir / "toc.yaml"
    if not toc_path.exists():
        return None

    try:
        toc = yaml.safe_load(toc_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error parsing {toc_path}: {e}", file=sys.stderr)
        return None

    chapters_dir = book_dir / "chapters"
    assembled_chapters = []
    global_ch_num = 1

    acts = toc.get("acts", [])
    for act_idx, act_info in enumerate(acts, 1):
        act_num = act_info.get("act", act_idx)
        act_title = act_info.get("title", f"Act {act_num}")
        ch_files = act_info.get("chapters", [])

        for ch_file in ch_files:
            file_path = chapters_dir / ch_file
            if not file_path.exists():
                # Check directly in book_dir for backwards compatibility
                file_path = book_dir / ch_file
            
            if not file_path.exists():
                print(f"⚠️ Warning: Chapter file not found: {ch_file} in {book_dir}", file=sys.stderr)
                continue

            parsed = parse_scene_file(file_path)
            if parsed:
                parsed["act_num"] = act_num
                parsed["act_title"] = act_title
                parsed["chapter_num"] = global_ch_num
                assembled_chapters.append(parsed)
                global_ch_num += 1

    return {
        "manifest": toc,
        "chapters": assembled_chapters
    }

def discover_chapters_fallback(book_dir: Path) -> List[Dict[str, Any]]:
    """Fallback scanner if toc.yaml is absent."""
    chapters = []
    for f in sorted(book_dir.rglob("*.md")):
        if "archive" in f.parts:
            continue
        if f.name.lower() in ["readme.md", "index.md", "summary.md", "master-outline.md", "outline.md"]:
            continue
        parsed = parse_scene_file(f)
        if parsed:
            chapters.append(parsed)
    return chapters

def compile_manuscript(chapters: List[Dict[str, Any]], manifest: Optional[Dict[str, Any]], book_name: str, output_path: Path):
    """Compile clean combined markdown manuscript with dynamic numbering."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    book_title = manifest.get("title", book_name.replace("-", " ").title()) if manifest else book_name.replace("-", " ").title()
    series_name = manifest.get("series", "The Convergence Saga") if manifest else "The Convergence Saga"
    edition_label = manifest.get("edition", "Studio Authoritative Edition") if manifest else "Studio Authoritative Edition"

    epigraph_text = None
    epigraph_author = None
    if manifest and "epigraph" in manifest:
        epigraph_text = manifest["epigraph"].get("text")
        epigraph_author = manifest["epigraph"].get("attribution")

    lines = [
        f"% {book_title}",
        f"% {series_name}",
        f"% {edition_label}",
        "",
        "---",
        ""
    ]

    if epigraph_text:
        lines.append(f"> *\"{epigraph_text}\"*")
        if epigraph_author:
            lines.append(f"> — {epigraph_author}")
        lines.append("")
        lines.append("---")
        lines.append("")

    current_act = None

    for ch in chapters:
        act_num = ch.get("act_num")
        act_title = ch.get("act_title")
        if act_num and act_num != current_act:
            current_act = act_num
            lines.append(f"\n\n# ACT {act_num}: {act_title.upper()}\n\n")

        ch_num = ch.get("chapter_num", "")
        ch_label = f"Chapter {ch_num}: " if ch_num else ""
        lines.append(f"## {ch_label}{ch['title']}\n")
        lines.append(f"*POV: {ch['pov']} · Location: {ch['setting']} · Timeline: {ch['timeline_anchor']}*\n\n")
        lines.append(ch["clean_body"])
        lines.append("\n\n* * *\n\n")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"📖 Compiled clean reader manuscript ({len(chapters)} chapters) to: {output_path}")

def generate_analytics_report(chapters: List[Dict[str, Any]], book_name: str):
    """Print storytelling pacing analytics and character presence index."""
    total_words = sum(c["actual_words"] for c in chapters)
    total_target = sum(c["target_words"] for c in chapters)
    total_reading_time = total_words / WORDS_PER_MINUTE

    print("\n" + "=" * 80)
    print(f"CONVERGENCE NOVEL MANUSCRIPT REPORT: {book_name.upper()}")
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

def markdown_to_html_body(md_text: str) -> str:
    """Lightweight converter from novel markdown to clean, standard XHTML."""
    lines = md_text.split("\n")
    html_paragraphs = []
    current_p = []

    def flush_p():
        if current_p:
            text = " ".join(current_p).strip()
            if text:
                # Basic typography & markdown spans
                text = html.escape(text)
                # Bold / Italic
                text = re.sub(r"\*\*\*(.*?)\*\*\*", r"<strong><em>\1</em></strong>", text)
                text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)
                text = re.sub(r"\*(.*?)\*", r"<em>\1</em>", text)
                text = re.sub(r"`(.*?)`", r"<code>\1</code>", text)
                html_paragraphs.append(f"<p>{text}</p>")
            current_p.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_p()
        elif stripped.startswith(">"):
            flush_p()
            quote_text = html.escape(stripped.lstrip("> ").strip())
            quote_text = re.sub(r"\*(.*?)\*", r"<em>\1</em>", quote_text)
            html_paragraphs.append(f"<blockquote><p>{quote_text}</p></blockquote>")
        elif stripped in ("---", "***", "* * *"):
            flush_p()
            html_paragraphs.append("<div class='scene-break'>* * *</div>")
        elif stripped.startswith("###"):
            flush_p()
            html_paragraphs.append(f"<h3>{html.escape(stripped.lstrip('#').strip())}</h3>")
        elif stripped.startswith("##"):
            flush_p()
            html_paragraphs.append(f"<h2>{html.escape(stripped.lstrip('#').strip())}</h2>")
        else:
            current_p.append(stripped)

    flush_p()
    return "\n".join(html_paragraphs)

def build_epub(chapters: List[Dict[str, Any]], manifest: Optional[Dict[str, Any]], book_dir_name: str, out_epub_path: Path):
    """Build a standard, clean EPUB 3 archive without external dependencies."""
    book_title = manifest.get("title", book_dir_name.replace("-", " ").title()) if manifest else book_dir_name.title()
    series_name = manifest.get("series", "The Convergence Saga") if manifest else "The Convergence Saga"
    epigraph = manifest.get("epigraph", {}) if manifest else {}

    out_epub_path.parent.mkdir(parents=True, exist_ok=True)

    css_content = """
    @charset "utf-8";
    body {
        font-family: Georgia, "Merriweather", "Times New Roman", serif;
        margin: 5% 8%;
        line-height: 1.6;
        color: #1a1a1a;
    }
    h1, h2, h3 {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        text-align: center;
        font-weight: 600;
        margin-top: 1.5em;
        margin-bottom: 0.8em;
    }
    h1.book-title {
        font-size: 2.2em;
        margin-top: 25%;
        margin-bottom: 0.2em;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    p.series-subtitle {
        text-align: center;
        font-style: italic;
        color: #555;
        margin-bottom: 20%;
    }
    p {
        margin: 0;
        text-indent: 1.5em;
        text-align: justify;
    }
    p:first-of-type, div.scene-break + p, h1 + p, h2 + p, h3 + p {
        text-indent: 0;
    }
    div.scene-break {
        text-align: center;
        margin: 1.8em 0;
        letter-spacing: 0.5em;
        color: #777;
    }
    blockquote {
        margin: 1.5em 2em;
        font-style: italic;
        color: #444;
    }
    .chapter-header {
        text-align: center;
        margin-bottom: 2em;
    }
    .chapter-number {
        font-size: 0.9em;
        text-transform: uppercase;
        letter-spacing: 0.2em;
        color: #777;
    }
    .chapter-title {
        font-size: 1.6em;
        margin-top: 0.3em;
    }
    .epigraph-box {
        margin-top: 30%;
        text-align: center;
        font-style: italic;
        padding: 0 10%;
    }
    .epigraph-attr {
        margin-top: 1em;
        font-size: 0.9em;
        text-align: right;
        font-style: normal;
        color: #666;
    }
    """

    manifest_items = [
        '<item id="styles" href="styles.css" media-type="text/css"/>',
        '<item id="title" href="title.xhtml" media-type="application/xhtml+xml"/>',
    ]
    spine_items = [
        '<itemref idref="title"/>',
    ]

    # Resolve Cover Art Image
    cover_image_path = None
    if manifest and manifest.get("cover_image"):
        cand = CONVERGENCE_DIR / manifest.get("cover_image")
        if cand.exists():
            cover_image_path = cand
    if not cover_image_path:
        if "book-1" in book_dir_name:
            cand = CONVERGENCE_DIR / "wiki/assets/concepts/characters/cairn/cairn-concept1.jpg"
            if cand.exists():
                cover_image_path = cand
        elif "book-2" in book_dir_name:
            cand = CONVERGENCE_DIR / "wiki/assets/concepts/war/colossus/colossus-concept1.jpg"
            if cand.exists():
                cover_image_path = cand

    with zipfile.ZipFile(out_epub_path, "w") as zf:
        # 1. mimetype (MUST be first and uncompressed)
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)

        # 2. META-INF/container.xml
        container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>"""
        zf.writestr("META-INF/container.xml", container_xml, compress_type=zipfile.ZIP_DEFLATED)

        # 3. OEBPS/styles.css
        zf.writestr("OEBPS/styles.css", css_content, compress_type=zipfile.ZIP_DEFLATED)

        # Cover Image & Page (if resolved)
        if cover_image_path and cover_image_path.exists():
            zf.write(cover_image_path, "OEBPS/cover.jpg")
            manifest_items.insert(0, '<item id="cover-image" href="cover.jpg" media-type="image/jpeg" properties="cover-image"/>')
            manifest_items.insert(1, '<item id="cover-page" href="cover.xhtml" media-type="application/xhtml+xml"/>')
            spine_items.insert(0, '<itemref idref="cover-page"/>')

            cover_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>Cover</title>
    <style type="text/css">
        body {{ margin: 0; padding: 0; text-align: center; background-color: #0b0c10; }}
        img {{ max-width: 100%; max-height: 100vh; height: auto; display: block; margin: 0 auto; }}
    </style>
</head>
<body>
    <div>
        <img src="cover.jpg" alt="{html.escape(book_title)} Cover" />
    </div>
</body>
</html>"""
            zf.writestr("OEBPS/cover.xhtml", cover_xhtml, compress_type=zipfile.ZIP_DEFLATED)

        # 4. Title page
        title_html = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>{html.escape(book_title)}</title>
    <link rel="stylesheet" type="text/css" href="styles.css" />
</head>
<body>
    <h1 class="book-title">{html.escape(book_title)}</h1>
    <p class="series-subtitle">{html.escape(series_name)}</p>
</body>
</html>"""
        zf.writestr("OEBPS/title.xhtml", title_html, compress_type=zipfile.ZIP_DEFLATED)

        # 5. Epigraph (if present)
        if epigraph and epigraph.get("text"):
            epi_html = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Epigraph</title>
    <link rel="stylesheet" type="text/css" href="styles.css" />
</head>
<body>
    <div class="epigraph-box">
        <p>"{html.escape(epigraph.get('text', ''))}"</p>
        <p class="epigraph-attr">— {html.escape(epigraph.get('attribution', ''))}</p>
    </div>
</body>
</html>"""
            zf.writestr("OEBPS/epigraph.xhtml", epi_html, compress_type=zipfile.ZIP_DEFLATED)
            manifest_items.append('<item id="epigraph" href="epigraph.xhtml" media-type="application/xhtml+xml"/>')
            spine_items.append('<itemref idref="epigraph"/>')

        # 6. Chapters
        nav_points = []
        for idx, ch in enumerate(chapters, start=1):
            ch_id = f"chapter_{idx}"
            ch_num_label = f"Chapter {ch.get('chapter_num', idx)}"
            ch_title = ch.get("title", f"Chapter {idx}")
            body_html = markdown_to_html_body(ch.get("clean_body", ""))

            ch_file_content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{html.escape(ch_title)}</title>
    <link rel="stylesheet" type="text/css" href="styles.css" />
</head>
<body>
    <div class="chapter-header">
        <div class="chapter-number">{html.escape(ch_num_label)}</div>
        <h2 class="chapter-title">{html.escape(ch_title)}</h2>
    </div>
    {body_html}
</body>
</html>"""
            zf.writestr(f"OEBPS/{ch_id}.xhtml", ch_file_content, compress_type=zipfile.ZIP_DEFLATED)
            manifest_items.append(f'<item id="{ch_id}" href="{ch_id}.xhtml" media-type="application/xhtml+xml"/>')
            spine_items.append(f'<itemref idref="{ch_id}"/>')
            nav_points.append(f'''
            <li><a href="{ch_id}.xhtml">{html.escape(ch_num_label)}: {html.escape(ch_title)}</a></li>''')

        # 7. Navigation document (nav.xhtml for EPUB 3)
        nav_html = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>Table of Contents</title>
    <link rel="stylesheet" type="text/css" href="styles.css" />
</head>
<body>
    <nav epub:type="toc" id="toc">
        <h1>Table of Contents</h1>
        <ol>
            {''.join(nav_points)}
        </ol>
    </nav>
</body>
</html>"""
        zf.writestr("OEBPS/nav.xhtml", nav_html, compress_type=zipfile.ZIP_DEFLATED)
        manifest_items.append('<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>')

        # 8. Package file (content.opf)
        content_opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:identifier id="pub-id">urn:uuid:convergence-{book_dir_name}</dc:identifier>
        <dc:title>{html.escape(book_title)}</dc:title>
        <dc:creator>Convergence Studio</dc:creator>
        <dc:language>en</dc:language>
        <meta property="dcterms:modified">2026-09-28T00:00:00Z</meta>
    </metadata>
    <manifest>
        {''.join(manifest_items)}
    </manifest>
    <spine>
        {''.join(spine_items)}
    </spine>
</package>"""
        zf.writestr("OEBPS/content.opf", content_opf, compress_type=zipfile.ZIP_DEFLATED)

    print(f"📖 EPUB generated successfully: {out_epub_path} ({out_epub_path.stat().st_size:,} bytes)")

def resolve_book_dir(query: str) -> Optional[Path]:
    p = MANUSCRIPT_DIR / query
    if p.is_dir() and (p / "chapters").exists():
        return p

    for b_dir in MANUSCRIPT_DIR.glob(f"*/{query}"):
        if b_dir.is_dir() and (b_dir / "chapters").exists():
            return b_dir

    try:
        from book_navigator import BOOK_REGISTRY
        q_clean = query.lower().strip()
        for reg in BOOK_REGISTRY:
            if q_clean == reg["id"].lower() or q_clean in [a.lower() for a in reg["aliases"]] or str(reg["num"]) == q_clean:
                cand = MANUSCRIPT_DIR / reg["id"]
                if cand.is_dir():
                    return cand
    except Exception:
        pass

    for toc in MANUSCRIPT_DIR.glob("*/*/toc.yaml"):
        b_cand = toc.parent
        if query.lower() in b_cand.name.lower() or query.lower() in b_cand.parent.name.lower():
            return b_cand
    return None

def process_book(book_target: str, output_override: Optional[str] = None, export_epub: bool = False):
    book_dir = resolve_book_dir(book_target)
    if not book_dir or not book_dir.exists():
        print(f"Error: Book '{book_target}' not found in {MANUSCRIPT_DIR}.", file=sys.stderr)
        return False

    manifest_data = load_from_manifest(book_dir)
    if manifest_data:
        chapters = manifest_data["chapters"]
        manifest = manifest_data["manifest"]
    else:
        chapters = discover_chapters_fallback(book_dir)
        manifest = None

    if not chapters:
        print(f"No chapters found in {book_dir}.")
        return False

    # Determine canonical export slug from manifest or directory
    export_slug = book_dir.name
    if manifest:
        export_slug = manifest.get("book_id") or manifest.get("book") or manifest.get("slug")
        if not export_slug and "title" in manifest:
            export_slug = re.sub(r"[^a-zA-Z0-9]+", "-", manifest["title"]).strip("-").lower()
    if not export_slug:
        export_slug = f"{book_dir.parent.name}-{book_dir.name}"

    out_path = Path(output_override) if output_override else COMPILED_DIR / f"{export_slug}.md"
    compile_manuscript(chapters, manifest, export_slug, out_path)
    generate_analytics_report(chapters, export_slug)

    if export_epub:
        epub_path = COMPILED_DIR / f"{export_slug}.epub"
        build_epub(chapters, manifest, export_slug, epub_path)

    return True

def main():
    parser = argparse.ArgumentParser(description="Convergence Novel Manuscript Compiler")
    parser.add_argument("--book", default="stone-child/book-01", help="Book identifier, path, or number")
    parser.add_argument("--output", help="Custom output path for compiled markdown")
    parser.add_argument("--all", action="store_true", help="Compile all books found in manuscript/")
    parser.add_argument("--epub", action="store_true", help="Generate KDP-compliant EPUB 3 e-book")

    args = parser.parse_args()

    if args.all:
        books_found = []
        for toc in sorted(MANUSCRIPT_DIR.glob("*/*/toc.yaml")):
            books_found.append(toc.parent)
        for b_dir in books_found:
            process_book(str(b_dir.relative_to(MANUSCRIPT_DIR)), export_epub=args.epub)
    else:
        process_book(args.book, args.output, export_epub=args.epub)

if __name__ == "__main__":
    main()

