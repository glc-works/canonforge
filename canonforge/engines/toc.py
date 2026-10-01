#!/usr/bin/env python3
"""
audit_toc_integrity.py

Deterministic Two-Way Integrity Gate for CanonForge Manuscripts.
Verifies that:
1. (No Dangling References) Every chapter declared in toc.yaml exists on disk.
2. (No Orphan Chapters) Every markdown file in chapters/ is declared in toc.yaml.
3. (No Duplicates) No chapter file is listed more than once.
4. (Series Manifest Consistency) Every book directory is registered in series.yaml.

Usage:
    uv run python scripts/audit_toc_integrity.py
    uv run python scripts/audit_toc_integrity.py --verbose
"""

import sys
import os
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from canonforge.core.manifest import find_universe_root

UNIVERSE_DIR = find_universe_root()
MANUSCRIPT_DIR = UNIVERSE_DIR / "manuscript"


def audit_toc_integrity(verbose: bool = False) -> Tuple[int, List[str]]:
    """Scan all series and book TOC manifests for 2-way consistency."""
    if not HAS_YAML:
        print("❌ Error: PyYAML is required to run TOC integrity audit.", file=sys.stderr)
        return 1, ["PyYAML missing"]

    errors: List[str] = []
    warnings: List[str] = []
    total_books_checked = 0
    total_chapters_verified = 0

    series_dirs = sorted([
        d for d in MANUSCRIPT_DIR.iterdir()
        if d.is_dir() and not d.name.startswith((".", "_", "compiled", "darlings", "exports"))
    ])

    for s_dir in series_dirs:
        series_yaml_path = s_dir / "series.yaml"
        series_registered_books: Set[str] = set()

        if series_yaml_path.exists():
            try:
                with open(series_yaml_path, encoding="utf-8") as sf:
                    s_data = yaml.safe_load(sf) or {}
                    for b in s_data.get("books", []):
                        if "folder" in b:
                            series_registered_books.add(b["folder"])
            except Exception as e:
                errors.append(f"[{s_dir.name}/series.yaml] Malformed YAML: {e}")
        else:
            warnings.append(f"[{s_dir.name}] Missing series.yaml manifest")

        book_dirs = sorted([d for d in s_dir.iterdir() if d.is_dir() and (d / "chapters").exists()])

        for b_dir in book_dirs:
            total_books_checked += 1
            toc_path = b_dir / "toc.yaml"
            chapters_dir = b_dir / "chapters"

            # Check if book is registered in series.yaml
            if series_registered_books and b_dir.name not in series_registered_books:
                warnings.append(f"[{s_dir.name}/{b_dir.name}] Folder not registered in series.yaml 'books' list")

            if not toc_path.exists():
                errors.append(f"[{s_dir.name}/{b_dir.name}] Missing toc.yaml manifest!")
                continue

            try:
                with open(toc_path, encoding="utf-8") as tf:
                    toc_data = yaml.safe_load(tf) or {}
            except Exception as e:
                errors.append(f"[{s_dir.name}/{b_dir.name}/toc.yaml] Malformed YAML: {e}")
                continue

            # 1. Gather all chapters declared in toc.yaml
            declared_chapters: List[str] = []
            for act in toc_data.get("acts", []):
                for ch in act.get("chapters", []):
                    declared_chapters.append(ch)

            # Check duplicate declarations
            seen: Set[str] = set()
            duplicates: Set[str] = set()
            for ch in declared_chapters:
                if ch in seen:
                    duplicates.add(ch)
                seen.add(ch)

            if duplicates:
                for dup in sorted(duplicates):
                    errors.append(f"[{s_dir.name}/{b_dir.name}/toc.yaml] Duplicate chapter declared: {dup}")

            # 2. Gather all physical chapters on disk
            physical_files = sorted([
                f.name for f in chapters_dir.glob("*.md")
                if not f.name.startswith((".", "MASTER-", "README"))
            ])

            # 3. Check for Dangling References (in TOC but not on disk)
            for ch in declared_chapters:
                ch_path = chapters_dir / ch
                if not ch_path.exists():
                    errors.append(f"[{s_dir.name}/{b_dir.name}] Dangling TOC entry (file missing on disk): {ch}")
                else:
                    total_chapters_verified += 1

            # 4. Check for Orphan Chapters (on disk but omitted from TOC)
            declared_set = set(declared_chapters)
            for f_name in physical_files:
                if f_name not in declared_set:
                    errors.append(f"[{s_dir.name}/{b_dir.name}] Orphan chapter file (on disk but omitted from toc.yaml): {f_name}")

    # Output Summary
    print("\n" + "=" * 70)
    print("CANONFORGE MANUSCRIPT TOC & INTEGRITY AUDITOR")
    print("=" * 70)
    print(f"• Total Series Audited   : {len(series_dirs)}")
    print(f"• Total Books Audited    : {total_books_checked}")
    print(f"• Total Chapters Checked : {total_chapters_verified}")
    print("-" * 70)

    if warnings and verbose:
        print(f"⚠️  {len(warnings)} WARNING(S):")
        for w in warnings:
            print(f"   • {w}")
        print("-" * 70)

    if errors:
        print(f"❌ FAILED: Found {len(errors)} TOC & Manuscript integrity violation(s):\n")
        for err in errors:
            print(f"   ⛔ {err}")
        print("\n" + "=" * 70)
        return 1, errors

    print("🎉 100% TOC INTEGRITY VERIFIED:")
    print("   ✓ Zero orphan chapters on disk (all files tracked in toc.yaml)")
    print("   ✓ Zero dangling TOC references (all declared files exist on disk)")
    print("   ✓ Zero duplicate chapter entries across acts")
    print("=" * 70 + "\n")
    return 0, []


def main():
    parser = argparse.ArgumentParser(description="Deterministic Two-Way Integrity Gate for CanonForge Manuscripts")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show warnings and non-fatal details")
    args = parser.parse_args()

    code, _ = audit_toc_integrity(verbose=args.verbose)
    sys.exit(code)


if __name__ == "__main__":
    main()
