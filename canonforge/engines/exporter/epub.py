"""
CanonForge Exporter: Production EPUB 3.0 Generation Engine
--------------------------------------------------------------------------------
Compiles valid, standards-compliant EPUB 3.0 e-books with nav.xhtml,
NCX fallback, and custom typography for Apple Books, Kindle, and Kobo.
"""

import re
import html
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

from canonforge.engines.exporter.metadata import get_book_metadata, resolve_book_dir

EPUB_CONTAINER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>
"""

EPUB_CSS = """@charset "UTF-8";
body {
    font-family: Georgia, Garamond, "Times New Roman", serif;
    font-size: 1.05em;
    line-height: 1.7;
    margin: 5%;
    padding: 0;
    text-align: justify;
}
h1, h2, h3 {
    text-align: center;
    font-weight: normal;
    color: #8b3a0f;
    margin-top: 1.5em;
    margin-bottom: 0.8em;
}
.chapter-number {
    text-align: center;
    font-size: 0.8em;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #666;
    margin-bottom: 0.3em;
}
p {
    margin-top: 0;
    margin-bottom: 1.2em;
    text-indent: 1.5em;
}
p:first-of-type {
    text-indent: 0;
}
.scene-break {
    text-align: center;
    color: #8b3a0f;
    margin: 2em 0;
    font-size: 1.1em;
}
.titlepage {
    text-align: center;
    margin-top: 20%;
}
.titlepage h1 {
    font-size: 2.2em;
    margin-bottom: 0.2em;
}
.titlepage .author {
    font-size: 1.1em;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-top: 2em;
}
"""

def generate_epub(
    book_slug: str,
    chapters_data: List[Dict[str, Any]],
    out_dir: Optional[Path] = None,
    base_dir: Optional[Path] = None
) -> Path:
    """Natively compile valid, publication-grade EPUB 3.0 file."""
    book_path = resolve_book_dir(book_slug, base_dir)
    meta = get_book_metadata(book_path) if book_path else {
        "title": book_slug.replace("-", " ").title(),
        "author": "Author",
        "publisher": "CanonForge Publishing",
        "language": "en",
        "description": "Novel manuscript compiled by CanonForge.",
        "rights": "All rights reserved by the author."
    }

    target_dir = out_dir or (book_path.parent.parent / "_build" / "export" if book_path else Path.cwd() / "_build" / "export")
    target_dir.mkdir(parents=True, exist_ok=True)
    epub_path = target_dir / f"{book_slug}.epub"

    book_uuid = str(uuid.uuid4())
    mod_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    with zipfile.ZipFile(epub_path, "w") as zf:
        # 1. Mimetype must be uncompressed and first entry
        mimetype_info = zipfile.ZipInfo("mimetype")
        mimetype_info.compress_type = zipfile.ZIP_STORED
        zf.writestr(mimetype_info, b"application/epub+zip")

        # 2. META-INF/container.xml
        zf.writestr("META-INF/container.xml", EPUB_CONTAINER_XML)

        # 3. OEBPS/style.css
        zf.writestr("OEBPS/style.css", EPUB_CSS)

        # 4. Titlepage
        titlepage_html = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
<head>
    <title>{html.escape(meta.get("title", book_slug))}</title>
    <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
    <div class="titlepage">
        <h1>{html.escape(meta.get("title", book_slug))}</h1>
        <div class="author">by {html.escape(meta.get("author", "Author"))}</div>
    </div>
</body>
</html>"""
        zf.writestr("OEBPS/titlepage.xhtml", titlepage_html)

        # 5. Chapter XHTML files
        manifest_items = [
            '<item id="style" href="style.css" media-type="text/css"/>',
            '<item id="titlepage" href="titlepage.xhtml" media-type="application/xhtml+xml"/>',
            '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
            '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
        ]
        spine_items = ['<itemref idref="titlepage"/>']
        nav_li_items = []
        ncx_nav_points = []

        for idx, ch in enumerate(chapters_data, 1):
            ch_filename = f"chapter_{idx:02d}.xhtml"
            ch_title = html.escape(ch.get("title", f"Chapter {idx}"))
            ch_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
<head>
    <title>{ch_title}</title>
    <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
    <div class="chapter-number">Chapter {idx}</div>
    <h2>{ch_title}</h2>
    {ch.get("html_body", "")}
</body>
</html>"""
            zf.writestr(f"OEBPS/{ch_filename}", ch_xhtml)

            item_id = f"chapter_{idx:02d}"
            manifest_items.append(f'<item id="{item_id}" href="{ch_filename}" media-type="application/xhtml+xml"/>')
            spine_items.append(f'<itemref idref="{item_id}"/>')
            nav_li_items.append(f'<li><a href="{ch_filename}">{ch_title}</a></li>')
            ncx_nav_points.append(f"""
        <navPoint id="navPoint-{idx+1}" playOrder="{idx+1}">
            <navLabel><text>{ch_title}</text></navLabel>
            <content src="{ch_filename}"/>
        </navPoint>""")

        # 6. nav.xhtml (EPUB 3 Nav)
        nav_html = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en">
<head><title>Table of Contents</title><link rel="stylesheet" type="text/css" href="style.css"/></head>
<body>
    <nav epub:type="toc" id="toc">
        <h1>Table of Contents</h1>
        <ol>
            {"".join(nav_li_items)}
        </ol>
    </nav>
</body>
</html>"""
        zf.writestr("OEBPS/nav.xhtml", nav_html)

        # 7. toc.ncx (EPUB 2 backward compatibility)
        toc_ncx = f"""<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head><meta name="dtb:uid" content="urn:uuid:{book_uuid}"/></head>
    <docTitle><text>{html.escape(meta.get("title", book_slug))}</text></docTitle>
    <navMap>
        {"".join(ncx_nav_points)}
    </navMap>
</ncx>"""
        zf.writestr("OEBPS/toc.ncx", toc_ncx)

        # 8. content.opf
        content_opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="3.0">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:identifier id="BookId">urn:uuid:{book_uuid}</dc:identifier>
        <dc:title>{html.escape(meta.get("title", book_slug))}</dc:title>
        <dc:creator>{html.escape(meta.get("author", "Author"))}</dc:creator>
        <dc:language>{meta.get("language", "en")}</dc:language>
        <meta property="dcterms:modified">{mod_time}</meta>
    </metadata>
    <manifest>
        {"".join(manifest_items)}
    </manifest>
    <spine toc="ncx">
        {"".join(spine_items)}
    </spine>
</package>"""
        zf.writestr("OEBPS/content.opf", content_opf)

    return epub_path
