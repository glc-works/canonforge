#!/usr/bin/env python3
"""
travel_planner.py

Spatial Travel & Logistics Engine for CanonForge.
Calculates overland distances, transit durations, weather impacts, and logistical
requirements across universe locations using SQLite game_world.db.

Features:
1. Shortest path graph search (Dijkstra) between any two places in the universe.
2. Mode-specific travel calculations: Foot, Mount, Crawler, Glider.
3. Weather and seasonal modifiers.
4. Supply calculation: Rations (lbs), Water (quarts), and Camp Rest Stops.
5. Generates narrative-ready travel log snippets for authors.
"""

import sys
import os
import sqlite3
import argparse
import heapq
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

SCRIPT_DIR = Path(__file__).resolve().parent
CONVERGENCE_DIR = SCRIPT_DIR.parent
DATA_DIR = CONVERGENCE_DIR / "data"
DB_PATH = DATA_DIR / "game_world.db"

WEATHER_MODIFIERS = {
    "clear": 1.0,
    "rain": 1.25,
    "blizzard": 1.55,
    "ash_storm": 1.40
}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def resolve_place_id(conn: sqlite3.Connection, query: str) -> Optional[Tuple[str, str, int]]:
    """Resolve user input to place_id and canonical name."""
    cur = conn.cursor()
    # Try exact match on ID
    cur.execute("SELECT place_id, name, danger_level FROM places WHERE place_id = ?", (query,))
    row = cur.fetchone()
    if row:
        return row["place_id"], row["name"], row["danger_level"]

    # Try exact match on name
    cur.execute("SELECT place_id, name, danger_level FROM places WHERE LOWER(name) = LOWER(?)", (query,))
    row = cur.fetchone()
    if row:
        return row["place_id"], row["name"], row["danger_level"]

    # Try LIKE match
    cur.execute("SELECT place_id, name, danger_level FROM places WHERE LOWER(name) LIKE LOWER(?)", (f"%{query}%",))
    row = cur.fetchone()
    if row:
        return row["place_id"], row["name"], row["danger_level"]

    return None

def build_graph(conn: sqlite3.Connection) -> Dict[str, List[Dict[str, Any]]]:
    """Build bidirectional graph of place routes."""
    cur = conn.cursor()
    cur.execute("""
        SELECT route_id, from_place_id, to_place_id, distance_miles, terrain_type, 
               elevation_change_ft, hazard_rating, standard_foot_hours, mount_hours, glider_crawler_hours, notes
        FROM place_routes
    """)
    rows = cur.fetchall()
    graph: Dict[str, List[Dict[str, Any]]] = {}

    for r in rows:
        u = r["from_place_id"]
        v = r["to_place_id"]
        if u not in graph:
            graph[u] = []
        if v not in graph:
            graph[v] = []

        edge_forward = dict(r)
        edge_forward["target"] = v
        graph[u].append(edge_forward)

        # Reverse edge (bidirectional travel)
        edge_reverse = dict(r)
        edge_reverse["target"] = u
        edge_reverse["elevation_change_ft"] = -r["elevation_change_ft"]
        graph[v].append(edge_reverse)

    return graph

def dijkstra_shortest_path(graph: Dict[str, List[Dict[str, Any]]], start_id: str, end_id: str, mode: str) -> Optional[List[Dict[str, Any]]]:
    """Find the shortest travel time path using Dijkstra algorithm."""
    hour_key = {
        "foot": "standard_foot_hours",
        "mount": "mount_hours",
        "crawler": "glider_crawler_hours",
        "glider": "glider_crawler_hours"
    }.get(mode, "mount_hours")

    # Priority queue: (cost_hours, current_node, path_edges)
    queue = [(0.0, start_id, [])]
    visited = {}

    while queue:
        cost, curr, path = heapq.heappop(queue)

        if curr in visited and visited[curr] <= cost:
            continue
        visited[curr] = cost

        if curr == end_id:
            return path

        for edge in graph.get(curr, []):
            nxt = edge["target"]
            edge_cost = edge[hour_key]
            if nxt not in visited or cost + edge_cost < visited[nxt]:
                heapq.heappush(queue, (cost + edge_cost, nxt, path + [edge]))

    return None

