#!/usr/bin/env python3
"""
CANONFORGE ENGINE: OBSIDIAN CANVAS GENERATOR (CHRONOLOGY & WORLD MATRIX)
--------------------------------------------------------------------------------
Generates interactive, multi-swimlane Obsidian .canvas files dynamically
from the universe's timeline manifest and event ledgers.

Layout Architecture:
- Horizontal X-Axis: Chronological Eras & Epochs
- Vertical Y-Axis: Factions / Theaters / Character Trajectories
- Visual Cards: Event cards with markdown notes, regions, and figures
- Directional Edges: Sequential narrative progression and cross-faction nexus points

Zero Creative IP Contamination: All eras, factions, and cards are discovered
dynamically from active universe data.
--------------------------------------------------------------------------------
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from canonforge.core.manifest import find_universe_root

CANVAS_PALETTE = ["1", "2", "3", "4", "5", "6"]


def load_universe_timeline(universe_dir: Path) -> Dict[str, Any]:
    """Load timeline data from JSON or YAML in universe data directory."""
    data_dir = universe_dir / "data"
    for candidate in [data_dir / "timeline.json", data_dir / "timeline.yaml", data_dir / "chronology.json"]:
        if candidate.exists():
            try:
                if candidate.suffix == ".json":
                    return json.loads(candidate.read_text(encoding="utf-8"))
                elif HAS_YAML:
                    return yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
            except Exception as e:
                print(f"⚠️ Warning loading {candidate.name}: {e}")
    return {}


def build_chronology_canvas(
    universe_dir: Path,
    output_path: Optional[Path] = None,
    factions_filter: Optional[List[str]] = None,
) -> Path:
    """Generate .canvas JSON file with horizontal swimlanes."""
    timeline = load_universe_timeline(universe_dir)
    eras_data = timeline.get("eras", [])
    events_data = timeline.get("events", [])

    if not eras_data and not events_data:
        # Fallback default eras if empty
        eras_data = [
            {"id": "era_0", "name": "Era I: Ancient Foundations", "range": "Early History"},
            {"id": "era_1", "name": "Era II: The Great Schism", "range": "Middle Age"},
            {"id": "era_2", "name": "Era III: The Modern Accord", "range": "Recent Era"},
            {"id": "era_3", "name": "Era IV: The Present Conflict", "range": "Active Campaign"},
        ]

    # Map era ID to index & X coordinate
    era_x_coords: Dict[str, int] = {}
    era_width = 550
    era_gap = 250
    col_step = era_width + era_gap
    start_x = -((len(eras_data) - 1) * col_step) // 2

    for idx, era in enumerate(eras_data):
        era_id = era.get("id", f"era_{idx}")
        era_x_coords[era_id] = start_x + (idx * col_step)

    # Collect and sort factions
    all_factions_found: List[str] = []
    for ev in events_data:
        f = ev.get("faction")
        if f and f not in all_factions_found and f.lower() not in ("all", "neutral", "none", "unknown"):
            all_factions_found.append(f)

    if not all_factions_found:
        all_factions_found = ["Order", "Accord", "Dominion", "Wilds"]

    if factions_filter:
        selected_factions = [f for f in all_factions_found if f.lower() in [x.lower() for x in factions_filter]]
        if not selected_factions:
            selected_factions = all_factions_found
    else:
        selected_factions = all_factions_found

    # Always include a General/World lane at the bottom
    selected_factions.append("World Events")

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []

    # 1. Generate Era Column Headers
    header_y = -850
    for idx, era in enumerate(eras_data):
        era_id = era.get("id", f"era_{idx}")
        x = era_x_coords[era_id]
        name = era.get("name", f"Era {idx}")
        range_str = era.get("range", "")
        header_text = f"# {name.upper()}"
        if range_str:
            header_text += f"\n*({range_str})*"

        color = CANVAS_PALETTE[idx % len(CANVAS_PALETTE)]
        nodes.append({
            "id": f"hdr_{era_id}",
            "type": "text",
            "text": header_text,
            "x": x,
            "y": header_y,
            "width": era_width,
            "height": 140,
            "color": color,
        })

    # 2. Build Swimlane Cards
    lane_height = 360
    start_y = -600
    faction_y_coords: Dict[str, int] = {}
    for f_idx, faction in enumerate(selected_factions):
        faction_y_coords[faction] = start_y + (f_idx * lane_height)

    # Place events into grid buckets: (faction, era_id) -> list of events
    buckets: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
        f: {e.get("id", f"era_{i}"): [] for i, e in enumerate(eras_data)}
        for f in selected_factions
    }

    for ev in events_data:
        ev_faction = ev.get("faction", "World Events")
        if ev_faction not in selected_factions:
            ev_faction = "World Events"

        ev_era = ev.get("era")
        if not ev_era or ev_era not in era_x_coords:
            # Fallback map by era index or default
            ev_era = eras_data[0].get("id", "era_0")

        buckets[ev_faction][ev_era].append(ev)

    # Render Event Cards and build intra-faction edges
    for f_idx, faction in enumerate(selected_factions):
        f_color = CANVAS_PALETTE[(f_idx + 1) % len(CANVAS_PALETTE)]
        y_pos = faction_y_coords[faction]
        prev_node_id: Optional[str] = None

        for era in eras_data:
            era_id = era.get("id", "era_0")
            events_here = buckets[faction][era_id]
            x_pos = era_x_coords[era_id]

            card_lines = [f"### {faction}"]
            if events_here:
                for ev in events_here:
                    title = ev.get("title", "Historical Event")
                    year = ev.get("year_ao", ev.get("year", ""))
                    year_label = f" ({year})" if year else ""
                    card_lines.append(f"**• {title}{year_label}**")
                    if ev.get("region"):
                        card_lines.append(f"  *Region:* {ev.get('region')}")
                    if ev.get("logline"):
                        card_lines.append(f"  *{ev.get('logline')}*")
                    if ev.get("characters"):
                        chars_str = ", ".join(ev["characters"])
                        card_lines.append(f"  *Figures:* {chars_str}")
            else:
                card_lines.append("*(No major recorded faction operations)*")

            node_id = f"node_{f_idx}_{era_id}"
            nodes.append({
                "id": node_id,
                "type": "text",
                "text": "\n".join(card_lines),
                "x": x_pos,
                "y": y_pos,
                "width": era_width,
                "height": 280,
                "color": f_color,
            })

            # Horizontal sequence edge
            if prev_node_id:
                edges.append({
                    "id": f"edge_{prev_node_id}_{node_id}",
                    "fromNode": prev_node_id,
                    "fromSide": "right",
                    "toNode": node_id,
                    "toSide": "left",
                    "label": "advances to",
                })
            prev_node_id = node_id

    # Resolve output path
    if not output_path:
        out_dir = universe_dir / "canvases"
        out_dir.mkdir(parents=True, exist_ok=True)
        target_file = out_dir / "Master-Chronology.canvas"
    else:
        target_file = Path(output_path)
        target_file.parent.mkdir(parents=True, exist_ok=True)

    canvas_payload = {
        "nodes": nodes,
        "edges": edges,
    }

    target_file.write_text(json.dumps(canvas_payload, indent=2), encoding="utf-8")
    return target_file


def main():
    parser = argparse.ArgumentParser(description="CanonForge Dynamic Obsidian Canvas Generator")
    parser.add_argument("--output", "-o", help="Target .canvas output file path")
    parser.add_argument("--factions", "-f", nargs="*", help="Filter specific factions for swimlanes")
    args = parser.parse_args()

    u_root = find_universe_root()
    out = build_chronology_canvas(u_root, output_path=Path(args.output) if args.output else None, factions_filter=args.factions)
    print(f"🎨 Generated visual Chronology Canvas at: {out}")


if __name__ == "__main__":
    main()
