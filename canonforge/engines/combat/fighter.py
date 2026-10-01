"""
Fighter model and character/monster relational loading.
"""
import re
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from canonforge.core.manifest import find_universe_root

def get_db_path() -> Path:
    u_root = find_universe_root()
    for cand in [u_root / "data" / "game_world.db", u_root / "db" / "game_world.db", Path.cwd() / "data" / "game_world.db"]:
        if cand.is_file():
            return cand
    return u_root / "data" / "game_world.db"

def get_db_connection() -> sqlite3.Connection:
    db_file = get_db_path()
    if not db_file.exists():
        raise FileNotFoundError(f"Game database not found at {db_file}. Run 'cf db' first.")
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    return conn

class Fighter:
    def __init__(self, fighter_id: str, name: str, is_player: bool = True):
        self.fighter_id = fighter_id
        self.name = name
        self.is_player = is_player
        self.race = "Valen"
        self.role = "Fighter"
        self.max_hp = 100
        self.current_hp = 100
        self.max_fp = 0
        self.current_fp = 0
        self.max_sp = 50
        self.current_sp = 50
        self.heat_cap = 0
        self.current_heat = 0
        self.phys_atk = 15
        self.force_atk = 0
        self.phys_def = 10
        self.force_def = 10
        self.element = "None"
        self.polarity = "Balanced"
        self.danger_rating = 1
        self.skills: List[Dict[str, Any]] = []
        self.weaknesses: List[str] = []
        self.immunities: List[str] = []
        
        # Buffs / Status
        self.shield = 0
        self.is_guarding = False
        self.is_dodging = False
        self.is_stunned = False
        self.atk_buff_turns = 0
        self.atk_buff_mult = 1.0
        self.def_buff_turns = 0
        self.def_buff_mult = 1.0
        self.potions_remaining = 2

    @property
    def is_alive(self) -> bool:
        return self.current_hp > 0

    def start_turn(self) -> List[str]:
        logs = []
        self.is_guarding = False
        
        # Stamina passive regen
        sp_regen = 8
        if self.current_sp < self.max_sp:
            self.current_sp = min(self.max_sp, self.current_sp + sp_regen)
            
        # Mechanical heat dissipation
        if self.heat_cap > 0 and self.current_heat > 0:
            vent = 6
            self.current_heat = max(0, self.current_heat - vent)
            
        # Buff countdowns
        if self.atk_buff_turns > 0:
            self.atk_buff_turns -= 1
            if self.atk_buff_turns == 0:
                self.atk_buff_mult = 1.0
                logs.append(f"  • {self.name}'s Attack Buff wore off.")
                
        if self.def_buff_turns > 0:
            self.def_buff_turns -= 1
            if self.def_buff_turns == 0:
                self.def_buff_mult = 1.0
                logs.append(f"  • {self.name}'s Defense Buff wore off.")

        if self.is_stunned:
            self.is_stunned = False
            logs.append(f"  ⚡ {self.name} breaks free from Stun!")
            return logs, True # turn skipped due to recovery
            
        return logs, False

    def take_damage(self, raw_damage: float, damage_type: str = "physical", attack_element: str = "None") -> Tuple[int, List[str]]:
        notes = []

        # Check evasion
        if self.is_dodging:
            self.is_dodging = False
            if random.random() < 0.6:
                notes.append("💨 EVADED! Rapid footwork completely dodged the strike.")
                return 0, notes
        
        # Check immunities
        if attack_element in self.immunities:
            notes.append(f"🛡️ IMMUNE to {attack_element}!")
            return 0, notes

        # Elemental modifier
        elem_mult = 1.0
        if (attack_element, self.element) in ELEMENT_ADVANTAGE:
            elem_mult = ELEMENT_ADVANTAGE[(attack_element, self.element)]
            if elem_mult > 1.0:
                notes.append(f"💥 Elemental Counter! (+20% vs {self.element})")
            else:
                notes.append(f"🌧️ Elemental Disadvantage (-20% vs {self.element})")

        # Weakness check
        if attack_element in self.weaknesses:
            elem_mult *= 1.3
            notes.append(f"⚠️ Hit Monster Weakness (+30% bonus)!")

        # Defense mitigation formula: Damage = RawAtk * (RawAtk / (RawAtk + Def)) * elem_mult
        defense = self.force_def if damage_type == "force" else self.phys_def
        defense *= self.def_buff_mult
        if self.is_guarding:
            defense *= 1.5
            notes.append("🛡️ Guarding stance reduced impact!")

        mitigated_damage = raw_damage * (raw_damage / (raw_damage + max(1.0, defense))) * elem_mult
        final_damage = max(1, int(round(mitigated_damage)))

        # Shield absorption
        if self.shield > 0:
            absorbed = min(self.shield, final_damage)
            self.shield -= absorbed
            final_damage -= absorbed
            notes.append(f"✨ Barrier absorbed {absorbed} dmg (Remaining: {self.shield})")

        self.current_hp = max(0, self.current_hp - final_damage)
        return final_damage, notes

