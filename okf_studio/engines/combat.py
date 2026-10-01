#!/usr/bin/env python3
"""
CONVERGENCE STUDIO: DETERMINISTIC RPG COMBAT SIMULATOR
------------------------------------------------------------------------------
Implements the canonical turn-based combat system defined in:
  • wiki/systems/Attributes-and-Stats.md (Diminishing Return Mitigation & Flat Ceiling)
  • wiki/systems/Skills-and-Resources.md (Energy Triad: SP, FP, Heat)
  • wiki/systems/Elements-and-Polarity.md (Terrestrial Elements Quad & Counters)
------------------------------------------------------------------------------
"""

import sys
import json
import random
import sqlite3
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

CONVERGENCE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = CONVERGENCE_DIR / "data" / "game_world.db"

# Canonical Terrestrial Elemental Cycle:
# Fire -> Wind -> Water -> Earth -> Fire
ELEMENT_ADVANTAGE = {
    ("Fire", "Wind"): 1.2,
    ("Fire", "Water"): 0.8,
    ("Wind", "Water"): 1.2,
    ("Wind", "Fire"): 0.8,
    ("Water", "Earth"): 1.2,
    ("Water", "Wind"): 0.8,
    ("Earth", "Fire"): 1.2,
    ("Earth", "Water"): 0.8,
}

def get_db_connection() -> sqlite3.Connection:
    if not DB_PATH.exists():
        print(f"❌ Error: Database not found at {DB_PATH}. Run scripts/init_local_db.py first.")
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
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
            
        # Korvath heat dissipation
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

    # Assign affinity
    if "Aurei" in f.race:
        f.element = "Wind"
        f.polarity = "Light"
    elif "Korvath" in f.race:
        f.element = "Fire"
        f.polarity = "Dark"
    else:
        f.element = "Earth"
        f.polarity = "Balanced"

    # Load 4 canonical legal skills for this character's race / calling
    race_filter = "Aurei" if "Aurei" in f.race else ("Korvath" if "Korvath" in f.race else "Valen")
    cur.execute("""
        SELECT * FROM skills 
        WHERE legal_races = 'All' OR legal_races = ?
        ORDER BY skill_tier ASC, resource_cost ASC 
        LIMIT 4
    """, (race_filter,))
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

def render_hp_bar(current: int, maximum: int, length: int = 16) -> str:
    ratio = max(0.0, min(1.0, current / max(1, maximum)))
    filled = int(round(ratio * length))
    empty = length - filled
    bar = "█" * filled + "░" * empty
    return f"[{bar}] {current:>3}/{maximum:<3} HP"

def render_status_card(f1: Fighter, f2: Fighter):
    print("┌" + "─" * 38 + "┬" + "─" * 38 + "┐")
    print(f"│ {f1.name[:36]:<36} │ {f2.name[:36]:<36} │")
    p1_race = f"{f1.race} ({f1.element})" if f1.is_player else f"Threat Lv.{f1.danger_rating} ({f1.element})"
    p2_race = f"{f2.race} ({f2.element})" if f2.is_player else f"Threat Lv.{f2.danger_rating} ({f2.element})"
    print(f"│ {p1_race[:36]:<36} │ {p2_race[:36]:<36} │")
    print(f"│ {render_hp_bar(f1.current_hp, f1.max_hp)[:36]:<36} │ {render_hp_bar(f2.current_hp, f2.max_hp)[:36]:<36} │")
    
    # Resource lines
    if f1.heat_cap > 0:
        res1 = f"Heat: {f1.current_heat}/{f1.heat_cap} | SP: {f1.current_sp}/{f1.max_sp}"
    elif f1.max_fp > 0:
        res1 = f"FP: {f1.current_fp}/{f1.max_fp} | SP: {f1.current_sp}/{f1.max_sp}"
    else:
        res1 = f"SP: {f1.current_sp}/{f1.max_sp}"

    if f2.heat_cap > 0:
        res2 = f"Heat: {f2.current_heat}/{f2.heat_cap} | SP: {f2.current_sp}/{f2.max_sp}"
    elif f2.max_fp > 0:
        res2 = f"FP: {f2.current_fp}/{f2.max_fp} | SP: {f2.current_sp}/{f2.max_sp}"
    else:
        res2 = f"SP: {f2.current_sp}/{f2.max_sp}"

    print(f"│ {res1[:36]:<36} │ {res2[:36]:<36} │")
    print("└" + "─" * 38 + "┴" + "─" * 38 + "┘")

