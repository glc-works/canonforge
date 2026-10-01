"""
CLI entrypoint for scene prep brief generation.
"""
import sys
import json
import argparse

from canonforge.engines.prep.builder import generate_scene_brief
from canonforge.engines.prep.prompt import print_scene_brief, generate_llm_authoring_prompt

def main():
    parser = argparse.ArgumentParser(description="CanonForge Scene & Authoring Brief Generator")
    parser.add_argument("target", nargs="?", help="Book number/slug, chapter path, or query (default: active draft)")
    parser.add_argument("chapter", nargs="?", help="Chapter number, slug, or title (when target is a book)")
    parser.add_argument("--book", "-b", help="Specific book filter slug")
    parser.add_argument("--phase", choices=["pre", "post", "opening", "climax"], help="Pin to intra-chapter phase")
    parser.add_argument("--prompt", "-p", action="store_true", help="Output AI-ready authoring system prompt")
    parser.add_argument("--json", "-j", action="store_true", help="Output raw JSON brief object")
    parser.add_argument("--inject", "-i", action="store_true", help="Inject scene brief into chapter markdown header")
    
    args = parser.parse_args()
    
    brief = generate_scene_brief(args.target, book_filter=args.book, chapter_query=args.chapter, phase=args.phase)
    
    if args.inject:
        from canonforge.engines.prep.prompt import inject_scene_brief
        if "error" in brief:
            print(f"❌ Error: {brief['error']}", file=sys.stderr)
            sys.exit(1)
        ok = inject_scene_brief(brief)
        if ok:
            print(f"✅ Scene brief successfully injected into header of: {brief['file_name']}")
        else:
            print(f"❌ Failed to inject scene brief into {brief.get('file_name', 'target')}")
        return

    if args.json:
        print(json.dumps(brief, indent=2, ensure_ascii=False))
        return
        
    if args.prompt:
        if "error" in brief:
            print(f"❌ Error: {brief['error']}", file=sys.stderr)
            sys.exit(1)
        print(generate_llm_authoring_prompt(brief))
        return
        
    print_scene_brief(brief)


if __name__ == "__main__":
    main()
