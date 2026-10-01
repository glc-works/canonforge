"""
sensory_dictionary.py

Backward-compatible facade for canonforge.engines.sensory.dictionary.
"""

from canonforge.engines.sensory.dictionary import (
    SensoryLexeme,
    SensoryDictionary,
    get_dictionary,
)

__all__ = ["SensoryLexeme", "SensoryDictionary", "get_dictionary"]