def load_character(conn: sqlite3.Connection, char_id: str) -> Optional[Fighter]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM v_character_combat_stats WHERE char_id = ?", (char_id,))
    row = cur.fetchone()
    if not row:
        return None

    f = Fighter(char_id, row["name"], is_player=True)
    f.race = row["birth_race"]
    f.role = row["role"]
    f.max_hp = row["max_hp"]
    f.current_hp = row["max_hp"]
    f.max_fp = row["max_fp"]
    f.current_fp = row["max_fp"]
    f.max_sp = row["max_sp"]
    f.current_sp = row["max_sp"]
    f.heat_cap = row["heat_capacity"]
    f.current_heat = 0
    f.phys_atk = row["base_phys_atk"]
    f.force_atk = row["base_force_atk"]
    f.phys_def = row["base_phys_def"]
    f.force_def = row["base_force_def"]

    # Assign affinity dynamically based on character traits or default to Balanced
    race_clean = f.race.lower() if f.race else "human"
    if "wind" in race_clean or "aether" in race_clean or "sky" in race_clean:
        f.element = "Wind"
        f.polarity = "Light"
    elif "fire" in race_clean or "forge" in race_clean or "iron" in race_clean:
        f.element = "Fire"
        f.polarity = "Dark"
    else:
        f.element = "Earth"
        f.polarity = "Balanced"

    # Load up to 4 canonical legal skills for this character's race / calling
    cur.execute("""
        SELECT * FROM skills 
        WHERE legal_races = 'All' OR legal_races = ? OR legal_races LIKE ?
        ORDER BY skill_tier ASC, resource_cost ASC 
        LIMIT 4
    """, (f.race, f"%{f.race}%"))
    f.skills = [dict(r) for r in cur.fetchall()]

    return f

def load_monster(conn: sqlite3.Connection, monster_id: str) -> Optional[Fighter]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM monsters WHERE monster_id = ?", (monster_id,))
    row = cur.fetchone()
    if not row:
        return None

    f = Fighter(monster_id, row["name"], is_player=False)
    f.role = row["classification"]
    f.max_hp = row["base_hp"]
    f.current_hp = row["base_hp"]
    f.phys_atk = row["base_atk"]
    f.force_atk = int(row["base_atk"] * 0.8)
    f.phys_def = int(row["base_hp"] * 0.25)
    f.force_def = int(row["base_hp"] * 0.2)
    f.element = row["element"] or "None"
    f.danger_rating = row["danger_rating"]
    
    try:
        f.weaknesses = json.loads(row["weaknesses"]) if row["weaknesses"] else []
    except:
        f.weaknesses = []
    try:
        f.immunities = json.loads(row["immunities"]) if row["immunities"] else []
    except:
        f.immunities = []

    # Assign monster default innate skill
    f.skills = [
        {
            "name": f"{row['element']} Surge",
            "resource_pool": "SP",
            "resource_cost": 0,
            "primary_effect": "damage",
            "effect_magnitude": 1.35,
            "polarity_affinity": row["element"]
        },
        {
            "name": "Ferocious Pounce",
            "resource_pool": "SP",
            "resource_cost": 0,
            "primary_effect": "damage",
            "effect_magnitude": 1.15,
            "polarity_affinity": "Physical"
        }
    ]

    return f

def get_monster_loot(conn: sqlite3.Connection, monster_id: str) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("""
        SELECT d.item_id, i.name, d.drop_chance, d.min_qty, d.max_qty
        FROM monster_loot_drops d
        JOIN items i ON d.item_id = i.item_id
        WHERE d.monster_id = ?
    """, (monster_id,))
    return [dict(r) for r in cur.fetchall()]