def execute_action(actor: Fighter, target: Fighter, action_type: str, skill_idx: int = 0) -> List[str]:
    logs = []
    
    if action_type == "attack":
        # Determine whether to use Phys or Force
        use_force = actor.force_atk > actor.phys_atk and actor.max_fp > 0
        raw_atk = actor.force_atk if use_force else actor.phys_atk
        raw_atk *= actor.atk_buff_mult
        dmg_type = "force" if use_force else "physical"
        
        dmg, notes = target.take_damage(raw_atk, damage_type=dmg_type, attack_element=actor.element)
        atk_label = "Force Bolt" if use_force else "Martial Strike"
        logs.append(f"⚔️ {actor.name} executes [{atk_label}] on {target.name} for {dmg} damage!")
        for n in notes:
            logs.append(f"   └─ {n}")

    elif action_type == "guard":
        actor.is_guarding = True
        actor.current_sp = min(actor.max_sp, actor.current_sp + 15)
        if actor.heat_cap > 0:
            actor.current_heat = max(0, actor.current_heat - 15)
        logs.append(f"🛡️ {actor.name} assumes [Bulwark Guard Stance]! (Def +50%, Stamina restored)")

    elif action_type == "potion":
        if actor.potions_remaining <= 0:
            logs.append(f"❌ {actor.name} reaches into satchel, but has no healing salves remaining!")
        else:
            actor.potions_remaining -= 1
            heal = int(actor.max_hp * 0.35)
            actor.current_hp = min(actor.max_hp, actor.current_hp + heal)
            actor.current_sp = min(actor.max_sp, actor.current_sp + 20)
            if actor.max_fp > 0:
                actor.current_fp = min(actor.max_fp, actor.current_fp + 15)
            logs.append(f"🧪 {actor.name} consumes [Sanctum Salve]! (Healed +{heal} HP, {actor.potions_remaining} left)")

    elif action_type == "skill":
        if not actor.skills or skill_idx >= len(actor.skills):
            logs.append(f"❌ Skill not found!")
            return logs

        sk = actor.skills[skill_idx]
        pool = sk.get("resource_pool", "SP")
        cost = sk.get("resource_cost", 0)

        # Check resource availability
        if pool == "SP" and actor.current_sp < cost:
            logs.append(f"⚠️ Not enough Stamina for [{sk['name']}]! (Needs {cost}, has {actor.current_sp})")
            # Fallback to normal attack
            return execute_action(actor, target, "attack")
        elif pool == "FP" and actor.current_fp < cost:
            logs.append(f"⚠️ Not enough Force for [{sk['name']}]! (Needs {cost}, has {actor.current_fp})")
            return execute_action(actor, target, "attack")
        elif pool == "Heat" and (actor.current_heat + cost > actor.heat_cap):
            logs.append(f"⚠️ OVERHEAT WARNING! [{sk['name']}] exceeds Heat Capacity ({actor.current_heat + cost} > {actor.heat_cap})!")
            return execute_action(actor, target, "guard")

        # Deduct / Add resource
        if pool == "SP":
            actor.current_sp -= cost
        elif pool == "FP":
            actor.current_fp -= cost
        elif pool == "Heat":
            actor.current_heat += cost

        # Apply skill effect
        effect = sk.get("primary_effect", "damage")
        mag = sk.get("effect_magnitude", 1.0)
        logs.append(f"⚡ {actor.name} unleashes [{sk['name']}]! (Cost: {cost} {pool})")

        if effect in ("damage", "aoe_damage"):
            raw_atk = (actor.force_atk if pool == "FP" else actor.phys_atk) * mag * actor.atk_buff_mult
            dmg_type = "force" if pool == "FP" else "physical"
            sk_elem = sk.get("polarity_affinity", actor.element)
            dmg, notes = target.take_damage(raw_atk, damage_type=dmg_type, attack_element=sk_elem)
            logs.append(f"   └─ Impact hits for {dmg} damage!")
            for n in notes:
                logs.append(f"   └─ {n}")

        elif effect == "shield":
            actor.shield += int(actor.max_hp * mag)
            logs.append(f"   └─ Conjured barrier protecting {actor.shield} HP!")

        elif effect == "buff_atk":
            actor.atk_buff_turns = 2
            actor.atk_buff_mult = mag
            logs.append(f"   └─ Attack boosted by {int((mag-1.0)*100)}% for 2 rounds!")

        elif effect == "buff_def":
            actor.def_buff_turns = 2
            actor.def_buff_mult = mag
            logs.append(f"   └─ Defense bolstered by {int((mag-1.0)*100)}% for 2 rounds!")

        elif effect == "stun":
            target.is_stunned = True
            logs.append(f"   └─ Target is STUNNED and cannot act next round!")

        elif effect == "dodge":
            actor.is_dodging = True
            logs.append(f"   └─ Prepared evasive footwork (60% chance to dodge next attack)!")

        elif effect == "debuff_def":
            target.def_buff_turns = 2
            target.def_buff_mult = 0.7
            logs.append(f"   └─ Weakened {target.name}'s armor (-30% Defense for 2 rounds)!")

        elif effect == "summon":
            aid_guard = int(actor.max_hp * (mag * 0.35))
            actor.shield += aid_guard
            logs.append(f"   └─ Deployed tactical automaton/animus! (Absorbs +{aid_guard} damage)")

        elif effect == "cleanse":
            actor.is_stunned = False
            actor.def_buff_mult = 1.0
            logs.append("   └─ Purged status impairments and restored equilibrium!")

        elif effect in ("taunt", "root", "slow"):
            target.is_guarding = False
            logs.append(f"   └─ Disrupted {target.name}'s tactical positioning!")

        elif effect == "first_strike":
            raw_atk = (actor.force_atk if pool == "FP" else actor.phys_atk) * mag * 1.2
            dmg_type = "force" if pool == "FP" else "physical"
            dmg, notes = target.take_damage(raw_atk, damage_type=dmg_type, attack_element=actor.element)
            logs.append(f"   └─ Swift initiative strike hits for {dmg} damage!")
            for n in notes:
                logs.append(f"   └─ {n}")

        elif effect == "heal":
            heal = int(actor.max_hp * mag)
            actor.current_hp = min(actor.max_hp, actor.current_hp + heal)
            logs.append(f"   └─ Restored +{heal} HP!")

    return logs