def format_travel_plan(conn: sqlite3.Connection, start_info: Tuple[str, str, int], end_info: Tuple[str, str, int], 
                       path: List[Dict[str, Any]], mode: str, weather: str, party_size: int):
    """Format comprehensive travel logistics report."""
    start_id, start_name, _ = start_info
    end_id, end_name, _ = end_info

    hour_key = {
        "foot": "standard_foot_hours",
        "mount": "mount_hours",
        "crawler": "glider_crawler_hours",
        "glider": "glider_crawler_hours"
    }.get(mode, "mount_hours")

    weather_mod = WEATHER_MODIFIERS.get(weather.lower(), 1.0)

    total_miles = sum(edge["distance_miles"] for edge in path)
    total_leagues = total_miles / 3.0
    base_hours = sum(edge[hour_key] for edge in path)
    adjusted_hours = base_hours * weather_mod
    travel_days = max(1.0, adjusted_hours / 8.0) # Standard 8-hour travel day

    # Supplies
    rations_lbs = party_size * travel_days * 1.5
    water_quarts = party_size * travel_days * 2.0
    camps_needed = int(travel_days) if adjusted_hours > 8.0 else 0

    print("\n" + "=" * 75)
    print(f"CANONFORGE EXPEDITION LOGISTICS PLANNER")
    print("=" * 75)
    print(f"• Origin       : {start_name} ({start_id})")
    print(f"• Destination  : {end_name} ({end_id})")
    print(f"• Transport    : {mode.upper()} ({'8-legged Crawler / Glider' if mode in ('crawler', 'glider') else ('Steel-Hound / Horse' if mode == 'mount' else 'Forced March')})")
    print(f"• Weather      : {weather.upper()} (Time Multiplier: {weather_mod:.2f}x)")
    print(f"• Party Size   : {party_size} traveler(s)")
    print("-" * 75)

    print(f"\n📊 EXPEDITION TOTALS:")
    print(f"  - Total Distance   : {total_miles:.1f} miles ({total_leagues:.1f} leagues)")
    print(f"  - Estimated Transit: {adjusted_hours:.1f} hours ({travel_days:.1f} marching days)")
    print(f"  - Camps / Bivouacs : {camps_needed} overnight stop(s) required")
    print(f"  - Provisions Needed: {rations_lbs:.1f} lbs dried rations / {water_quarts:.1f} quarts fresh water")

    print("\n📍 ROUTE ITINERARY LEGS:")
    itinerary_table = []
    cur = conn.cursor()
    max_hazard = 1

    for idx, edge in enumerate(path, 1):
        target_id = edge["target"]
        cur.execute("SELECT name, danger_level FROM places WHERE place_id = ?", (target_id,))
        t_row = cur.fetchone()
        t_name = t_row["name"] if t_row else target_id
        
        leg_hrs = edge[hour_key] * weather_mod
        h_rating = edge["hazard_rating"]
        if h_rating > max_hazard:
            max_hazard = h_rating
            
        danger_str = "⚠️ " * h_rating if h_rating >= 3 else f"Level {h_rating}"
        itinerary_table.append([
            f"Leg {idx}",
            f"To {t_name}",
            f"{edge['distance_miles']} mi",
            edge["terrain_type"][:25],
            f"{leg_hrs:.1f} hrs",
            danger_str
        ])

    if HAS_TABULATE:
        print(tabulate(itinerary_table, headers=["Leg", "Waypost", "Distance", "Terrain", "Duration", "Hazard"], tablefmt="simple"))
    else:
        for r in itinerary_table:
            print(f"  • {r[0]}: {r[1]} ({r[2]}) - {r[3]} | {r[4]} | Hazard: {r[5]}")

    if max_hazard >= 4:
        print(f"\n🚨 TACTICAL ALERT: Route traverses high-danger frontier terrain (Hazard Rating: {max_hazard}/5). Maintain armed guard watch at night.")

    print("\n" + "-" * 75)
    print("📜 NARRATIVE PROSE SNIPPET (Ready for Chapter Integration):")
    print("-" * 75)
    hours_round = round(adjusted_hours, 1)
    days_text = f"{int(travel_days)} days" if int(travel_days) > 1 else f"{hours_round} hours"
    print(f"> The journey from {start_name} to {end_name} covered {total_miles:.0f} miles across {len(path)} treacherous legs. By {mode}, through the biting {weather}, it would take them at least {days_text} of relentless marching. With {party_size} mouths to feed, they packed {rations_lbs:.0f} pounds of salted marrow and smoked oats, mindful that the shale ridges offered neither shelter nor clean springwater.")
    print("=" * 75 + "\n")

def list_all_places(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("SELECT place_id, name, location_kind, danger_level, governing_faction FROM places ORDER BY danger_level, name")
    rows = cur.fetchall()
    print("\n" + "=" * 75)
    print(f"CANONICAL UNIVERSE LOCATIONS (Total: {len(rows)})")
    print("=" * 75)
    table_data = [[r["place_id"], r["name"], r["location_kind"], r["governing_faction"], f"Level {r['danger_level']}"] for r in rows]
    if HAS_TABULATE:
        print(tabulate(table_data, headers=["Place ID", "Name", "Kind", "Faction", "Danger"], tablefmt="simple"))
    else:
        for r in table_data:
            print(f"  • {r[0]:<30} | {r[1]:<25} | {r[2]} | {r[4]}")
    print("=" * 75 + "\n")

def main():
    parser = argparse.ArgumentParser(description="CanonForge Frontier Geography & Travel Logistics Planner")
    parser.add_argument("--from", dest="from_loc", help="Departure location (name or place_id)")
    parser.add_argument("--to", dest="to_loc", help="Destination location (name or place_id)")
    parser.add_argument("--mode", default="mount", choices=["foot", "mount", "crawler", "glider"], help="Transport mode")
    parser.add_argument("--weather", default="clear", choices=["clear", "rain", "blizzard", "ash_storm"], help="Weather condition")
    parser.add_argument("--party", type=int, default=2, help="Number of travelers in party")
    parser.add_argument("--list", action="store_true", help="List all places registered in the active universe")
    args = parser.parse_args()

    conn = get_db()

    if args.list or not args.from_loc or not args.to_loc:
        list_all_places(conn)
        if not args.from_loc or not args.to_loc:
            print("💡 Usage Example: uv run scripts/travel_planner.py --from 'River Crossing' --to 'Mist Hollow' --mode mount --weather blizzard\n")
            conn.close()
            return

    start_info = resolve_place_id(conn, args.from_loc)
    end_info = resolve_place_id(conn, args.to_loc)

    if not start_info:
        print(f"❌ Error: Origin location '{args.from_loc}' not found. Use --list to view valid places.")
        conn.close()
        sys.exit(1)

    if not end_info:
        print(f"❌ Error: Destination location '{args.to_loc}' not found. Use --list to view valid places.")
        conn.close()
        sys.exit(1)

    graph = build_graph(conn)
    path = dijkstra_shortest_path(graph, start_info[0], end_info[0], args.mode)

    if not path:
        print(f"❌ No connected route found between {start_info[1]} and {end_info[1]}.")
        conn.close()
        sys.exit(1)

    format_travel_plan(conn, start_info, end_info, path, args.mode, args.weather, args.party)
    conn.close()

if __name__ == "__main__":
    main()
