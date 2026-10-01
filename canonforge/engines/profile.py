#!/usr/bin/env python3
"""
CANONFORGE ENGINE: CHARACTER INTELLIGENCE DOSSIER & PROFILER
--------------------------------------------------------------------------------
Synthesizes SSOT Lore Cards, Biometric Invariants, RPG Combat Attributes,
Relational Social Topologies, and Manuscript Telemetry into a unified dossier.

Zero Creative IP Contamination: All invariants, attributes, and relationships
are loaded dynamically from the active universe's manifests and wiki records.
--------------------------------------------------------------------------------
"""

import sys
import os
import re
import json
import sqlite3
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from collections import Counter

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from canonforge.core.manifest import find_universe_root


def parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter and body from markdown."""
    fm: Dict[str, Any] = {}
    body = text
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if match:
        body = text[match.end():]
        raw_yaml = match.group(1)
        if HAS_YAML:
            try:
                parsed = yaml.safe_load(raw_yaml)
                if isinstance(parsed, dict):
                    fm = parsed
            except Exception:
                pass
        if not fm:
            for line in raw_yaml.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm, body


def find_character_wiki(query: str, universe_dir: Path) -> Optional[Dict[str, Any]]:
    """Scan universe wiki directory for character lore cards."""
    wiki_dir = universe_dir / "wiki"
    if not wiki_dir.exists():
        return None

    candidate_dirs = [
        wiki_dir / "terms" / "characters",
        wiki_dir / "characters",
        wiki_dir / "terms" / "people",
        wiki_dir,
    ]

    all_files: List[Path] = []
    for cd in candidate_dirs:
        if cd.exists():
            all_files.extend(list(cd.glob("*.md")) + list(cd.glob("**/*.md")))
    all_files = sorted(list(set(all_files)))

    q_clean = query.strip().lower()

    # 1. Exact match by filename stem or title
    matched_file: Optional[Path] = None
    for f in all_files:
        stem_clean = f.stem.lower().replace("-", " ").replace("_", " ")
        if stem_clean == q_clean or f.stem.lower() == q_clean:
            matched_file = f
            break

    # 2. Check exact title or exact alias match in frontmatter
    if not matched_file:
        for f in all_files:
            text = f.read_text(encoding="utf-8", errors="ignore")
            fm, _ = parse_frontmatter(text)
            title = fm.get("title", "").strip().lower()
            aliases = [str(a).strip().lower() for a in fm.get("aliases", []) if isinstance(a, str)]
            if q_clean == title or q_clean in aliases:
                matched_file = f
                break

    # 3. Prefix match (e.g. "elena" matching "elena-the-navigator")
    if not matched_file:
        prefix_matches = [
            f for f in all_files
            if f.stem.lower().startswith(q_clean + "-") or f.stem.lower().startswith(q_clean + "_")
        ]
        if prefix_matches:
            prefix_matches.sort(key=lambda x: len(x.stem))
            matched_file = prefix_matches[0]

    # 4. General substring match (shorter stem preferred)
    if not matched_file:
        candidates = [f for f in all_files if q_clean in f.stem.lower().replace("-", " ")]
        if candidates:
            candidates.sort(key=lambda x: (len(x.stem), x.stem))
            matched_file = candidates[0]

    if not matched_file:
        return None

    text = matched_file.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)

    # Extract bio paragraph
    bio_lines = []
    for line in body.splitlines():
        line_s = line.strip()
        if line_s.startswith(">") or line_s.startswith("#") or not line_s:
            continue
        if len(line_s) > 35:
            bio_lines.append(line_s)
            if len(bio_lines) >= 2:
                break
    bio_summary = " ".join(bio_lines)

    invariants = fm.get("invariants", {})
    if not isinstance(invariants, dict):
        invariants = {}

    return {
        "file_name": matched_file.name,
        "file_path": str(matched_file),
        "title": fm.get("title", matched_file.stem.replace("-", " ").title()),
        "id": fm.get("id", f"char_{matched_file.stem.lower().replace('-', '_')}"),
        "house": fm.get("house", "Independent / Common"),
        "faction": fm.get("faction", "Unaligned"),
        "role": fm.get("role", "Character"),
        "birth_date": str(fm.get("birth_date", "Unknown")),
        "birth_race": fm.get("birth_race", "Standard"),
        "biological_state": fm.get("biological_state", "Pure Flesh"),
        "status": fm.get("entity_status", fm.get("status", "Active")),
        "labels": fm.get("labels", []),
        "invariants": invariants,
        "bio_summary": bio_summary,
        "full_fm": fm,
    }


def load_character_db_stats(char_id: str, char_name: str, universe_dir: Path) -> Dict[str, Any]:
    """Query SQLite database for character stats and metadata if available."""
    db_paths = [
        universe_dir / "data" / "game_world.db",
        universe_dir / "data" / "world.db",
    ]
    for db_path in db_paths:
        if db_path.exists():
            try:
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute(
                    "SELECT * FROM characters WHERE char_id = ? OR name LIKE ? LIMIT 1;",
                    (char_id, f"%{char_name}%"),
                )
                row = cur.fetchone()
                base_data = dict(row) if row else {}

                combat_data = {}
                try:
                    cur.execute(
                        "SELECT * FROM v_character_combat_stats WHERE char_id = ? LIMIT 1;",
                        (char_id,),
                    )
                    c_row = cur.fetchone()
                    if c_row:
                        combat_data = dict(c_row)
                except Exception:
                    pass

                conn.close()
                if base_data or combat_data:
                    return {**base_data, **combat_data}
            except Exception:
                pass
    return {}


def get_social_topology(char_name: str, universe_dir: Path) -> Dict[str, Any]:
    """Extract relational connections, allies, and rivals."""
    try:
        from canonforge.engines import relations as cr
        rel_data = cr.load_relationships_data()
        if not rel_data:
            return {}
        all_chars = cr.get_all_characters(rel_data)
        resolved = cr.resolve_character_name(char_name, all_chars)
        if not resolved:
            return {}
        graph = cr.build_adjacency_graph(rel_data)
        edges = graph.get(resolved, [])
        allies = [e for e in edges if e.get("sentiment", 0) >= 0.6]
        rivals = [e for e in edges if e.get("sentiment", 0) <= -0.2]
        return {
            "resolved_name": resolved,
            "total_connections": len(edges),
            "allies": allies,
            "rivals": rivals,
        }
    except Exception:
        return {}


def get_manuscript_footprint(char_name: str, universe_dir: Path) -> Dict[str, Any]:
    """Calculate appearance count and co-occurring cast across manuscript."""
    db_paths = [
        universe_dir / "data" / "metrics_cache.db",
        universe_dir / "data" / "game_world.db",
    ]
    for db_path in db_paths:
        if db_path.exists():
            try:
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                cur.execute("SELECT file_name, book_slug, top_chars_json FROM chapter_metrics;")
                rows = cur.fetchall()
                conn.close()

                appearances = 0
                books_counter: Counter = Counter()
                co_chars_counter: Counter = Counter()
                clean_target_first = char_name.split()[0].lower().strip(",.")

                for fname, bslug, top_chars_raw in rows:
                    if not top_chars_raw:
                        continue
                    try:
                        top_chars = json.loads(top_chars_raw)
                        present_names = [c[0] for c in top_chars]
                        is_present = False
                        for p_name in present_names:
                            p_first = p_name.split()[0].lower().strip(",.")
                            if clean_target_first == p_first or clean_target_first in p_name.lower():
                                is_present = True
                                break
                        if is_present:
                            appearances += 1
                            books_counter[bslug] += 1
                            for p_name in present_names:
                                p_first = p_name.split()[0].lower().strip(",.")
                                if clean_target_first != p_first:
                                    co_chars_counter[p_name] += 1
                    except Exception:
                        pass

                return {
                    "appearances": appearances,
                    "books": dict(books_counter),
                    "co_occurring": co_chars_counter.most_common(4),
                }
            except Exception:
                pass

    return {"appearances": 0, "books": {}, "co_occurring": []}


def calculate_age(birth_date: str, target_year: Optional[int] = None) -> str:
    """Calculate character's exact age in a given calendar year."""
    if not birth_date or birth_date.lower() in ("unknown", "none"):
        return "Unknown"
    match = re.match(r"^(\d{4})", birth_date.strip())
    if match and target_year:
        birth_year = int(match.group(1))
        age = target_year - birth_year
        return f"{age} winters old (in year {target_year})"
    elif match:
        return f"Born {match.group(1)}"
    return birth_date


