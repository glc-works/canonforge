"""
Lightweight Markdown to clean semantic HTML converter.
"""
import re
import html
from typing import Tuple

def markdown_to_html_body(md_text: str) -> Tuple[str, str]:
    """Convert novel chapter markdown into semantic HTML/XHTML."""
    # Strip YAML frontmatter
    body = re.sub(r"^---\s*\n.*?\n---\s*\n", "", md_text, flags=re.DOTALL)
    
    # Extract chapter title
    title_match = re.search(r"^#\s+(.+)$", body, flags=re.MULTILINE)
    chapter_title = title_match.group(1).strip() if title_match else "Chapter"
    
    # Remove top-level h1 from body to avoid duplication
    body = re.sub(r"^#\s+.+$", "", body, count=1, flags=re.MULTILINE)
    
    # Replace wiki links [[Target|Display]] -> Display, [[Target]] -> Target
    body = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r"\2", body)
    body = re.sub(r"\[\[([^\]]+)\]\]", r"\1", body)

    lines = body.splitlines()
    html_lines = []
    in_blockquote = False
    in_list = False
    is_first_p = True

    for raw_line in lines:
        line = raw_line.strip()
        
        # Blank line
        if not line:
            if in_blockquote:
                html_lines.append("</blockquote>")
                in_blockquote = False
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            continue

        # Ornamental scene breaks
        if re.match(r"^(\*\s*\*\s*\*|\*{3,}|_{3,}|-{3,})$", line):
            if in_blockquote:
                html_lines.append("</blockquote>")
                in_blockquote = False
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append('<div class="scene-break">✦ &#160; ✦ &#160; ✦</div>')
            is_first_p = True
            continue

        # Headings (h2, h3)
        h2_match = re.match(r"^##\s+(.+)$", line)
        if h2_match:
            html_lines.append(f'<h2>{html.escape(h2_match.group(1).strip())}</h2>')
            continue
        h3_match = re.match(r"^###\s+(.+)$", line)
        if h3_match:
            html_lines.append(f'<h3>{html.escape(h3_match.group(1).strip())}</h3>')
            continue

        # Blockquote
        if line.startswith(">"):
            if not in_blockquote:
                html_lines.append("<blockquote>")
                in_blockquote = True
            q_text = line.lstrip("> ").strip()
            # Inline formatting
            q_text = format_inlines(q_text)
            html_lines.append(f"<p>{q_text}</p>")
            continue

        # Unordered list
        if line.startswith(("- ", "* ")) and not re.match(r"^(\*\s*\*\s*\*|\*{3,})$", line):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            item_text = line[2:].strip()
            item_text = format_inlines(item_text)
            html_lines.append(f"<li>{item_text}</li>")
            continue

        # Normal paragraph
        p_text = format_inlines(line)
        if is_first_p:
            html_lines.append(f'<p class="first-p">{p_text}</p>')
            is_first_p = False
        else:
            html_lines.append(f"<p>{p_text}</p>")

    if in_blockquote:
        html_lines.append("</blockquote>")
    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines), chapter_title

def format_inlines(text: str) -> str:
    """Format bold, italic, and escape xml/html."""
    # Escape basic HTML chars first (except we handle bold/italic safely)
    t = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    # Bold italic: ***text***
    t = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", t)
    # Bold: **text**
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    # Italic: *text*
    t = re.sub(r"\*([^*\n]+?)\*", r"<em>\1</em>", t)
    # Inline code: `text`
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return t

# ==============================================================================
# 1. STANDALONE INTERACTIVE HTML READER GENERATOR
# ==============================================================================
