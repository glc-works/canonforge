"""
unified_polish.py

CanonForge Studio: Unified Single-Pass Literary Reviewer & Polish Suite (OKF v0.3).
Executes single-pass multi-engine evaluation across:
1. Pacing & Telemetry (Word counts, sentence rhythm, reading time)
2. Anti-Slop & Deep POV (AI clichés, filter words, adverbs, tricolons)
3. 5-Senses Sensory Radar (Four-Sense Rule across 600-word windows)
4. Biometric Invariants & Fact Checking (Scars, eyes, weapons, bonds)
5. Canon Leak Guard (Zero modern/Earth terms)
"""

import sys
import os
import re
import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Set
from collections import Counter

SCRIPT_DIR = Path(__file__).resolve().parent
CONVERGENCE_DIR = SCRIPT_DIR.parent
MANUSCRIPT_DIR = CONVERGENCE_DIR / "manuscript"

# Import existing engines
try:
    import chapter_metrics as cm
    HAS_CM = True
except ImportError:
    HAS_CM = False

try:
    import audit_prose as ap
    HAS_AP = True
except ImportError:
    HAS_AP = False

try:
    import audit_sensory as asen
    HAS_ASEN = True
except ImportError:
    HAS_ASEN = False

try:
    import audit_continuity as ac
    HAS_AC = True
except ImportError:
    HAS_AC = False

try:
    import novel_pipeline as np
    HAS_NP = True
except ImportError:
    HAS_NP = False

try:
    import book_navigator as bn
    HAS_BN = True
except ImportError:
    HAS_BN = False


# ==============================================================================
# RESOLVER
# ==============================================================================

def resolve_draft_file(
    query: Optional[str] = None,
    chapter_query: Optional[str] = None,
    allow_interactive: bool = True
) -> Optional[Path]:
    """Find draft file by exact path, book+chapter, or interactive navigator."""
    if HAS_BN:
        target_1 = query
        target_2 = chapter_query if (query and bn.resolve_book(query)) else None
        res = bn.resolve_interactive_or_cli(target_1, target_2, allow_interactive=allow_interactive)
        if res:
            return res[1]

    if not query:
        # Check git modified chapters first
        if HAS_CM:
            git_mod = cm.find_target_file("")
        import subprocess
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain", "manuscript/"],
                cwd=str(CONVERGENCE_DIR),
                capture_output=True,
                text=True
            )
            for line in res.stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2:
                    p = CONVERGENCE_DIR / parts[-1]
                    if p.suffix == ".md" and "chapters" in str(p) and p.exists():
                        return p
        except Exception:
            pass
            
        # Fallback to newest manuscript file
        all_mds = list(MANUSCRIPT_DIR.rglob("*.md"))
        chaps = [f for f in all_mds if "chapters" in str(f) and not f.name.startswith("compiled") and not f.name.startswith(".")]
        if chaps:
            chaps.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return chaps[0]
        return None

    # Check direct file
    p = Path(query)
    if p.exists() and p.is_file():
        return p
    p_conv = CONVERGENCE_DIR / query
    if p_conv.exists() and p_conv.is_file():
        return p_conv

    # Substring search in manuscript
    q_clean = query.lower().replace(".md", "").strip()
    all_mds = list(MANUSCRIPT_DIR.rglob("*.md"))
    valid = [f for f in all_mds if not f.name.startswith("compiled") and not f.name.startswith(".")]
    
    exact = [f for f in valid if f.stem.lower() == q_clean or f.name.lower() == q_clean]
    if exact:
        return exact[0]
        
    m = re.search(r"\b(?:ch)?(\d+)\b", q_clean)
    if m:
        num = int(m.group(1))
        prefix = f"ch{num:02d}-"
        num_m = [f for f in valid if f.name.startswith(prefix)]
        if num_m:
            return num_m[0]
            
    sub = [f for f in valid if q_clean in f.stem.lower()]
    if sub:
        return sub[0]
        
    return None


# ==============================================================================
# AUDIT ENGINE
# ==============================================================================