def print_dossier(wiki: Dict[str, Any], db: Dict[str, Any], rel: Dict[str, Any], foot: Dict[str, Any], target_year: Optional[int] = None):
    """Format and print an exhaustive intelligence profile dossier."""
    name = wiki.get("title", "Unknown Entity")
    char_id = wiki.get("id", db.get("char_id", "N/A"))
    invariants = wiki.get("invariants", {})
    status = wiki.get("status", "Active")
    status_badge = "🟢 ACTIVE" if "active" in status.lower() else f"🔴 {status.upper()}"

    age_str = calculate_age(wiki.get("birth_date", db.get("birthday", "")), target_year)

    print("\n" + "=" * 80)
    print(f"  🗂️  INTELLIGENCE DOSSIER: {name.upper()}")
    print(f"      Entity ID: {char_id} | Status: {status_badge}")
    print("=" * 80)

    # 1. Vital Records & Lineage
    print("\n📋 SECTION 1: VITAL RECORDS & LINEAGE")
    print(f"  • Canonical Name      : {name}")
    print(f"  • House / Faction     : {wiki.get('house', 'None')} | {wiki.get('faction', 'Independent')}")
    print(f"  • Role & Narrative Tier: {wiki.get('role', 'Story Character')}")
    print(f"  • Chronological Age   : {age_str}")
    print(f"  • Biological State    : {wiki.get('biological_state', 'Pure Flesh')} ({wiki.get('birth_race', 'Standard')})")

    # 2. Biometric Invariants & Continuity
    print("\n👁️  SECTION 2: BIOMETRIC INVARIANTS & CONTINUITY GUARD")
    if invariants:
        valid_eyes = invariants.get("valid_eye_colors", [])
        if valid_eyes:
            print(f"  • Eye Color           : {', '.join(valid_eyes)}")
        forbidden_eyes = invariants.get("forbidden_eye_colors", [])
        if forbidden_eyes:
            print(f"  • Forbidden Eye Colors: 🚫 {', '.join(forbidden_eyes)}")
        if "hair_color" in invariants:
            print(f"  • Hair Color          : {invariants['hair_color']}")
        if "scar_location" in invariants:
            print(f"  • Signature Mark/Scar : ⚡ {invariants['scar_location']}")
        if "signature_weapon" in invariants:
            print(f"  • Signature Weapon    : ⚔️  {invariants['signature_weapon']}")
        if "bound_animus" in invariants:
            print(f"  • Bound Spirit/Relic  : ✨ {invariants['bound_animus']}")
        if "forbidden_traits" in invariants:
            print(f"  • Anti-Drift Guard    : 🚫 Prohibited: {', '.join(invariants['forbidden_traits'])}")
    else:
        print("  • Standard biometrics active. No high-risk physical drift rules flagged for this entity.")

    # 3. Narrative Synopsis
    if wiki.get("bio_summary"):
        print("\n📖 SECTION 3: CANONICAL DOSSIER SYNOPSIS")
        print(f"  \"{wiki['bio_summary']}\"")

    # 4. RPG Combat Attributes
    if db:
        print("\n⚔️  SECTION 4: RPG COMBAT ATTRIBUTES & PROGRESSION")
        level = db.get("level", 1)
        hp = db.get("max_hp", db.get("base_hp", 100))
        str_ = db.get("strength", 10)
        dex_ = db.get("dexterity", 10)
        vit_ = db.get("vitality", 10)
        wil_ = db.get("willpower", 10)
        force_ = db.get("force_resonance", db.get("force_power", 0))
        print(f"  • Level: {level} | HP: {hp} | State: {wiki.get('biological_state', 'Pure Flesh')}")
        print(f"  • Core Attributes: STR {str_} | DEX {dex_} | VIT {vit_} | WIL {wil_} | POWER {force_}")

    # 5. Relational Topology
    if rel and rel.get("total_connections", 0) > 0:
        print("\n🕸️  SECTION 5: SOCIAL TOPOLOGY & RELATIONAL RADAR")
        print(f"  • Total Direct Connections : {rel['total_connections']} canonical bond(s)")
        if rel.get("allies"):
            ally_str = ", ".join([f"{e.get('target', 'Unknown')} (+{e.get('sentiment', 0):.2f})" for e in rel["allies"][:3]])
            print(f"  • Key Allies & Protectors   : 🟢 {ally_str}")
        if rel.get("rivals"):
            rival_str = ", ".join([f"{e.get('target', 'Unknown')} ({e.get('sentiment', 0):.2f})" for e in rel["rivals"][:3]])
            print(f"  • Antagonists & Enmities    : 🔴 {rival_str}")

    # 6. Manuscript Footprint
    if foot and foot.get("appearances", 0) > 0:
        print("\n📊 SECTION 6: MANUSCRIPT FOOTPRINT & TELEMETRY")
        print(f"  • Documented Appearances   : {foot['appearances']} chapter(s) across the saga")
        if foot.get("books"):
            b_summary = ", ".join([f"{b}: {c} chs" for b, c in foot["books"].items()])
            print(f"  • Distribution by Book     : {b_summary}")
        if foot.get("co_occurring"):
            co_str = ", ".join([f"{c} ({cnt}x)" for c, cnt in foot["co_occurring"]])
            print(f"  • Top Scene Partners       : 👥 {co_str}")

    print("=" * 80 + "\n")


