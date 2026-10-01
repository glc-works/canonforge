"""
canonforge.engines.combat

Deterministic RPG Turn-Based Combat Simulation Engine.
"""
from canonforge.engines.combat.fighter import (
    Fighter,
    get_db_connection,
    load_character,
    load_monster,
    get_monster_loot,
)
from canonforge.engines.combat.mechanics import (
    render_hp_bar,
    render_status_card,
    execute_action,
    choose_monster_action,
)
from canonforge.engines.combat.simulator import simulate_battle
from canonforge.engines.combat.cli import list_combatants, main

__all__ = [
    "Fighter",
    "get_db_connection",
    "load_character",
    "load_monster",
    "get_monster_loot",
    "render_hp_bar",
    "render_status_card",
    "execute_action",
    "choose_monster_action",
    "simulate_battle",
    "list_combatants",
    "main",
]
