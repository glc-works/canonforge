"""
canonforge.engines.sensory

Unified Sensory Radar, Knowledge Graph Thesaurus, and Immersion Engine.
"""

from canonforge.engines.sensory.dictionary import (
    SensoryLexeme,
    SensoryDictionary,
    get_dictionary,
)
from canonforge.engines.sensory.radar import (
    analyze_text,
    load_composite_profiles,
    get_token_variants,
    DEFAULT_SENSES,
    SIGHT_LEXICON,
    SOUND_LEXICON,
    SMELL_LEXICON,
    TASTE_LEXICON,
    TOUCH_LEXICON,
)
from canonforge.engines.sensory.reporter import (
    print_sensory_report,
    SENSE_ICONS,
)

__all__ = [
    "SensoryLexeme",
    "SensoryDictionary",
    "get_dictionary",
    "analyze_text",
    "load_composite_profiles",
    "get_token_variants",
    "print_sensory_report",
    "SENSE_ICONS",
    "DEFAULT_SENSES",
    "SIGHT_LEXICON",
    "SOUND_LEXICON",
    "SMELL_LEXICON",
    "TASTE_LEXICON",
    "TOUCH_LEXICON",
]
