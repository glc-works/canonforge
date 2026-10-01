#!/usr/bin/env python3
"""
CONVERGENCE STUDIO: ANTI-SLOP & DEEP POV PROSE LINTER
------------------------------------------------------------------------------
Enforces the literary fiction standards of the Convergence Style Guide:
  • Eliminates AI cliches, purple slop, and tricolon tropes
  • Flags filter words that break Deep 3rd-Person Limited POV
  • Detects dialogue adverb clutter in favor of subtext & action beats
  • Audits sentence cadence and paragraph rhythm
------------------------------------------------------------------------------
"""

import sys
import re
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple

CONVERGENCE_DIR = Path(__file__).resolve().parent.parent
MANUSCRIPT_DIR = CONVERGENCE_DIR / "manuscript"

# ==============================================================================
# 1. FORBIDDEN AI CLICHÉS & PURPLE SLOP LEXICON
# ==============================================================================
AI_CLICHES = [
    # Metaphor cliches
    (r"\btapestry of\b", "tapestry of", "Generic AI metaphor for complexity"),
    (r"\ba testament to\b", "a testament to", "Classic AI filler cliché"),
    (r"\btestament to the fact\b", "testament to the fact", "Redundant AI filler"),
    (r"\bdance of (shadows|light|flames|dust)\b", "dance of [x]", "Overused purple prose trope"),
    (r"\bpalpable\b", "palpable", "Show don't tell: describe the physical reaction instead"),
    (r"\bcacophony of\b", "cacophony of", "Overused acoustic trope; specify distinct mechanical/organic sounds"),
    (r"\bunspoken (agreement|understanding|bond)\b", "unspoken [x]", "Vague abstraction; show through physical posture"),
    (r"\bshiver (ran|went) down\b", "shiver ran down", "Bodily cliché; ground in temperature or muscular reaction"),
    (r"\bcouldn't help but\b", "couldn't help but", "Unnecessary narrator filter"),
    (r"\bcould not help but\b", "could not help but", "Unnecessary narrator filter"),
    (r"\ba wave of (dread|panic|relief|grief)\b", "a wave of [emotion]", "Vague summary; ground in visceral organ sensations"),
    (r"\blike a moth to a flame\b", "like a moth to a flame", "Dead idiom"),
    (r"\ba stark reminder\b", "a stark reminder", "Lazy thematic editorializing"),
    (r"\bin the blink of an eye\b", "in the blink of an eye", "Dead idiom; ground in microseconds or reflex"),
    (r"\bpiercing (gaze|eyes|stare)\b", "piercing gaze", "Tired romance/AI trope"),
    (r"\beyes widened in shock\b", "eyes widened in shock", "Melodramatic face cliché"),
    (r"\bbreath caught in (his|her|their) throat\b", "breath caught in throat", "Melodramatic physical cliché"),
    (r"\bair was thick with\b", "air was thick with", "Vague atmosphere; specify actual particles/scent"),
    (r"\bbeacon of hope\b", "beacon of hope", "Tired high-fantasy cliché"),
    (r"\bdelve into\b", "delve into", "Academic/AI buzzword"),
    (r"\bneedless to say\b", "needless to say", "If needless to say, do not say it"),
    (r"\bas if time (stood still|had stopped)\b", "as if time stood still", "Dead cinematic trope"),
    (r"\blittle did (he|she|they) know\b", "little did [x] know", "Severe POV violation (unearned omniscient narrator)"),
    (r"\ba sense of (unease|dread|wonder)\b", "a sense of [x]", "Name-dropping emotion instead of sensory immersion"),
]

