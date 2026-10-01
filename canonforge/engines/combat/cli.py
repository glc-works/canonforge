"""
CLI entrypoint for turn-based combat simulation.
"""
import sys
import json
import argparse
from canonforge.engines.combat.fighter import (
    Fighter, get_db_connection, load_character, load_monster
)
from canonforge.engines.combat.simulator import simulate_battle

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
    parser = argparse.ArgumentParser(description="Deterministic CanonForge RPG Turn-Based Combat Simulator")
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
