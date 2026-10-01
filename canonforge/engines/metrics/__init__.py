"""
canonforge.engines.metrics

High-Performance Chapter Metrics & Content Counter Engine.
"""
from canonforge.engines.metrics.cache import init_metrics_cache, clear_metrics_cache
from canonforge.engines.metrics.registry import (
    get_canonical_character_registry, get_item_registry
)
from canonforge.engines.metrics.calculator import (
    compute_metrics, get_chapter_metrics
)
from canonforge.engines.metrics.reporter import (
    print_chapter_dossier, print_book_summary, find_target_file
)
from canonforge.engines.metrics.cli import main

__all__ = [
    "init_metrics_cache",
    "clear_metrics_cache",
    "get_canonical_character_registry",
    "get_item_registry",
    "compute_metrics",
    "get_chapter_metrics",
    "print_chapter_dossier",
    "print_book_summary",
    "find_target_file",
    "main",
]
