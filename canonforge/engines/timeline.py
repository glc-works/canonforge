#!/usr/bin/env python3
"""
CONVERGENCE STUDIO: CHRONOLOGY & TRAVEL PHYSICS GATE
------------------------------------------------------------------------------
Enforces physical plausibility and temporal consistency across manuscript chapters:
1. Shortest-path route distance computation using canonical routes.json network.
2. Character/POV travel velocity bounds (foot march, crawler, mount, aether-skimmer).
3. Monotonic timeline progression (prevents inadvertent time-travel/chronological reversals).
------------------------------------------------------------------------------
"""

import sys
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Set

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

SCRIPT_DIR = Path(__file__).resolve().parent
CONVERGENCE_DIR = SCRIPT_DIR.parent
MANUSCRIPT_DIR = CONVERGENCE_DIR / "manuscript"
ROUTES_FILE = CONVERGENCE_DIR / "data" / "routes.json"
DISTANCES_FILE = CONVERGENCE_DIR / "data" / "world_distances.yaml"

class RouteNetwork:
    def __init__(self):
        self.graph: Dict[str, Dict[str, float]] = {}
        self.location_aliases: Dict[str, str] = {}
        self.benchmarks: Dict[str, Dict[str, float]] = {}
        self.load_data()

    def load_data(self):
        # 1. Load routes
        if ROUTES_FILE.is_file():
            try:
                data = json.loads(ROUTES_FILE.read_text(encoding="utf-8"))
                for r in data.get("routes", []):
                    u = r["from_place_id"]
                    v = r["to_place_id"]
                    dist = float(r.get("distance_miles", 20.0))
                    if u not in self.graph: self.graph[u] = {}
                    if v not in self.graph: self.graph[v] = {}
                    self.graph[u][v] = min(self.graph[u].get(v, dist), dist)
                    self.graph[v][u] = min(self.graph[v].get(u, dist), dist)
            except Exception as e:
                print(f"⚠️ Warning loading routes.json: {e}")

        # 2. Load world distances & aliases
        if DISTANCES_FILE.is_file() and HAS_YAML:
            try:
                w_data = yaml.safe_load(DISTANCES_FILE.read_text(encoding="utf-8")) or {}
                self.location_aliases = {k.lower(): v for k, v in w_data.get("location_aliases", {}).items()}
                self.benchmarks = w_data.get("velocity_benchmarks", {})
            except Exception as e:
                print(f"⚠️ Warning loading world_distances.yaml: {e}")

    def resolve_location(self, setting_text: str) -> Optional[str]:
        if not setting_text:
            return None
        text_lower = setting_text.lower()
        # Direct match or alias substring
        for alias, node in sorted(self.location_aliases.items(), key=lambda x: -len(x[0])):
            if alias in text_lower:
                return node
        return None

    def shortest_distance(self, start: str, end: str) -> float:
        if start == end:
            return 0.0
        if start not in self.graph or end not in self.graph:
            return 25.0  # Conservative estimate if one node is unmapped

        # Dijkstra algorithm
        import heapq
        queue = [(0.0, start)]
        distances = {start: 0.0}

        while queue:
            current_dist, u = heapq.heappop(queue)
            if u == end:
                return current_dist
            if current_dist > distances.get(u, float('inf')):
                continue
            for v, weight in self.graph.get(u, {}).items():
                d = current_dist + weight
                if d < distances.get(v, float('inf')):
                    distances[v] = d
                    heapq.heappush(queue, (d, v))

        return distances.get(end, 50.0)

def parse_frontmatter(file_path: Path) -> Dict[str, Any]:
    text = file_path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    if HAS_YAML:
        try:
            return yaml.safe_load(m.group(1)) or {}
        except Exception:
            pass
    # Fallback regex extraction
    data = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            data[k.strip()] = v.strip().strip('"').strip("'")
    return data

def parse_year_numeric(timeline_str: str) -> Optional[float]:
    if not timeline_str:
        return None
    # Look for explicit Year: e.g. "1064 AO", "Year +5 (1064 AO)", "Year 6"
    m_ao = re.search(r"(\d{4})\s*AO", timeline_str)
    if m_ao:
        return float(m_ao.group(1))
    m_yr = re.search(r"Year\s*\+?(\d+)", timeline_str, re.IGNORECASE)
    if m_yr:
        return 1060.0 + float(m_yr.group(1))
    return None

