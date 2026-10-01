"""
CanonForge CLI Package
--------------------------------------------------------------------------------
Provides Git-native command line interface, capability grouping,
and anti-deadend discovery engine.
"""

from canonforge.cli.main import main, build_parser
from canonforge.cli.dashboard import find_workspace_root, discover_universes

__all__ = [
    "main",
    "build_parser",
    "find_workspace_root",
    "discover_universes",
]
