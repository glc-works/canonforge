#!/usr/bin/env python3
"""
CANONFORGE ENGINE: CHRONOLOGY QUERY & WORLD-STATE ENGINE
--------------------------------------------------------------------------------
Authoritative timeline, age, and historical world-state query engine.
Eliminates mental math for authors and validates historical consistency across eras:
- Query by Year: Active living cast, ages, events, births, and deceased figures.
- Query by Character: Chronological trajectory across all canonical epochs.

Zero Creative IP Contamination: All calendar systems, anchor years, eras, and
entities are loaded dynamically from the active universe's manifests.
--------------------------------------------------------------------------------
"""

import sys
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from canonforge.core.manifest import find_universe_root


def parse_year(date_str: Any) -> Optional[int]:
    """Parse 4-digit calendar year from date string or integer."""
    if not date_str:
        return None
    if isinstance(date_str, int):
        return date_str
    m = re.match(r"^(\d{4})", str(date_str).strip())
    if m:
        return int(m.group(1))
    return None


def load_universe_chronology(universe_dir: Path) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Load timeline events and character lifespan records dynamically."""
    data_dir = universe_dir / "data"
    timeline_data: Dict[str, Any] = {}

    # 1. Load timeline.json / timeline.yaml
    for candidate in [data_dir / "timeline.json", data_dir / "timeline.yaml", data_dir / "chronology.json"]:
        if candidate.exists():
            try:
                if candidate.suffix == ".json":
                    timeline_data = json.loads(candidate.read_text(encoding="utf-8"))
                elif HAS_YAML:
                    timeline_data = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
                break
            except Exception as e:
                print(f"⚠️ Warning loading {candidate.name}: {e}")

    # 2. Load characters from data/characters.json or scan wiki/
    characters: List[Dict[str, Any]] = []
    chars_json = data_dir / "characters.json"
    if chars_json.exists():
        try:
            c_data = json.loads(chars_json.read_text(encoding="utf-8"))
            raw_chars = c_data.get("characters", c_data if isinstance(c_data, list) else [])
            for rc in raw_chars:
                characters.append({
                    "name": rc.get("char_name", rc.get("name", "Unknown")),
                    "birth_year": parse_year(rc.get("birthday", rc.get("birth_date"))),
                    "birth_date": rc.get("birthday", rc.get("birth_date", "")),
                    "death_year": parse_year(rc.get("death_date")),
                    "house": rc.get("house", "Independent"),
                    "faction": rc.get("faction", "Neutral"),
                    "role": rc.get("role", "Character"),
                })
        except Exception:
            pass

    # If characters list is empty, scan wiki cards
    if not characters:
        wiki_dir = universe_dir / "wiki"
        if wiki_dir.exists():
            for f in wiki_dir.glob("**/*.md"):
                text = f.read_text(encoding="utf-8", errors="ignore")
                match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
                if match:
                    raw_yaml = match.group(1)
                    fm = {}
                    if HAS_YAML:
                        try:
                            fm = yaml.safe_load(raw_yaml) or {}
                        except Exception:
                            pass
                    if not fm:
                        for line in raw_yaml.splitlines():
                            if ":" in line:
                                k, v = line.split(":", 1)
                                fm[k.strip()] = v.strip().strip('"').strip("'")

                    if fm.get("type") in ("Character Entity", "Character") or "char" in fm.get("id", "") or "character" in str(fm.get("labels", "")):
                        characters.append({
                            "name": fm.get("title", f.stem.replace("-", " ").title()),
                            "birth_year": parse_year(fm.get("birth_date")),
                            "birth_date": str(fm.get("birth_date", "")),
                            "death_year": parse_year(fm.get("death_date")),
                            "house": fm.get("house", "Independent"),
                            "faction": fm.get("faction", "Neutral"),
                            "role": fm.get("role", "Character"),
                        })

    return timeline_data, characters


def query_year(target_year: int, timeline: Dict[str, Any], characters: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate world state, active cast, and events for a given calendar year."""
    calendar = timeline.get("calendar", {})
    system_name = calendar.get("system", "Calendar Year")
    anchor_year = calendar.get("crossing_anchor_year", calendar.get("anchor_year"))

    epoch_label = ""
    if anchor_year is not None:
        delta = target_year - anchor_year
        if delta == 0:
            epoch_label = "Anchor Year 0"
        elif delta > 0:
            epoch_label = f"Anchor +{delta}"
        else:
            epoch_label = f"Anchor {delta}"

    # Filter events
    events = [e for e in timeline.get("events", []) if e.get("year_ao", e.get("year")) == target_year]

    living = []
    born_this_year = []
    deceased = []
    unborn = []

    for c in characters:
        name = c["name"]
        byear = c["birth_year"]
        dyear = c["death_year"]
        house = c["house"]
        faction = c["faction"]

        if byear is None:
            continue

        if target_year < byear:
            unborn.append({"name": name, "years_until_birth": byear - target_year})
        elif target_year == byear:
            born_this_year.append({"name": name, "house": house, "faction": faction})
        elif dyear and target_year > dyear:
            deceased.append({"name": name, "years_since_death": target_year - dyear})
        else:
            age = target_year - byear
            living.append({"name": name, "age": age, "house": house, "faction": faction})

    living.sort(key=lambda x: -x["age"])

    return {
        "year": target_year,
        "system": system_name,
        "epoch_label": epoch_label,
        "events": events,
        "living": living,
        "born_this_year": born_this_year,
        "deceased": deceased,
        "unborn_count": len(unborn),
    }


