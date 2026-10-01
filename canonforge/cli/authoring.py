"""
CanonForge CLI: Authoring & Linguistic Quality Commands
--------------------------------------------------------------------------------
Handles:
  - cf thesaurus : Query Sensory Knowledge Graph (synonyms/antonyms with intensities)
  - cf sensory   : 5-senses radar and 4-sense window saturation audit
  - cf pov       : Deep 3rd Limited POV audit (head-hopping, filter verbs)
  - cf prose     : Anti-slop and AI cadence linter
  - cf polish    : Single-pass literary review and benchmark scorecard
"""

import sys
import json
from pathlib import Path
from typing import Optional

from canonforge.core.manifest import find_universe_root
from canonforge.core.resolver import resolve_chapter


def resolve_chapter_file(target_arg: Optional[str] = None, universe_dir: Optional[Path] = None) -> Optional[Path]:
    """Resolve a target chapter path from argument or active universe."""
    return resolve_chapter(target_arg, universe_dir=universe_dir)


def cmd_thesaurus(args):
    """Query Sensory Knowledge Graph thesaurus."""
    from canonforge.engines import sensory_dictionary
    d = sensory_dictionary.get_dictionary()
    word = getattr(args, "word", "")
    if not word:
        print("❌ Error: Missing target word for thesaurus. Usage: cf thesaurus <word>")
        sys.exit(1)

    hit = d.lookup(word)
    if not hit:
        if getattr(args, "format", "text") == "json":
            print(json.dumps({"error": f"Word '{word}' not found in Sensory Dictionary."}, indent=2))
        else:
            print(f"❌ Word '{word}' not found in Sensory Dictionary.")
        sys.exit(1)

    syns = d.get_synonyms(word, theme=getattr(args, "theme", None), intensity=getattr(args, "intensity", None))
    ants = d.get_antonyms(word, theme=getattr(args, "theme", None))

    if getattr(args, "format", "text") == "json":
        payload = {
            "word": word,
            "intensity": hit.intensity,
            "senses": list(hit.senses),
            "aliases": sorted(list(hit.aliases)),
            "synonyms": [{"lemma": s.lemma, "intensity": s.intensity, "themes": list(s.thematic_tags)} for s in syns],
            "antonyms": [{"lemma": a.lemma, "thermal": a.thermal, "tactile": a.tactile} for a in ants]
        }
        print(json.dumps(payload, indent=2))
        return

    print(f"\n📚 SENSORY THESAURUS GRAPH: '{word}' (Intensity: {hit.intensity}/3)")
    print(f"  • Primary Senses: {', '.join(hit.senses)}")
    if hit.aliases:
        print(f"  • Lore Aliases   : {', '.join(sorted(list(hit.aliases)))}")
    if syns:
        print("  • Synonyms       :")
        for s in syns:
            print(f"    - [{s.intensity}/3] {s.lemma} (Themes: {', '.join(s.thematic_tags)})")
    if ants:
        print("  • Antonyms       :")
        for a in ants:
            print(f"    - {a.lemma} (Thermal: {a.thermal or 'Neutral'} | Tactile: {a.tactile or 'Neutral'})")
    print()


def cmd_sensory(args):
    """Run 5-senses radar audit on chapter."""
    from canonforge.engines import sensory
    target = resolve_chapter_file(getattr(args, "chapter", None))
    if not target:
        print(f"❌ Could not locate chapter: {getattr(args, 'chapter', 'default')}")
        sys.exit(1)

    comp = sensory.load_composite_profiles()
    res = sensory.analyze_text(target.read_text(encoding="utf-8"), composite=comp)
    if getattr(args, "format", "text") == "json":
        print(json.dumps(res, indent=2))
    else:
        sensory.print_sensory_report(target.name, res, comp, show_windows=getattr(args, "show_windows", False))


def cmd_pov(args):
    """Run Deep 3rd Limited POV audit on chapter."""
    from canonforge.engines import pov
    target = resolve_chapter_file(getattr(args, "chapter", None))
    if not target:
        print(f"❌ Could not locate chapter: {getattr(args, 'chapter', 'default')}")
        sys.exit(1)

    res = pov.audit_chapter_pov(target)
    if getattr(args, "format", "text") == "json":
        print(json.dumps(res, indent=2))
    else:
        pov.print_pov_report(res)


def cmd_prose(args):
    """Run anti-slop and filter word linter on chapter."""
    from canonforge.engines import prose
    target = resolve_chapter_file(getattr(args, "chapter", None))
    if not target:
        print(f"❌ Could not locate chapter: {getattr(args, 'chapter', 'default')}")
        sys.exit(1)

    text = target.read_text(encoding="utf-8")
    res = prose.audit_text(text, filename=target.name)
    if getattr(args, "format", "text") == "json":
        print(json.dumps(res, indent=2))
    else:
        prose.print_audit_report(res, verbose=getattr(args, "verbose", False))


def cmd_polish(args):
    """Run single-pass unified literary reviewer on chapter."""
    from canonforge.engines import polish
    target = resolve_chapter_file(getattr(args, "chapter", None))
    if not target:
        print(f"❌ Could not locate chapter: {getattr(args, 'chapter', 'default')}")
        sys.exit(1)

    res = polish.review_chapter(target)
    if getattr(args, "format", "text") == "json":
        print(json.dumps(res, indent=2))
    else:
        polish.print_review(res)