# ==============================================================================
# 2. FILTER WORDS (COGNITIVE BARRIERS TO DEEP POV)
# ==============================================================================
# Filter words place a glass pane between the reader and the world.
# "She heard the engine whine" -> "The engine whined."
# "He felt the iron bite his skin" -> "The iron bit his skin."
FILTER_PATTERNS = [
    (r"\b(felt|feels|feeling) (the|a|his|her|their|an)\b", "felt [noun]", "Direct experience: replace with immediate physical sensation"),
    (r"\b(saw|sees|seeing) (the|a|his|her|their|an)\b", "saw [noun]", "Direct observation: describe the object/action directly"),
    (r"\b(heard|hears|hearing) (the|a|his|her|their|an)\b", "heard [noun]", "Direct acoustic: let the sound verb lead the sentence"),
    (r"\b(noticed|notices|noticing) (that|the|a)\b", "noticed [x]", "Narrative redundancy: if told to reader, the POV noticed it"),
    (r"\b(realized|realizes) (that)?\b", "realized that", "Show the deduction through physical evidence or action"),
    (r"\b(watched|watches|watching) as\b", "watched as", "Passive framing; let the subject act directly"),
    (r"\b(could see|could hear|could feel|could smell)\b", "could [sense]", "Unnecessary modal filter; make sensory verb active"),
    (r"\bseemed to (be|have|drift|move|grow)\b", "seemed to [verb]", "Weak hedge; commit to the observation"),
    (r"\bappeared to (be|have)\b", "appeared to [x]", "Weak hedge"),
    (r"\bthought to (himself|herself|themselves)\b", "thought to [self]", "Redundant: 3rd-person limited interiority is already in the character's head"),
]

# ==============================================================================
# 3. DIALOGUE ADVERBS (-LY ATTRIBUTIONS)
# ==============================================================================
DIALOGUE_ADVERB_PATTERN = re.compile(
    r'["\']\s*(?:said|asked|whispered|muttered|replied|shouted|exclaimed|barked|growled|snapped)\s+([a-zA-Z]+ly)\b',
    re.IGNORECASE
)

# Tricolon pattern: "not X, but Y, a Z"
TRICOLON_PATTERN = re.compile(
    r"\bnot\s+([^,]+),\s*but\s+([^,]+),\s*(?:a|an)\s+([^.]+)\.",
    re.IGNORECASE
)

def audit_text(text: str, filename: str = "chapter") -> Dict[str, Any]:
    lines = text.splitlines()
    total_words = len(text.split())
    total_sentences = max(1, len(re.findall(r"[.!?]+(?:\s+|$)", text)))
    
    cliche_hits = []
    filter_hits = []
    adverb_hits = []
    tricolon_hits = []

    # 1. Line-by-line inspection
    for line_idx, line in enumerate(lines, start=1):
        clean_line = line.strip()
        if not clean_line or clean_line.startswith("#") or clean_line.startswith("---"):
            continue

        # Check AI clichés
        for pattern, label, explanation in AI_CLICHES:
            matches = list(re.finditer(pattern, clean_line, re.IGNORECASE))
            for m in matches:
                cliche_hits.append({
                    "line": line_idx,
                    "matched": m.group(0),
                    "label": label,
                    "explanation": explanation,
                    "context": clean_line
                })

        # Check filter words (strictly on narrative prose; exclude spoken character dialogue in quotes)
        prose_only_line = re.sub(r'"[^"]*"', '', clean_line)
        prose_only_line = re.sub(r'“[^”]*”', '', prose_only_line)

        for pattern, label, tip in FILTER_PATTERNS:
            matches = list(re.finditer(pattern, prose_only_line, re.IGNORECASE))
            for m in matches:
                filter_hits.append({
                    "line": line_idx,
                    "matched": m.group(0),
                    "label": label,
                    "tip": tip,
                    "context": clean_line
                })

        # Check dialogue adverbs
        adv_matches = DIALOGUE_ADVERB_PATTERN.findall(clean_line)
        for adv in adv_matches:
            adverb_hits.append({
                "line": line_idx,
                "adverb": adv,
                "context": clean_line
            })

        # Check tricolons
        tri_matches = TRICOLON_PATTERN.findall(clean_line)
        for tri in tri_matches:
            tricolon_hits.append({
                "line": line_idx,
                "context": clean_line
            })

    # 2. Cadence & Rhythm Metrics
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    sentence_lengths = [len(s.split()) for s in sentences]
    avg_sentence_len = sum(sentence_lengths) / max(1, len(sentence_lengths))
    variance = sum((x - avg_sentence_len) ** 2 for x in sentence_lengths) / max(1, len(sentence_lengths))
    std_dev_sentence = variance ** 0.5

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip() and not p.startswith("#")]
    avg_para_words = sum(len(p.split()) for p in paragraphs) / max(1, len(paragraphs))

    # 3. Purity Score Calculation (Starting at 100)
    score = 100.0
    score -= (len(cliche_hits) * 4.0)       # Heavy penalty for AI slop clichés
    score -= (len(tricolon_hits) * 3.0)     # Penalty for repetitive tricolons
    score -= (len(adverb_hits) * 2.0)       # Moderate penalty for dialogue adverbs
    
    # Filter word density penalty (> 1.2% density begins heavy deduction)
    filter_density = (len(filter_hits) / max(1, total_words)) * 100
    if filter_density > 1.2:
        excess = filter_density - 1.2
        score -= (excess * 8.0)

    final_score = max(0.0, min(100.0, score))

    return {
        "filename": filename,
        "total_words": total_words,
        "total_sentences": total_sentences,
        "avg_sentence_length": round(avg_sentence_len, 1),
        "sentence_std_dev": round(std_dev_sentence, 1),
        "avg_paragraph_words": round(avg_para_words, 1),
        "filter_density_pct": round(filter_density, 2),
        "cliche_hits": cliche_hits,
        "filter_hits": filter_hits,
        "adverb_hits": adverb_hits,
        "tricolon_hits": tricolon_hits,
        "purity_score": round(final_score, 1),
    }