def build_profile(target: str, universe_dir: Optional[Path] = None, target_year: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Build complete character profile data structure."""
    u_root = universe_dir or find_universe_root()
    wiki_data = find_character_wiki(target, u_root)
    if not wiki_data:
        return None
    db_data = load_character_db_stats(wiki_data["id"], wiki_data["title"], u_root)
    rel_data = get_social_topology(wiki_data["title"], u_root)
    footprint = get_manuscript_footprint(wiki_data["title"], u_root)
    return {
        "wiki": wiki_data,
        "game_db": db_data,
        "relations": rel_data,
        "footprint": footprint,
    }


def main():
    parser = argparse.ArgumentParser(description="CanonForge Character Profiling & Intelligence Dossier Engine")
    parser.add_argument("target", nargs="?", help="Character name or query")
    parser.add_argument("--year", "-y", type=int, help="Target year for chronological age calculation")
    parser.add_argument("--json", action="store_true", help="Output raw JSON profiling object")
    args = parser.parse_args()

    if not args.target:
        print("\nUsage: cf profile <character_name> [--year YYYY] [--json]\n")
        return

    u_root = find_universe_root()
    profile = build_profile(args.target, u_root, target_year=args.year)
    if not profile:
        print(f"❌ Character '{args.target}' not found in canonical wiki records.")
        sys.exit(1)

    if args.json:
        # Convert non-serializable objects
        print(json.dumps(profile, indent=2, default=str))
    else:
        print_dossier(profile["wiki"], profile["game_db"], profile["relations"], profile["footprint"], target_year=args.year)


if __name__ == "__main__":
    main()
