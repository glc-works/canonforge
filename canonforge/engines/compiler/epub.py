"""
EPUB packaging and OEBPS manifest generation.
"""
import re
import html
import zipfile
from pathlib import Path
from typing import Dict, List, Any, Optional

from canonforge.core.manifest import find_universe_root

UNIVERSE_DIR = find_universe_root()

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
    series_name = manifest.get("series", "Original Saga") if manifest else "Original Saga"
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
        cand = UNIVERSE_DIR / manifest.get("cover_image")
        if cand.exists():
            cover_image_path = cand
    if not cover_image_path:
        if "book-1" in book_dir_name:
            cand = UNIVERSE_DIR / "wiki/assets/cover.jpg"
            if cand.exists():
                cover_image_path = cand
        elif "book-2" in book_dir_name:
            cand = UNIVERSE_DIR / "wiki/assets/concepts/war/colossus/colossus-concept1.jpg"
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
        <dc:identifier id="pub-id">urn:uuid:canonforge-{book_dir_name}</dc:identifier>
        <dc:title>{html.escape(book_title)}</dc:title>
        <dc:creator>CanonForge Studio</dc:creator>
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

