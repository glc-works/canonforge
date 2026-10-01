"""
Production EPUB3 generation engine with nav.xhtml and cover support.
"""
import re
import html
import zipfile
from pathlib import Path
from typing import Dict, List, Any

PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent
MANUSCRIPT_DIR = PACKAGE_ROOT / "manuscript"
WIKI_DIR = PACKAGE_ROOT / "wiki"

def generate_epub(book_slug: str, chapters_data: List[Dict[str, Any]]) -> Path:
    """Natively compile valid, publication-grade EPUB 3.0 file."""
    meta = get_book_metadata(MANUSCRIPT_DIR / book_slug)

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    epub_path = EXPORTS_DIR / f"{book_slug}.epub"
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
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en">
<head>
    <title>{html.escape(meta["title"])}</title>
    <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
    <div class="titlepage">
        <h1>{html.escape(meta["title"])}</h1>
        <div class="subtitle">{html.escape(meta["subtitle"])}</div>
        <div class="author">{html.escape(meta["author"])}</div>
        <p style="margin-top: 3em; font-size: 0.85em; color: #888;">{html.escape(meta["publisher"])}</p>
    </div>
</body>
</html>
"""
        zf.writestr("OEBPS/titlepage.xhtml", titlepage_html)

        # 5. Chapters XHTML
        manifest_items = [
            '<item id="style" href="style.css" media-type="text/css"/>',
            '<item id="titlepage" href="titlepage.xhtml" media-type="application/xhtml+xml"/>',
            '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
            '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
        ]
        spine_items = [
            '<itemref idref="titlepage"/>'
        ]
        nav_toc_list = []
        ncx_nav_points = []

        for idx, ch in enumerate(chapters_data, 1):
            ch_filename = f"ch{idx:02d}.xhtml"
            ch_id = f"ch{idx:02d}"
            manifest_items.append(f'<item id="{ch_id}" href="{ch_filename}" media-type="application/xhtml+xml"/>')
            spine_items.append(f'<itemref idref="{ch_id}"/>')
            
            nav_toc_list.append(f'<li><a href="{ch_filename}">Chapter {idx}: {html.escape(ch["title"])}</a></li>')
            ncx_nav_points.append(f"""
            <navPoint id="navPoint-{idx+1}" playOrder="{idx+1}">
                <navLabel><text>Chapter {idx}: {html.escape(ch["title"])}</text></navLabel>
                <content src="{ch_filename}"/>
            </navPoint>
            """)

            chapter_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en">
<head>
    <title>Chapter {idx}: {html.escape(ch["title"])}</title>
    <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
    <div class="chapter-number">Chapter {idx}</div>
    <h2>{html.escape(ch["title"])}</h2>
    {ch["html_body"]}
</body>
</html>
"""
            zf.writestr(f"OEBPS/{ch_filename}", chapter_xhtml)

        # 6. Nav Document (EPUB 3)
        nav_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en">
<head>
    <title>Table of Contents</title>
    <link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
    <nav epub:type="toc" id="toc">
        <h1>Table of Contents</h1>
        <ol>
            {chr(10).join(nav_toc_list)}
        </ol>
    </nav>
</body>
</html>
"""
        zf.writestr("OEBPS/nav.xhtml", nav_xhtml)

        # 7. NCX Document (EPUB 2 backward compatibility)
        toc_ncx = f"""<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="urn:uuid:{book_uuid}"/>
        <meta name="dtb:depth" content="1"/>
        <meta name="dtb:totalPageCount" content="0"/>
        <meta name="dtb:maxPageNumber" content="0"/>
    </head>
    <docTitle><text>{html.escape(meta["title"])}</text></docTitle>
    <docAuthor><text>{html.escape(meta["author"])}</text></docAuthor>
    <navMap>
        <navPoint id="navPoint-1" playOrder="1">
            <navLabel><text>Title Page</text></navLabel>
            <content src="titlepage.xhtml"/>
        </navPoint>
        {"".join(ncx_nav_points)}
    </navMap>
</ncx>
"""
        zf.writestr("OEBPS/toc.ncx", toc_ncx)

        # 8. Content.opf (Master Package Document)
        content_opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="3.0">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:identifier id="BookId">urn:uuid:{book_uuid}</dc:identifier>
        <dc:title>{html.escape(meta["title"])}</dc:title>
        <dc:creator>{html.escape(meta["author"])}</dc:creator>
        <dc:publisher>{html.escape(meta["publisher"])}</dc:publisher>
        <dc:language>{meta["language"]}</dc:language>
        <dc:description>{html.escape(meta["description"])}</dc:description>
        <dc:rights>{html.escape(meta["rights"])}</dc:rights>
        <meta property="dcterms:modified">{mod_time}</meta>
    </metadata>
    <manifest>
        {chr(10).join(manifest_items)}
    </manifest>
    <spine toc="ncx">
        {chr(10).join(spine_items)}
    </spine>
</package>
"""
        zf.writestr("OEBPS/content.opf", content_opf)

    return epub_path