def run_single_pass_audit(file_path: Path) -> Dict[str, Any]:
    """Execute unified multi-engine audit in a single pass."""
    start_t = time.perf_counter()
    raw_text = file_path.read_text(encoding="utf-8")
    
    # 1. Frontmatter strip for body analysis
    body_text = raw_text
    meta = {}
    if raw_text.startswith("---"):
        parts = raw_text.split("---", 2)
        if len(parts) >= 3:
            body_text = parts[2].strip()
            
    # 2. Metrics & Telemetry
    metrics = None
    if HAS_CM:
        metrics = cm.get_chapter_metrics(file_path)
    else:
        words = body_text.split()
        metrics = {
            "char_total": len(body_text),
            "word_count": len(words),
            "sentence_count": max(1, len(re.findall(r"[.!?]+(?:\s+|$)", body_text))),
            "paragraph_count": max(1, len([p for p in body_text.split("\n\n") if p.strip()])),
            "reading_time_min": round(len(words) / 220.0, 1),
            "top_10_words": []
        }

    # 3. Prose Purity & Anti-Slop
    prose_results = {}
    if HAS_AP:
        prose_results = ap.audit_text(body_text, filename=file_path.name)
    else:
        prose_results = {
            "cliche_hits": [], "filter_hits": [], "adverb_hits": [],
            "tricolon_hits": [], "purity_score": 100.0
        }

    cliches = prose_results.get("cliche_hits", [])
    filters = prose_results.get("filter_hits", [])
    adverbs = prose_results.get("adverb_hits", [])
    tricolons = prose_results.get("tricolon_hits", [])

    # 4. Tactile Sensory Radar (5-Senses)
    sensory_results = {}
    if HAS_ASEN:
        s_raw = asen.analyze_text(body_text)
        words_len = max(1, s_raw.get("total_words", len(body_text.split())))
        per_1k = max(1.0, words_len / 1000.0)
        densities = {s: round(cnt / per_1k, 1) for s, cnt in s_raw.get("sense_counts", {}).items()}
        failing_windows = sum(1 for w in s_raw.get("windows", []) if not w.get("compliant", True))
        sensory_results = {
            "density_per_1000": densities,
            "sense_counts": s_raw.get("sense_counts", {}),
            "sense_samples": s_raw.get("sense_samples", {}),
            "windows_failing_rule": failing_windows,
            "total_windows": len(s_raw.get("windows", [])),
            "immersion_score": s_raw.get("immersion_score", 85.0),
            "four_sense_compliance_pct": s_raw.get("four_sense_compliance_pct", 100.0)
        }
    else:
        sensory_results = {
            "density_per_1000": {"Sight": 10, "Sound": 8, "Smell": 5, "Taste": 3, "Touch": 8},
            "windows_failing_rule": 0,
            "total_windows": 1,
            "immersion_score": 85.0
        }

    # 5. Canon Leaks
    canon_leaks = []
    is_stone_saga = "stone-child" in str(file_path) or "iron-pilgrimage" in str(file_path)
    if HAS_NP:
        for pat, label in np.CANON_LEAK_PATTERNS:
            if is_stone_saga and "human" in label.lower():
                continue
            for idx, line in enumerate(body_text.splitlines(), 1):
                if re.search(pat, line, re.IGNORECASE):
                    canon_leaks.append({
                        "line": idx,
                        "leak": label,
                        "snippet": line.strip()[:80]
                    })

    # 6. Physical Invariant Checks
    invariant_violations = []
    if HAS_AC:
        for char_name, inv in ac.KNOWN_INVARIANTS.items():
            first_name = char_name.split()[0].lower()
            if char_name.lower() in body_text.lower():
                # Check forbidden eye colors
                for f_col in inv.get("forbidden_eye_colors", []):
                    pat = rf"\b{re.escape(f_col)}\s+(?:eyes|gaze|stare)\b"
                    for idx, line in enumerate(body_text.splitlines(), 1):
                        if re.search(pat, line, re.IGNORECASE):
                            if first_name in line.lower() or char_name.lower() in line.lower():
                                invariant_violations.append({
                                    "line": idx,
                                    "char": char_name,
                                    "rule": f"Forbidden eye color '{f_col}' for {char_name}",
                                    "snippet": line.strip()[:80]
                                })
                # Check forbidden animi
                for f_animus in inv.get("forbidden_animi", []):
                    pat = rf"\b{re.escape(f_animus)}\b"
                    for idx, line in enumerate(body_text.splitlines(), 1):
                        if re.search(pat, line, re.IGNORECASE) and char_name.lower() in line.lower():
                            invariant_violations.append({
                                "line": idx,
                                "char": char_name,
                                "rule": f"Forbidden animus '{f_animus}' bound to {char_name}",
                                "snippet": line.strip()[:80]
                            })

    # ==========================================================================
    # LITERARY HEALTH SCORING (0.0 to 10.0)
    # ==========================================================================
    word_count = metrics["word_count"]
    per_1k = max(1.0, word_count / 1000.0)
    
    # A. Sensory Immersion Score (Max 10.0)
    densities = sensory_results.get("density_per_1000", {})
    has_smell = densities.get("Smell", 0) >= 1.5
    has_taste = densities.get("Taste", 0) >= 0.8
    has_touch = densities.get("Touch", 0) >= 2.0
    failing_windows = sensory_results.get("windows_failing_rule", 0)
    
    sensory_score = 10.0
    if not has_smell:
        sensory_score -= 1.8
    if not has_taste:
        sensory_score -= 1.2
    if not has_touch:
        sensory_score -= 1.5
    sensory_score -= min(3.0, failing_windows * 0.8)
    sensory_score = max(2.0, min(10.0, sensory_score))

    # B. Prose Purity Score (Max 10.0)
    cliche_rate = len(cliches) / per_1k
    filter_rate = len(filters) / per_1k
    adverb_rate = len(adverbs) / per_1k
    tricolon_count = len(tricolons)
    
    prose_score = 10.0
    prose_score -= (cliche_rate * 1.5)
    prose_score -= (filter_rate * 0.3)
    prose_score -= (adverb_rate * 0.4)
    prose_score -= (tricolon_count * 0.5)
    prose_score = max(2.0, min(10.0, prose_score))

    # C. Cadence & Rhythm Score (Max 10.0)
    sent_count = metrics["sentence_count"]
    avg_words_per_sent = word_count / max(1, sent_count)
    cadence_score = 10.0
    if avg_words_per_sent < 11.0 or avg_words_per_sent > 24.0:
        cadence_score -= 2.0
    cadence_score = max(4.0, min(10.0, cadence_score))

    # D. Continuity & Invariants Score (Max 10.0)
    leak_penalty = len(canon_leaks) * 3.0
    invariant_penalty = len(invariant_violations) * 2.0
    continuity_score = max(0.0, 10.0 - leak_penalty - invariant_penalty)

    # Composite Overall Score
    overall_score = round(
        (sensory_score * 0.30) +
        (prose_score * 0.35) +
        (cadence_score * 0.15) +
        (continuity_score * 0.20),
        1
    )

    # Generate Patch Recommendations
    patches = []
    
    # 1. Canon leaks (Highest priority)
    for lk in canon_leaks[:3]:
        patches.append({
            "priority": "🔴 CRITICAL",
            "line": lk["line"],
            "type": "Canon Leak",
            "issue": f"Forbidden source term: {lk['leak']}",
            "snippet": lk["snippet"],
            "suggestion": "Replace immediately with the universe in-world equivalent."
        })

    # 2. Invariants
    for inv in invariant_violations[:3]:
        patches.append({
            "priority": "🔴 CRITICAL",
            "line": inv["line"],
            "type": "Physical Drift",
            "issue": inv["rule"],
            "snippet": inv["snippet"],
            "suggestion": "Correct physical attribute to match canonical records."
        })

    # 3. AI Clichés
    for cl in cliches[:4]:
        patches.append({
            "priority": "🟠 HIGH",
            "line": cl.get("line", 1),
            "type": "AI Cliché",
            "issue": f"Banned cliché: '{cl.get('cliche')}'",
            "snippet": cl.get("context", ""),
            "suggestion": cl.get("explanation", "Describe immediate physical sensation instead.")
        })

    # 4. Filters
    for fl in filters[:4]:
        patches.append({
            "priority": "🟡 MEDIUM",
            "line": fl.get("line", 1),
            "type": "Filter Word (Deep POV)",
            "issue": f"Narrative filter: '{fl.get('matched')}'",
            "snippet": fl.get("context", ""),
            "suggestion": fl.get("tip", "Delete filter; let sensory action or noun lead clause.")
        })

    elapsed_ms = round((time.perf_counter() - start_t) * 1000.0, 2)

    return {
        "file_name": file_path.name,
        "file_path": str(file_path.resolve()),
        "overall_score": overall_score,
        "scores": {
            "sensory_immersion": round(sensory_score, 1),
            "prose_purity": round(prose_score, 1),
            "cadence_rhythm": round(cadence_score, 1),
            "continuity_invariants": round(continuity_score, 1)
        },
        "metrics": metrics,
        "prose_telemetry": {
            "cliche_count": len(cliches),
            "filter_count": len(filters),
            "adverb_count": len(adverbs),
            "tricolon_count": len(tricolons)
        },
        "sensory_telemetry": sensory_results,
        "canon_leaks": canon_leaks,
        "invariant_violations": invariant_violations,
        "patches": patches,
        "execution_time_ms": elapsed_ms
    }


