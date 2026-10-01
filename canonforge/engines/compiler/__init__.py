"""
canonforge.engines.compiler

Authoritative Novel Manuscript Compiler & Analytics Engine.
"""
from canonforge.engines.compiler.assembler import (
    parse_scene_file,
    load_from_manifest,
    discover_chapters_fallback,
    compile_manuscript,
    resolve_book_dir,
)
from canonforge.engines.compiler.analytics import generate_analytics_report
from canonforge.engines.compiler.epub import markdown_to_html_body, build_epub
from canonforge.engines.compiler.cli import process_book, main

__all__ = [
    "parse_scene_file",
    "load_from_manifest",
    "discover_chapters_fallback",
    "compile_manuscript",
    "resolve_book_dir",
    "generate_analytics_report",
    "markdown_to_html_body",
    "build_epub",
    "process_book",
    "main",
]