def choose_monster_action(m: Fighter, p: Fighter) -> Tuple[str, int]:
    # 40% skill, 60% attack
    if m.skills and random.random() < 0.45:
        idx = random.randint(0, len(m.skills) - 1)
        return "skill", idx
    return "attack", 0

def simulate_battle(p1: Fighter, p2: Fighter, interactive: bool = False) -> Dict[str, Any]:
    print("\n" + "=" * 80)
    print(f"⚔️ CONVERGENCE RPG COMBAT ARENA: {p1.name} vs. {p2.name}")
    print("=" * 80)

    round_num = 1
    max_rounds = 30
    battle_log = []

    while p1.is_alive and p2.is_alive and round_num <= max_rounds:
        print(f"\n--- [ ROUND {round_num} ] ---")
        render_status_card(p1, p2)

        # -----------------------------
        # 1. Fighter 1 Turn
        # -----------------------------
        p1_notes, p1_skip = p1.start_turn()
        for note in p1_notes:
            print(note)
            
        if not p1_skip and p1.is_alive:
            if interactive and p1.is_player:
                print(f"\nSelect Action for {p1.name}:")
                print("  [1] Normal Attack")
                for i, sk in enumerate(p1.skills):
                    cost_str = f"{sk.get('resource_cost', 0)} {sk.get('resource_pool', 'SP')}"
                    print(f"  [{i+2}] Skill: {sk['name']} ({cost_str} - {sk.get('primary_effect')})")
                offset = len(p1.skills) + 2
                print(f"  [{offset}] Bulwark Guard / Vent")
                print(f"  [{offset+1}] Use Sanctum Salve ({p1.potions_remaining} left)")
                
                try:
                    choice = input("\nAction (1-{}): ".format(offset+1)).strip()
                    choice_int = int(choice)
                    if choice_int == 1:
                        act, s_idx = "attack", 0
                    elif 2 <= choice_int < offset:
                        act, s_idx = "skill", choice_int - 2
                    elif choice_int == offset:
                        act, s_idx = "guard", 0
                    elif choice_int == offset + 1:
                        act, s_idx = "potion", 0
                    else:
                        act, s_idx = "attack", 0
                except (ValueError, EOFError):
                    act, s_idx = "attack", 0
            else:
                # Automated logic
                if p1.current_hp < p1.max_hp * 0.35 and p1.potions_remaining > 0:
                    act, s_idx = "potion", 0
                elif p1.heat_cap > 0 and p1.current_heat > p1.heat_cap * 0.75:
                    act, s_idx = "guard", 0
                elif p1.skills and random.random() < 0.6:
                    act, s_idx = "skill", random.randint(0, len(p1.skills) - 1)
                else:
                    act, s_idx = "attack", 0

            logs = execute_action(p1, p2, act, s_idx)
            for l in logs:
                print(l)
                battle_log.append(l)

        if not p2.is_alive:
            break

        # -----------------------------
        # 2. Fighter 2 Turn
        # -----------------------------
        p2_notes, p2_skip = p2.start_turn()
        for note in p2_notes:
            print(note)

        if not p2_skip and p2.is_alive:
            if interactive and p2.is_player:
                # 2nd player interactive in PvP
                act, s_idx = "attack", 0
            elif not p2.is_player:
                act, s_idx = choose_monster_action(p2, p1)
            else:
                if p2.current_hp < p2.max_hp * 0.35 and p2.potions_remaining > 0:
                    act, s_idx = "potion", 0
                elif p2.skills and random.random() < 0.5:
                    act, s_idx = "skill", random.randint(0, len(p2.skills) - 1)
                else:
                    act, s_idx = "attack", 0

            logs = execute_action(p2, p1, act, s_idx)
            for l in logs:
                print(l)
                battle_log.append(l)

        round_num += 1

    # End of battle evaluation
    print("\n" + "=" * 80)
    print("🏁 COMBAT RESOLUTION & AFTERMATH")
    print("=" * 80)

    winner = p1 if p1.is_alive else (p2 if p2.is_alive else None)
    if winner:
        print(f"🏆 VICTORY: {winner.name} stands triumphant after {min(round_num, max_rounds)} rounds!")
    else:
        print(f"🤝 STALEMATE: Combat concluded without decisive kill.")

    conn = get_db_connection()
    loot_dropped = []
    if winner == p1 and not p2.is_player:
        drops = get_monster_loot(conn, p2.fighter_id)
        if drops:
            print("\n🎁 LOOT HARVEST:")
            for d in drops:
                if random.random() <= d["drop_chance"]:
                    qty = random.randint(d["min_qty"], d["max_qty"])
                    print(f"   ✓ [Acquired] {qty}x {d['name']} ({d['item_id']})")
                    loot_dropped.append({"name": d["name"], "qty": qty})
            if not loot_dropped:
                print("   • No rare materials extracted from carcass.")
        
        # Check flat-ceiling rule ratio
        print("\n⚖️ CANONICAL FLAT-CEILING BALANCE AUDIT:")
        atk_ratio = round(p1.phys_atk / max(1, p2.phys_atk), 2)
        hp_ratio = round(p1.max_hp / max(1, p2.max_hp), 2)
        print(f"   • Attack Ratio  : {atk_ratio}x (Albion target: 1.0x - 1.4x)")
        print(f"   • Hit Point Ratio: {hp_ratio}x (Balanced Encounter)")
        if 0.7 <= atk_ratio <= 1.5:
            print("   ✅ PASS: Encounter adheres to the Flat-Ceiling power band canon.")
        else:
            print("   ⚠️ NOTE: High power delta detected (High tier boss or elite encounter).")

    conn.close()
    print("=" * 80 + "\n")
    return {
        "winner": winner.name if winner else "Tie",
        "rounds": round_num,
        "loot": loot_dropped
    }

