"""
Command line interface for character relations engine
"""
import sys
import argparse
from pathlib import Path
from canonforge.engines.relations.timeline import (
    load_relationships_data, get_all_characters, resolve_character_name
)
from canonforge.engines.relations.graph import (
    inspect_character_relations, find_relationship_path
)
from canonforge.engines.relations.matrix import (
    build_cast_matrix, audit_chapter_relations
)
from canonforge.engines.relations.exporter import (
    export_mermaid_diagram, sync_relationships_to_db
)
from canonforge.engines.relations.mutations import (
    check_relationship_exists, add_relationship, update_relationship, add_timeline_slice
)

def main():
    parser = argparse.ArgumentParser(description="CanonForge Character Relationship Graph & Dual-Anchor Continuity Engine")
    parser.add_argument("target", nargs="?", help="Character name or action (path, matrix, audit, exists, add, update, timeline)")
    parser.add_argument("extra", nargs="*", help="Secondary character names or target file")
    parser.add_argument("--year", "-y", type=int, help="Historical timeline year (e.g. 1050, 1055, 1064)")
    parser.add_argument("--book", "-b", type=int, help="Book number (e.g. 1, 2, 3, 4)")
    parser.add_argument("--chapter", "-c", type=int, help="Chapter number (e.g. 18, 23, 26)")
    parser.add_argument("--story", help="Story slug (e.g. the-sun-sanctum-champion, the-stone-child)")
    parser.add_argument("--type", "-t", help="Relationship type (kinship, alliance, comrade, romance, rivalry, tension, mentorship, bond, feud)")
    parser.add_argument("--sub-type", help="Specific relationship sub-type (e.g. devoted_siblings, smuggler_contract)")
    parser.add_argument("--sentiment", type=float, help="Affinity score from -1.0 (mortal enemy) to +1.0 (devoted/loyal)")
    parser.add_argument("--symmetry", choices=["directed", "symmetric"], default="directed", help="Symmetry mode")
    parser.add_argument("--state", help="Active dynamic tension or status")
    parser.add_argument("--notes", help="Permanent canonical background notes")
    parser.add_argument("--event", help="Trigger event for milestone slice")
    parser.add_argument("--rule", help="Strict narrative writing rule for author/LLM")
    parser.add_argument("--phase", help="Intra-chapter phase (e.g. pre, post, opening, climax)")
    parser.add_argument("--scene", type=int, help="Specific scene number within chapter")
    parser.add_argument("--mermaid", "-m", action="store_true", help="Export Mermaid.js diagram")
    parser.add_argument("--sync-db", "-s", action="store_true", help="Sync relationships into SQLite database")
    
    args = parser.parse_args()
    data = load_relationships_data()
    
    if args.sync_db:
        sync_relationships_to_db(data)
        return
        
    if args.mermaid:
        mmd = export_mermaid_diagram(data, ao_year=args.year)
        print(mmd)
        return
        
    if not args.target:
        all_chars = get_all_characters(data)
        print("\n" + "=" * 75)
        print("  CANONFORGE CHARACTER RELATIONSHIP DUAL-ANCHOR ENGINE")
        print("=" * 75)
        print(f"• Total Canonical Relationships : {len(data.get('relationships', []))}")
        print(f"• Registered Characters in Graph: {len(all_chars)}")
        print("\nInspection Commands:")
        print("  ./cf relations <character>             : Inspect baseline / latest state")
        print("  ./cf relations <char> --chapter 18 -b 4: Inspect state at Book 4 Chapter 18")
        print("  ./cf relations <char> --year 1055      : Inspect state at 1055 AO (Historical)")
        print("  ./cf relations exists <char_a> <char_b>: Topology existence vs typology separation")
        print("  ./cf relations exists <c1> <c2> -b 1 -c 9: Check turning points within a chapter")
        print("  ./cf relations path <char_a> <char_b>  : Find shortest relational path")
        print("  ./cf relations matrix <c1> <c2> <c3>   : Show ensemble cross-matrix")
        print("  ./cf relations audit <chapter.md>      : Audit chapter interpersonal dynamics")
        print("\nAuthoring & CRUD Commands:")
        print("  ./cf relations add <c1> <c2> --type alliance --sentiment 0.8 --state \"Pact formed\"")
        print("  ./cf relations update <c1> <c2> --sentiment -0.5 --state \"Betrayal revealed\"")
        print("  ./cf relations update <c1> <c2> -b 1 -c 9 --phase post --sentiment -1.0")
        print("  ./cf relations timeline <c1> <c2> -b 4 -c 20 --sentiment 0.9 --rule \"Reconciled\"")
        print("  ./cf relations --mermaid               : Print Mermaid diagram")
        print("  ./cf relations --sync-db               : Sync into SQLite DB")
        print("=" * 75 + "\n")
        return
        
    cmd = args.target.lower()
    
    if cmd == "exists":
        if len(args.extra) < 2:
            print("❌ Exists command requires two character names: `./cf relations exists <char_a> <char_b>`")
            return
        check_relationship_exists(
            args.extra[0],
            args.extra[1],
            data,
            ao_year=args.year,
            book=args.book,
            chapter=args.chapter,
            story=args.story,
            phase=args.phase,
            scene=args.scene
        )
    elif cmd == "add":
        if len(args.extra) < 2:
            print("❌ Add command requires two character names: `./cf relations add <char_a> <char_b> --type <type>`")
            return
        if not args.type:
            print("❌ Add command requires `--type <type>` (e.g. kinship, alliance, mentorship, feud, romance, tension).")
            return
        add_relationship(
            args.extra[0],
            args.extra[1],
            relation_type=args.type,
            sub_type=args.sub_type or "",
            sentiment=args.sentiment if args.sentiment is not None else 0.0,
            symmetry=args.symmetry,
            dynamic_state=args.state or "",
            notes=args.notes or "",
            data=data
        )
    elif cmd == "update":
        if len(args.extra) < 2:
            print("❌ Update command requires two character names: `./cf relations update <char_a> <char_b>`")
            return
        update_relationship(
            args.extra[0],
            args.extra[1],
            sentiment=args.sentiment,
            dynamic_state=args.state,
            relation_type=args.type,
            sub_type=args.sub_type,
            notes=args.notes,
            rule=args.rule,
            ao_year=args.year,
            book=args.book,
            chapter=args.chapter,
            phase=args.phase,
            scene=args.scene,
            story=args.story,
            data=data
        )
    elif cmd == "timeline":
        if len(args.extra) < 2:
            print("❌ Timeline command requires two character names: `./cf relations timeline <char_a> <char_b>`")
            return
        anchor_type = "chapter" if (args.book or args.chapter) else "chronological"
        slice_data = {
            "anchor_type": anchor_type,
            "ao_year_start": args.year,
            "ao_year_end": args.year,
            "story": args.story,
            "book": args.book,
            "from_ch": args.chapter or 1,
            "to_ch": args.chapter,
            "phase": args.phase.lower() if args.phase else None,
            "scene": args.scene,
            "relation_type": args.type or "alliance",
            "sub_type": args.sub_type or "",
            "sentiment": args.sentiment if args.sentiment is not None else 0.0,
            "trigger_event": args.event or args.state or "Milestone reached",
            "narrative_rule": args.rule or ""
        }
        slice_data = {k: v for k, v in slice_data.items() if v is not None}
        add_timeline_slice(args.extra[0], args.extra[1], slice_data, data=data)
    elif cmd == "path":
        if len(args.extra) < 2:
            print("❌ Path command requires two character names: `./cf relations path <char_a> <char_b>`")
            return
        find_relationship_path(args.extra[0], args.extra[1], data, ao_year=args.year)
    elif cmd == "matrix":
        if not args.extra:
            print("❌ Matrix command requires at least two character names: `./cf relations matrix <c1> <c2> ...`")
            return
        build_cast_matrix(args.extra, data, ao_year=args.year)
    elif cmd == "audit":
        if not args.extra:
            print("❌ Audit command requires a chapter file: `./cf relations audit <chapter.md>`")
            return
        audit_chapter_relations(Path(args.extra[0]), data)
    else:
        # Default: inspect character with optional time anchor
        inspect_character_relations(
            args.target,
            data,
            ao_year=args.year,
            book=args.book,
            chapter=args.chapter,
            story=args.story,
            phase=args.phase,
            scene=args.scene
        )

if __name__ == "__main__":
    main()