def print_audit_report(result: Dict[str, Any], verbose: bool = False):
    score = result["purity_score"]
    color = "🟢" if score >= 90 else ("🟡" if score >= 75 else "🔴")

    print("\n" + "=" * 80)
    print(f"PROSE PURITY & DEEP POV AUDIT: {result['filename']}")
    print("=" * 80)
    print(f"• Total Words        : {result['total_words']:,} words")
    print(f"• Total Sentences    : {result['total_sentences']:,}")
    print(f"• Avg Sentence Len   : {result['avg_sentence_length']} words (Cadence Std Dev: ±{result['sentence_std_dev']})")
    print(f"• Avg Paragraph Len  : {result['avg_paragraph_words']} words")
    print(f"• Filter Word Density: {result['filter_density_pct']}% of prose (Target: < 1.0%)")
    print("-" * 80)
    print(f"🏆 LITERARY PROSE PURITY SCORE: {color} {score}/100")
    print("-" * 80)

    # 1. AI Clichés
    if result["cliche_hits"]:
        print(f"\n⚠️  AI CLICHÉS & PURPLE SLOP DETECTED ({len(result['cliche_hits'])} instances):")
        for hit in result["cliche_hits"][:8 if not verbose else 50]:
            print(f"  Line {hit['line']:>4} | Matched: [{hit['matched']}]")
            print(f"            Tip: {hit['explanation']}")
            print(f"            Context: \"{hit['context'][:90]}...\"")
        if len(result["cliche_hits"]) > 8 and not verbose:
            print(f"  ... and {len(result['cliche_hits']) - 8} more. Use --verbose to view all.")
    else:
        print("  ✓ Zero forbidden AI cliches detected. Pristine prose integrity.")

    # 2. Tricolons
    if result["tricolon_hits"]:
        print(f"\n⚠️  PREDICTABLE TRICOLON CONSTRUCTIONS ({len(result['tricolon_hits'])}):")
        for hit in result["tricolon_hits"][:3]:
            print(f"  Line {hit['line']:>4} | Context: \"{hit['context'][:90]}...\"")

    # 3. Filter Words
    if result["filter_hits"]:
        sample_count = 6 if not verbose else len(result["filter_hits"])
        print(f"\n🔍 DEEP POV FILTER WORDS ({len(result['filter_hits'])} total, showing top {sample_count}):")
        for hit in result["filter_hits"][:sample_count]:
            print(f"  Line {hit['line']:>4} | Matched: [{hit['matched']}]")
            print(f"            Tip: {hit['tip']}")
            print(f"            Context: \"{hit['context'][:90]}...\"")
        if len(result["filter_hits"]) > sample_count:
            print(f"  ... and {len(result['filter_hits']) - sample_count} more filter words.")
    else:
        print("  ✓ Zero cognitive filter words. Direct immersion achieved.")

    # 4. Dialogue Adverbs
    if result["adverb_hits"]:
        print(f"\n🗣️  DIALOGUE ADVERB CLUTTER ({len(result['adverb_hits'])}):")
        for hit in result["adverb_hits"][:5]:
            print(f"  Line {hit['line']:>4} | Adverb: [{hit['adverb']}] in: \"{hit['context'][:80]}...\"")
            print(f"            Tip: Replace adverb with physical action beat or trust subtext.")

    print("\n" + "=" * 80 + "\n")