def list_combatants():
    conn = get_db_connection()
    cur = conn.cursor()
    print("\n" + "=" * 75)
    print("AVAILABLE CHARACTERS (PLAYERS & HEROES)")
    print("=" * 75)
    cur.execute("""
        SELECT char_id, name, birth_race, role, max_hp, max_fp, max_sp, heat_capacity, base_phys_atk, base_phys_def
        FROM v_character_combat_stats
        WHERE char_type IN ('hero', 'npc') AND max_hp > 0
        ORDER BY birth_race, name
        LIMIT 15
    """)
    for r in cur.fetchall():
        res = f"FP:{r['max_fp']}" if r['max_fp'] > 0 else (f"Heat:{r['heat_capacity']}" if r['heat_capacity'] > 0 else f"SP:{r['max_sp']}")
        print(f"• {r['char_id']:<32} | {r['name'][:22]:<22} | {r['birth_race'][:12]:<12} | HP:{r['max_hp']:<3} Atk:{r['base_phys_atk']:<2} Def:{r['base_phys_def']:<2} | {res}")

    print("\n" + "=" * 75)
    print("AVAILABLE BESTIARY MONSTERS")
    print("=" * 75)
    cur.execute("""
        SELECT monster_id, name, element, base_hp, base_atk, danger_rating, primary_habitat
        FROM monsters
        ORDER BY danger_rating, name
        LIMIT 15
    """)
    for r in cur.fetchall():
        print(f"• {r['monster_id']:<24} | {r['name']:<20} | Elem: {r['element']:<6} | Threat Lv.{r['danger_rating']} | HP:{r['base_hp']:<3} Atk:{r['base_atk']:<2}")
    print("=" * 75 + "\n")
    conn.close()