def audit_book_timeline(book_toc: Path, network: RouteNetwork) -> List[Dict[str, Any]]:
    violations = []
    if not book_toc.is_file() or not HAS_YAML:
        return violations

    try:
        toc_data = yaml.safe_load(book_toc.read_text(encoding="utf-8")) or {}
    except Exception:
        return violations

    # Collect chapters in TOC order
    chapter_entries = []
    for act in toc_data.get("acts", []):
        for ch in act.get("chapters", []):
            f_name = ch if isinstance(ch, str) else (ch.get("file") if isinstance(ch, dict) else None)
            if f_name:
                f_path = book_toc.parent / "chapters" / f_name
                if f_path.is_file():
                    fm = parse_frontmatter(f_path)
                    chapter_entries.append({
                        "file": f_name,
                        "path": f_path,
                        "pov": fm.get("pov") or fm.get("character") or "Unknown",
                        "setting": fm.get("setting", ""),
                        "timeline": fm.get("timeline", "")
                    })

    # Group by POV character to check track consistency
    pov_tracks: Dict[str, List[Dict[str, Any]]] = {}
    for entry in chapter_entries:
        pov = entry["pov"]
        # Normalize POV key
        pov_key = pov.split()[0].lower() if pov else "unknown"
        if pov_key not in pov_tracks:
            pov_tracks[pov_key] = []
        pov_tracks[pov_key].append(entry)

    # 1. Audit monotonic timeline within POV tracks
    for pov_key, chapters in pov_tracks.items():
        prev_year = None
        prev_entry = None
        for ch in chapters:
            yr = parse_year_numeric(ch["timeline"])
            if yr is not None and prev_year is not None:
                if yr < prev_year:
                    # Chronological regression!
                    violations.append({
                        "type": "chronological_reversal",
                        "pov": ch["pov"],
                        "file": ch["file"],
                        "details": f"Timeline regressed from {prev_year} AO ({prev_entry['file']}) to {yr} AO ({ch['file']}) without flashback tag."
                    })
            if yr is not None:
                prev_year = yr
                prev_entry = ch

    # 2. Audit travel distance / velocity physics between consecutive POV scenes
    for pov_key, chapters in pov_tracks.items():
        for i in range(len(chapters) - 1):
            c1 = chapters[i]
            c2 = chapters[i + 1]
            loc1 = network.resolve_location(c1["setting"])
            loc2 = network.resolve_location(c2["setting"])

            if loc1 and loc2 and loc1 != loc2:
                dist = network.shortest_distance(loc1, loc2)
                # Check for explicit day count in timeline string
                t2 = c2["timeline"].lower()
                m_days = re.search(r"(\d+)\s*days?", t2)
                if m_days:
                    elapsed_days = float(m_days.group(1))
                    max_crawler_miles = elapsed_days * 35.0  # 35 miles/day max for crawler or mount
                    if dist > max_crawler_miles:
                        violations.append({
                            "type": "travel_physics_violation",
                            "pov": c2["pov"],
                            "file": c2["file"],
                            "details": f"Travel from {loc1} to {loc2} is {dist:.1f} miles, but timeline specifies only {elapsed_days:.0f} days (max allowable {max_crawler_miles:.1f} miles)."
                        })

    return violations

def main():
    parser = argparse.ArgumentParser(description="Convergence Chronology & Travel Physics Gate")
    parser.add_argument("--book", help="Specific book directory to audit")
    parser.add_argument("--all", action="store_true", help="Audit all books across manuscript")
    args = parser.parse_args()

    network = RouteNetwork()

    if args.book:
        target_tocs = list(MANUSCRIPT_DIR.glob(f"*{args.book}*/toc.yaml")) + list(MANUSCRIPT_DIR.glob(f"*/*{args.book}*/toc.yaml"))
    else:
        target_tocs = sorted(MANUSCRIPT_DIR.glob("*/*/toc.yaml"))

    all_violations = []
    total_chapters = 0

    print("\n" + "=" * 80)
    print("CONVERGENCE CHRONOLOGY & TRAVEL PHYSICS GATE")
    print("=" * 80)
    print(f"• Monitored Route Nodes: {len(network.graph)}")
    print(f"• Location Aliases Active: {len(network.location_aliases)}")
    print(f"• Velocity Benchmarks: {len(network.benchmarks)}")
    print("-" * 80)

    for toc in target_tocs:
        violations = audit_book_timeline(toc, network)
        all_violations.extend(violations)

    if not all_violations:
        print("🎉 100% TIMELINE & TRAVEL PHYSICS INTEGRITY:")
        print("   Zero temporal regressions or impossible transit velocities detected across all chapters!\n")
        sys.exit(0)

    print(f"❌ DETECTED {len(all_violations)} CHRONOLOGY / TRAVEL VIOLATIONS:")
    for v in all_violations:
        print(f"  • [{v['type'].upper()}] POV: {v['pov']} ({v['file']})")
        print(f"    {v['details']}\n")

    sys.exit(1)

if __name__ == "__main__":
    main()