def query_character(query: str, timeline: Dict[str, Any], characters: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Query lifespan status across key canon epochs for a character."""
    q_clean = query.strip().lower()
    matches = [c for c in characters if q_clean in c["name"].lower()]
    if not matches:
        return None

    c = matches[0]
    byear = c["birth_year"]
    dyear = c["death_year"]

    eras = timeline.get("eras", [])
    milestones = []
    for era in eras:
        name = era.get("name", "Era")
        range_str = era.get("range", "")
        # Try to parse start year from range
        m = re.search(r"(\d{4})", range_str)
        yr = int(m.group(1)) if m else byear
        milestones.append((name, yr))

    if not milestones and byear:
        milestones = [("Birth", byear), ("Mid-Era", byear + 20), ("Mature Era", byear + 40)]

    status_progression = []
    for label, yr in milestones:
        if byear is None:
            status = "Unknown birth year"
        elif yr < byear:
            status = f"Unborn (born in {byear - yr} yrs)"
        elif dyear and yr > dyear:
            status = f"Deceased (died at age {dyear - byear})"
        else:
            status = f"Age {yr - byear} years"
        status_progression.append({"epoch": label, "year": yr, "status": status})

    return {
        "character": c,
        "milestones": status_progression,
    }


def print_year_report(data: Dict[str, Any]):
    """Format and print world-state inventory for target year."""
    system = data["system"]
    yr = data["year"]
    epoch = f" ({data['epoch_label']})" if data["epoch_label"] else ""

    print("=" * 75)
    print(f"WORLD STATE INVENTORY: YEAR {yr} {system}{epoch}")
    print("=" * 75)

    events = data["events"]
    print(f"\n📜 HISTORICAL EVENTS IN YEAR {yr}:")
    if events:
        for ev in events:
            title = ev.get("title", "Event")
            season = ev.get("season", "Season")
            region = ev.get("region", "World")
            faction = ev.get("faction", "Unaligned")
            logline = ev.get("logline", "")
            print(f"  • [{season}] {title}")
            print(f"    Region: {region} | Faction: {faction}")
            if logline:
                print(f"    Logline: {logline}")
            if ev.get("characters"):
                print(f"    Figures: {', '.join(ev['characters'])}")
    else:
        print("  (No recorded catastrophic nexus events logged in master ledger for this year)")

    living = data["living"]
    print("\n" + "-" * 75)
    print(f"👥 ACTIVE CHARACTERS & AGES IN YEAR {yr} ({len(living)} living):")
    print("-" * 75)

    for item in living:
        print(f"  [{item['age']:>2} yrs] {item['name']:<35} ({item['house']}, {item['faction']})")

    if data["born_this_year"]:
        print(f"\n👶 BORN THIS YEAR ({len(data['born_this_year'])}):")
        for b in data["born_this_year"]:
            print(f"  • {b['name']} ({b['house']}, {b['faction']})")

    if data["deceased"]:
        print(f"\n✝ DECEASED PRIOR TO YEAR {yr} ({len(data['deceased'])}):")
        for d in data["deceased"][:8]:
            print(f"  • {d['name']} (Died {d['years_since_death']} yrs ago)")
        if len(data["deceased"]) > 8:
            print(f"  ... and {len(data['deceased']) - 8} other historical figures.")

    print("=" * 75 + "\n")


def print_character_report(data: Dict[str, Any]):
    """Format and print character chronology profile."""
    c = data["character"]
    print("=" * 75)
    print(f"CHRONOLOGY PROFILE: {c['name'].upper()}")
    print("=" * 75)
    print(f"• House / Faction: {c['house']} / {c['faction']}")
    print(f"• Narrative Role:  {c['role']}")
    print(f"• Canonical Birth: {c['birth_date'] or 'Unknown'}")
    if c.get("death_year"):
        print(f"• Canonical Death: Year {c['death_year']}")

    print("\nLifespan Status Across Key Canon Epochs:")
    for m in data["milestones"]:
        print(f"  • {m['epoch']:<32} ({m['year']}): {m['status']}")
    print("=" * 75 + "\n")


def main():
    parser = argparse.ArgumentParser(description="CanonForge Chronology & World-State Engine")
    parser.add_argument("--year", "-y", type=int, help="Query world state, cast ages, and events for a given calendar year")
    parser.add_argument("--character", "-c", type=str, help="Query lifespan status across key canon epochs for a character")
    parser.add_argument("--json", action="store_true", help="Output raw JSON data")
    args = parser.parse_args()

    u_root = find_universe_root()
    timeline, characters = load_universe_chronology(u_root)

    if args.character:
        res = query_character(args.character, timeline, characters)
        if not res:
            print(f"❌ Character '{args.character}' not found in canonical records.")
            sys.exit(1)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print_character_report(res)
    elif args.year is not None:
        res = query_year(args.year, timeline, characters)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print_year_report(res)
    else:
        # Check calendar anchor or default year 1058
        cal = timeline.get("calendar", {})
        def_yr = cal.get("crossing_anchor_year", 1058)
        res = query_year(def_yr, timeline, characters)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print_year_report(res)


if __name__ == "__main__":
    main()