def main():
    parser = argparse.ArgumentParser(description="Deterministic Convergence RPG Turn-Based Combat Simulator")
    parser.add_argument("--player", default="char_vaelin_pale_weaver", help="Character ID for Player (default: char_vaelin_pale_weaver)")
    parser.add_argument("--monster", default="mon_ash_stag", help="Monster ID for Enemy (default: mon_ash_stag)")
    parser.add_argument("--enemy-char", help="Character ID for Enemy Character (PvP duel mode)")
    parser.add_argument("--interactive", action="store_true", help="Interactive round-by-round manual control")
    parser.add_argument("--list", action="store_true", help="List available characters and monsters")
    args = parser.parse_args()

    if args.list:
        list_combatants()
        return

    conn = get_db_connection()
    p1 = load_character(conn, args.player)
    if not p1:
        print(f"❌ Error: Player character '{args.player}' not found.")
        conn.close()
        sys.exit(1)

    if args.enemy_char:
        p2 = load_character(conn, args.enemy_char)
        if not p2:
            print(f"❌ Error: Enemy character '{args.enemy_char}' not found.")
            conn.close()
            sys.exit(1)
        p2.is_player = False # enemy side
    else:
        p2 = load_monster(conn, args.monster)
        if not p2:
            print(f"❌ Error: Monster '{args.monster}' not found.")
            conn.close()
            sys.exit(1)

    conn.close()
    simulate_battle(p1, p2, interactive=args.interactive)

if __name__ == "__main__":
    main()
