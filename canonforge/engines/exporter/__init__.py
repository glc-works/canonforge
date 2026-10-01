"""
canonforge.engines.exporter

Authoritative E-Book & Reader Publication Generator.
"""
from canonforge.engines.exporter.metadata import get_book_metadata, resolve_book_dir
from canonforge.engines.exporter.formatter import markdown_to_html_body, format_inlines
from canonforge.engines.exporter.reader_html import generate_html_reader
from canonforge.engines.exporter.epub import generate_epub
from canonforge.engines.exporter.cli import export_single_book, main

__all__ = [
    "get_book_metadata",
    "resolve_book_dir",
    "markdown_to_html_body",
    "format_inlines",
    "generate_html_reader",
    "generate_epub",
    "export_single_book",
    "main",
]
