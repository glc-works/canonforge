"""
canonforge/engines/search.py

Universal Entity & Lore Search Engine for CanonForge Studio.
Designed with Zero Dead-Ends (Fuzzy Levenshtein Autocorrect & Contextual Suggestions).
100% Free of Universe-Specific Hardcoding.
"""

import sys
import os
import re
import json
import sqlite3
import difflib
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

def find_universe_root() -> Path:
    cwd = Path.cwd().resolve()
    for parent in [cwd, *cwd.parents]:
        if (parent / "universe.yaml").exists():
            return parent
    return cwd

def get_wiki_dir(root: Path) -> Path:
    wiki = root / "wiki"
    return wiki if wiki.exists() else root

def get_db_path(root: Path) -> Optional[Path]:
    for cand in [root / "data" / "game_world.db", root / "data" / "canon.db", *root.glob("data/*.db")]:
        if cand.exists():
            return cand
    return None

def clean_wikilinks(text: str) -> str:
    if not text:
        return ""
    t = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", text)
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)

def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    fm = {}
    body = content
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
    if m:
        fm_text, body = m.group(1), m.group(2)
        for line in fm_text.splitlines():
            line = line.strip()
            if ":" in line and not line.startswith("#"):
                k, v = line.split(":", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k == "tags" or k == "labels":
                    fm[k] = [t.strip().lstrip("-").strip() for t in v.split(",") if t.strip()]
                else:
                    fm[k] = v
    return fm, body

def scan_wiki_entities(wiki_dir: Path) -> List[Dict[str, Any]]:
    entities = []
    if not wiki_dir.exists():
        return entities

    for md_file in wiki_dir.rglob("*.md"):
        if md_file.name.lower() in ("readme.md", "index.md", "summary.md"):
            continue
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception:
            continue

        fm, body = parse_frontmatter(content)
        name = fm.get("name") or fm.get("title") or md_file.stem.replace("-", " ").title()
        
        # Determine domain/category from folder structure
        rel_parts = md_file.relative_to(wiki_dir).parts
        domain = rel_parts[0] if len(rel_parts) > 1 else "general"
        if len(rel_parts) > 2 and domain in ("terms", "database"):
            domain = rel_parts[1]

        # Extract summary or first non-empty line
        lines = [line.strip() for line in body.splitlines() if line.strip() and not line.strip().startswith("#")]
        snippet = clean_wikilinks(lines[0])[:120] if lines else ""

        entities.append({
            "id": md_file.stem,
            "name": name,
            "domain": domain,
            "path": md_file,
            "frontmatter": fm,
            "snippet": snippet,
        })

    return entities

def search_sqlite_db(db_path: Path, keyword: str, domain_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    if not db_path or not db_path.exists():
        return []
    results = []
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        
        pat = f"%{keyword}%"
        for tbl in tables:
            if domain_filter and domain_filter.lower() not in tbl.lower():
                continue
            cols = [c[1] for c in cur.execute(f"PRAGMA table_info({tbl})").fetchall()]
            text_cols = [c for c in cols if any(t in c.lower() for t in ["name", "title", "id", "role", "kind", "class", "desc"])]
            if not text_cols:
                continue
            clause = " OR ".join([f"{col} LIKE ?" for col in text_cols])
            try:
                for row in cur.execute(f"SELECT * FROM {tbl} WHERE {clause}", [pat] * len(text_cols)).fetchall():
                    d_row = dict(row)
                    name = d_row.get("name") or d_row.get("title") or str(d_row.get(cols[0]))
                    results.append({
                        "id": str(d_row.get("id") or d_row.get(f"{tbl[:-1]}_id") or name),
                        "name": name,
                        "domain": tbl,
                        "info": " | ".join([f"{k}: {v}" for k, v in list(d_row.items())[:4] if v]),
                        "raw": d_row,
                    })
            except Exception:
                continue
        conn.close()
    except Exception:
        pass
    return results

def search_entities(
    query: str,
    domain: Optional[str] = None,
    tag: Optional[str] = None,
    root_dir: Optional[Path] = None,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    root = root_dir or find_universe_root()
    wiki_dir = get_wiki_dir(root)
    db_path = get_db_path(root)

    wiki_entities = scan_wiki_entities(wiki_dir)
    db_results = search_sqlite_db(db_path, query, domain) if db_path else []

    all_names = [e["name"] for e in wiki_entities] + [d["name"] for d in db_results]
    matched = []

    q_lower = query.lower()
    for e in wiki_entities:
        if domain and domain.lower() not in e["domain"].lower():
            continue
        if tag:
            tags = [str(t).lower() for t in e["frontmatter"].get("tags", [])]
            if not any(tag.lower() in t for t in tags):
                continue
        if not q_lower or q_lower in e["name"].lower() or q_lower in e["id"].lower() or q_lower in e["snippet"].lower():
            matched.append(e)

    # Merge db results that aren't already represented
    matched_names = {m["name"].lower() for m in matched}
    for d in db_results:
        if d["name"].lower() not in matched_names:
            matched.append({
                "id": d["id"],
                "name": d["name"],
                "domain": d["domain"],
                "path": None,
                "frontmatter": d.get("raw", {}),
                "snippet": d.get("info", ""),
            })

    # Zero dead-end suggestions
    suggestions = []
    if not matched and query:
        suggestions = difflib.get_close_matches(query, list(set(all_names)), n=4, cutoff=0.4)

    return matched, suggestions

def render_search_report(results: List[Dict[str, Any]], suggestions: List[str], query: str, detail: bool = False):
    if not results:
        print(f"\n🔍 No entities found matching '{query}'.")
        if suggestions:
            print("💡 Did you mean:")
            for s in suggestions:
                print(f"   - {s}")
        print("\nTip: Run 'cf search' without arguments to explore the lore catalog.\n")
        return

    print(f"\n📚 Found {len(results)} entities matching '{query}':\n")
    if detail:
        for r in results:
            print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print(f"📌 {r['name']} ({r['domain'].title()}) [ID: {r['id']}]")
            if r.get("path"):
                print(f"   File: {r['path']}")
            fm = r.get("frontmatter", {})
            for k, v in fm.items():
                if k not in ("name", "title") and v:
                    print(f"   • {k}: {v}")
            if r.get("snippet"):
                print(f"   Summary: {r['snippet']}")
            print()
    else:
        rows = []
        for r in results:
            fm = r.get("frontmatter", {})
            extra = fm.get("role") or fm.get("kind") or fm.get("faction") or r.get("snippet", "")[:40]
            rows.append([r["id"][:20], r["name"][:30], r["domain"][:15], extra[:40]])

        headers = ["ID", "Name", "Category", "Details"]
        if HAS_TABULATE:
            print(tabulate(rows, headers=headers, tablefmt="rounded_grid"))
        else:
            print(f"{'ID':<20} | {'Name':<30} | {'Category':<15} | {'Details'}")
            print("-" * 80)
            for row in rows:
                print(f"{row[0]:<20} | {row[1]:<30} | {row[2]:<15} | {row[3]}")
    print()

def main():
    parser = argparse.ArgumentParser(description="CanonForge Universal Lore & Entity Search Engine")
    parser.add_argument("query", nargs="?", default="", help="Search keyword or entity name")
    parser.add_argument("--type", "-t", dest="domain", help="Filter by domain/category (character, place, item, etc.)")
    parser.add_argument("--tag", help="Filter by tag")
    parser.add_argument("--detail", "-d", action="store_true", help="Display full detailed inspection view")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    args = parser.parse_args()

    results, suggestions = search_entities(args.query, domain=args.domain, tag=args.tag)

    if args.format == "json":
        payload = {
            "query": args.query,
            "count": len(results),
            "results": [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "domain": r["domain"],
                    "path": str(r["path"]) if r["path"] else None,
                    "frontmatter": r["frontmatter"],
                    "snippet": r["snippet"],
                }
                for r in results
            ],
            "suggestions": suggestions,
        }
        print(json.dumps(payload, indent=2))
        return

    render_search_report(results, suggestions, args.query, detail=args.detail)

if __name__ == "__main__":
    main()
