"""
Turn-based combat physics, action resolution, and status effects.
"""
import random
from typing import List, Tuple
from canonforge.engines.combat.fighter import Fighter

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

