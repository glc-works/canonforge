"""
canonforge.engines.prep

CanonForge Studio: Instant Scene & Authoring Brief Generator (OKF v0.3).
"""
from canonforge.engines.prep.locator import (
    find_chapter_target,
    get_git_modified_chapters,
    parse_frontmatter,
)
from canonforge.engines.prep.palettes import (
    extract_previous_chapter_hook,
    get_setting_sensory_palette,
)
from canonforge.engines.prep.builder import generate_scene_brief
from canonforge.engines.prep.prompt import (
    print_scene_brief,
    generate_llm_authoring_prompt,
)
from canonforge.engines.prep.cli import main

__all__ = [
    "find_chapter_target",
    "get_git_modified_chapters",
    "parse_frontmatter",
    "extract_previous_chapter_hook",
    "get_setting_sensory_palette",
    "generate_scene_brief",
    "print_scene_brief",
    "generate_llm_authoring_prompt",
    "main",
]