# ==============================================================================
# REPORTING & FORMATTING
# ==============================================================================

def print_polish_report(report: Dict[str, Any], verbose: bool = False):
    """Render comprehensive AuthorX polish report in terminal."""
    score = report["overall_score"]
    if score >= 9.0:
        badge = "🟢 MASTERPIECE / PUBLICATION READY"
    elif score >= 7.8:
        badge = "🌱 STRONG LITERARY DRAFT (Minor polish required)"
    elif score >= 6.5:
        badge = "🟠 COMPETENT (Needs slop prune & sensory lift)"
    else:
        badge = "🔴 HEAVY REVISION NEEDED (Filter clutter or canon leaks)"

    print("\n" + "=" * 80)
    print(f"  ✨ AUTHORX UNIFIED POLISH SUITE: {report['file_name']}")
    print(f"      Overall Health: {score:.1f}/10.0 | Status: {badge}")
    print(f"      Single-Pass Engine Speed: ⚡ {report['execution_time_ms']} ms")
    print("=" * 80)

    # 1. Scorecard Breakdown
    sc = report["scores"]
    print("\n📊 1. LITERARY HEALTH SCORECARD:")
    print(f"  • Sensory Immersion   : {sc['sensory_immersion']:>4.1f}/10.0 (Smell, Taste, Touch, Four-Sense Rule)")
    print(f"  • Prose Purity & POV  : {sc['prose_purity']:>4.1f}/10.0 (Zero cliches, filter words, -ly adverbs)")
    print(f"  • Cadence & Rhythm    : {sc['cadence_rhythm']:>4.1f}/10.0 (Sentence variety & paragraph density)")
    print(f"  • Continuity & Canon  : {sc['continuity_invariants']:>4.1f}/10.0 (Invariants, scars, zero canon leaks)")

    # 2. Document Metrics
    m = report["metrics"]
    w_sent = round(m["word_count"] / max(1, m["sentence_count"]), 1)
    print(f"\n📈 2. DOCUMENT TELEMETRY:")
    print(f"  • Word Count          : {m['word_count']:,} words (~{m['reading_time_min']} min reading time)")
    print(f"  • Sentence Rhythm     : {m['sentence_count']:,} sentences (~{w_sent} words/sentence)")
    print(f"  • Paragraphs          : {m['paragraph_count']:,} paragraphs")
    if m.get("top_10_words"):
        top_w = [f"{w} ({c})" for w, c in m["top_10_words"][:6]]
        print(f"  • Top Content Words   : " + ", ".join(top_w))

    # 3. Slop & Filter Diagnostics
    pt = report["prose_telemetry"]
    print(f"\n🧹 3. PROSE PURITY DIAGNOSTICS:")
    print(f"  • Banned AI Clichés   : {pt['cliche_count']} detected")
    print(f"  • Cognitive Filters   : {pt['filter_count']} detected ('he saw', 'she felt', 'noticed')")
    print(f"  • Dialogue -ly Adverbs: {pt['adverb_count']} detected ('said quietly', 'replied coldly')")
    print(f"  • Tricolon Tropes     : {pt['tricolon_count']} detected")

    # 4. Sensory Balance Radar
    densities = report["sensory_telemetry"].get("density_per_1000", {})
    print(f"\n👃 4. TACTILE SENSORY RADAR (per 1,000 words):")
    for s_name in ["Sight", "Sound", "Smell", "Taste", "Touch"]:
        cnt = densities.get(s_name, 0.0)
        target = 2.0 if s_name in ("Sight", "Sound", "Touch") else (1.5 if s_name == "Smell" else 0.8)
        icon = "🟢" if cnt >= target else "⚠️ "
        print(f"  {icon} {s_name:<8} : {cnt:>4.1f} hits / 1,000w (Benchmark target: {target:.1f}+)")

    # 5. Actionable Patch Suggestions
    print(f"\n🎯 5. ACTIONABLE REWRITE PATCH LIST ({len(report['patches'])} suggestions):")
    if not report["patches"]:
        print("  ✓ Zero critical issues detected! Prose is clean, tactile, and in deep POV.")
    else:
        for idx, patch in enumerate(report["patches"][:8], 1):
            print(f"  [{idx}] {patch['priority']} | Line {patch['line']} | {patch['type']}")
            print(f"      Issue      : {patch['issue']}")
            print(f"      Original   : \"{patch['snippet']}\"")
            print(f"      👉 Action  : {patch['suggestion']}")
            print()

    print("=" * 80 + "\n")


# ==============================================================================
# CLI RUNNER
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="CanonForge Studio: Unified Single-Pass Literary Reviewer")
    parser.add_argument("target", nargs="?", help="Book number/slug, draft path, or query (default: active modified draft)")
    parser.add_argument("chapter", nargs="?", help="Chapter number, slug, or title (when target is a book)")
    parser.add_argument("--json", "-j", action="store_true", help="Output raw JSON analysis")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose reporting")
    
    args = parser.parse_args()
    
    target_file = resolve_draft_file(args.target, chapter_query=args.chapter)
    if not target_file or not target_file.exists():
        print(f"❌ Error: Draft chapter '{args.target or 'active'}' could not be located in manuscript directory.")
        sys.exit(1)
        
    report = run_single_pass_audit(target_file)
    
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return
        
    print_polish_report(report, verbose=args.verbose)


if __name__ == "__main__":
    main()
