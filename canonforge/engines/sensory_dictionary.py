"""
sensory_dictionary.py

Backward-compatible facade for canonforge.engines.sensory.dictionary.
"""

from canonforge.engines.sensory.dictionary import (
    SensoryLexeme,
    SensoryDictionary,
    get_dictionary,
)

__all__ = ["SensoryLexeme", "SensoryDictionary", "get_dictionary", "main"]

def main():
    import sys
    import argparse
    parser = argparse.ArgumentParser(description="CanonForge Sensory Dictionary & Knowledge Graph")
    parser.add_argument("query", nargs="?", default=None, help="Word or lemma to look up")
    parser.add_argument("--validate-graph", action="store_true", help="Validate bidirectionality of synonyms/antonyms")
    parser.add_argument("--synonyms", help="Find synonyms for a lemma")
    parser.add_argument("--antonyms", help="Find antonyms for a lemma")
    args = parser.parse_args()

    d = get_dictionary()

    if args.validate_graph:
        v = d.validate_graph_integrity()
        print("\n" + "=" * 80)
        print("SENSORY KNOWLEDGE GRAPH: INTEGRITY VALIDATION")
        print("=" * 80)
        print(f"• Total Synonym Links Checked  : {v['total_syn_links']}")
        print(f"• Total Antonym Links Checked  : {v['total_ant_links']}")
        print(f"• Total Lore Aliases Indexed   : {v['total_alias_links']}")
        if v["valid"]:
            print("✅ 100% GRAPH INTEGRITY: All referenced synonyms and antonyms resolve cleanly!")
            print("=" * 80 + "\n")
            return 0
        else:
            print("❌ GRAPH INTEGRITY VIOLATIONS DETECTED:")
            if v["missing_synonyms"]:
                print("  Missing Synonyms:")
                for k, ms in v["missing_synonyms"].items():
                    print(f"    - {k} -> {ms}")
            if v["missing_antonyms"]:
                print("  Missing Antonyms:")
                for k, ma in v["missing_antonyms"].items():
                    print(f"    - {k} -> {ma}")
            print("=" * 80 + "\n")
            return 1

    if args.query:
        hit = d.lookup(args.query)
        if hit:
            print(f"\n📖 SENSORY DICTIONARY ENTRY: '{args.query}'")
            print(f"  • Canonical Lemma : {hit.lemma}")
            print(f"  • Senses Triggered: {', '.join(hit.senses)}")
            print(f"  • Part of Speech  : {hit.pos}")
            print(f"  • Intensity Level : {hit.intensity}/3")
            print(f"  • Allowed Themes  : {', '.join(sorted(list(hit.thematic_tags)))}")
            print(f"  • Thermal Vector  : {hit.thermal or 'Neutral'}")
            print(f"  • Tactile Vector  : {hit.tactile or 'Neutral'}")
        else:
            print(f"\n❌ Word '{args.query}' not found in Sensory Dictionary.\n")
        return 0

    print("=" * 70)
    print("CANONFORGE MASTER SENSORY DICTIONARY (SSOT)")
    print("=" * 70)
    print(f"• Total Canonical Lemmas         : {len(d.lexemes)}")
    print(f"• Indexed Single-Word Forms (O(1)): {len(d.inverted_index)}")
    print(f"• Indexed Multi-Word Phrases     : {len(d.phrase_index)}")
    print(f"• Max Phrase Length              : {d.max_phrase_len} words")
    print(f"• Registered Thematic Profiles   : {len(d.themes_registry)}")
    print("=" * 70)
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