def find_chapter_files(target: str) -> List[Path]:
    p = Path(target)
    if p.is_file():
        return [p]
    
    # Try resolving relative to manuscript
    m_path = MANUSCRIPT_DIR / target
    if m_path.is_file():
        return [m_path]
    elif m_path.is_dir():
        chapters_dir = m_path / "chapters"
        if chapters_dir.exists():
            return sorted([f for f in chapters_dir.glob("*.md") if "archive" not in f.parts])
        return sorted([f for f in m_path.rglob("*.md") if "archive" not in f.parts and "_build" not in f.parts])

    # Search in series directories if target matches a book directory or toc
    for b_dir in list(MANUSCRIPT_DIR.glob(f"*/{target}")) + list(MANUSCRIPT_DIR.glob(f"*/*{target}*")):
        if b_dir.is_dir():
            chapters_dir = b_dir / "chapters"
            if chapters_dir.exists():
                return sorted([f for f in chapters_dir.glob("*.md") if "archive" not in f.parts])
            return sorted([f for f in b_dir.rglob("*.md") if "archive" not in f.parts and "_build" not in f.parts])

    # Search by slug
    matches = list(MANUSCRIPT_DIR.rglob(f"*{target}*"))
    files = [
        f for f in matches
        if f.is_file() and f.suffix == ".md" and not f.name.startswith((".", "MASTER-", "README"))
        and "_build" not in f.parts and "compiled" not in f.parts and "darlings" not in f.parts and "exports" not in f.parts and "archive" not in f.parts
    ]
    return sorted(files)

def main():
    parser = argparse.ArgumentParser(description="Convergence Anti-Slop & Deep POV Prose Linter")
    parser.add_argument("target", nargs="?", default=None, help="Chapter markdown file or book slug")
    parser.add_argument("--book", help="Book slug to audit (e.g. the-sun-sanctum-apprentice)")
    parser.add_argument("--all-books", action="store_true", help="Audit all chapters across all books")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print all infractions in full detail")
    args = parser.parse_args()

    target = args.book or args.target or "the-iron-on-the-anvil.md"

    if args.all_books:
        all_mds = sorted(MANUSCRIPT_DIR.glob("*/*/chapters/*.md"))
        print(f"\n📚 Running Batch Prose Audit across {len(all_mds)} manuscript chapters...\n")
        scores = []
        for ch in all_mds:
            text = ch.read_text(encoding="utf-8")
            res = audit_text(text, filename=f"{ch.parent.parent.name}/{ch.name}")
            scores.append((res["filename"], res["purity_score"], res["total_words"]))
            print_audit_report(res, verbose=args.verbose)

        print("=" * 80)
        print("CONVERGENCE BATCH PROSE PURITY SUMMARY")
        print("=" * 80)
        for fname, sc, wc in scores:
            col = "🟢" if sc >= 90 else ("🟡" if sc >= 75 else "🔴")
            print(f"{col} {sc:>5.1f}/100 | {wc:>6,} words | {fname}")
        avg_score = sum(s[1] for s in scores) / max(1, len(scores))
        print("-" * 80)
        print(f"Overall Average Prose Purity: {avg_score:.1f}/100\n")
        return

    files = find_chapter_files(target)
    if not files:
        print(f"❌ Error: Could not locate chapter markdown file for: {target}")
        sys.exit(1)

    for f in files:
        text = f.read_text(encoding="utf-8")
        result = audit_text(text, filename=f.name)
        print_audit_report(result, verbose=args.verbose)

if __name__ == "__main__":
    main()
