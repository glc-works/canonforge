"""
Combat encounter orchestration and battle loop simulation.
"""
import time
from typing import Dict, Any
from canonforge.engines.combat.fighter import Fighter, get_db_connection, get_monster_loot
from canonforge.engines.combat.mechanics import (
    render_status_card, execute_action, choose_monster_action
)

def simulate_battle(p1: Fighter, p2: Fighter, interactive: bool = False) -> Dict[str, Any]:
    print("\n" + "=" * 80)
    print(f"⚔️ CANONFORGE RPG COMBAT ARENA: {p1.name} vs. {p2.name}")
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

