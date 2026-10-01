import re
from pathlib import Path
from typing import Dict, Any
from canonforge.engines.prep.builder import generate_scene_brief

def print_scene_brief(brief: Dict[str, Any]):
    """Render high-clarity terminal authoring cockpit."""
    if "error" in brief:
        print(f"\n❌ Error: {brief['error']}\n")
        return

    print("\n" + "=" * 80)
    print(f"  🎬 AUTHORX SCENE BRIEF: Book {brief['book']} | Ch {brief['chapter']:02d}: \"{brief['title']}\"")
    print(f"      File: {brief['file_name']} | Generated in ⚡ {brief['retrieval_ms']} ms")
    print("=" * 80)

    # 1. Coordinate & Setting
    print(f"\n📍 1. NARRATIVE COORDINATES:")
    print(f"  • Point of View (POV) : 👁️  {brief['pov']}")
    print(f"  • Primary Setting     : 🏰 {brief['setting']}")
    print(f"  • Timeline Anchor     : ⏳ {brief['timeline_anchor']}")
    print(f"  • Target Word Range   : 🎯 3,500 – 4,200 words (Depth Point Anchor)")

    # 2. Continuity Bridge
    print(f"\n🌉 2. CONTINUITY BRIDGE (PREVIOUS CHAPTER HOOK):")
    if brief.get("continuity_bridge"):
        b = brief["continuity_bridge"]
        print(f"  • From Preceding Chapter: {b['prev_file']} (Ch {b['prev_ch_num']:02d})")
        print(f"  • Concluding Physical State:")
        for line in b["hook_text"].splitlines()[-4:]:
            print(f"    > \"{line}\"")
    else:
        print("  • (Opening chapter of book or standalone sequence — fresh scene entry)")

    # 3. Active Interpersonal Relations & Writing Rules
    print(f"\n🤝 3. ACTIVE CAST RELATIONSHIPS & NARRATIVE WRITING RULES:")
    if brief.get("relational_dynamics"):
        for r in brief["relational_dynamics"]:
            sent = r["sentiment"]
            sent_str = f"+{sent:.2f}" if sent >= 0 else f"{sent:.2f}"
            color = "🟢" if sent >= 0.5 else ("🌱" if sent >= 0.0 else ("🟠" if sent >= -0.5 else "🔴"))
            print(f"  • {r['pair']} [{color} {sent_str} | {r['relation_type']}: {r['sub_type']}]")
            print(f"    💬 Active State : {r['dynamic_state']}")
            if r.get("narrative_rule"):
                print(f"    ✍️  WRITING RULE : {r['narrative_rule']}")
            if len(r.get("intra_slices", [])) > 1:
                print(f"    ⚡ INTRA-CHAPTER TURNING POINT: Contains {len(r['intra_slices'])} phases! Use `--phase pre` or `--phase post`.")
            print()
    else:
        print("  • Cast members operate on established solo / ambient dynamics.")

    # 4. Biometric Invariants & Key Physical Markers
    print(f"\n🧬 4. BIOMETRIC INVARIANTS & GEAR (UNBREAKABLE TRUTHS):")
    if brief.get("biometric_invariants"):
        for inv in brief["biometric_invariants"]:
            print(f"  • {inv['name']}:")
            print(f"    - Eyes & Hair : {inv['eye_color']} | {inv['hair_color']}")
            print(f"    - Scar / Mark : {inv['signature_mark']}")
            print(f"    - Gear / Relic: {inv['weapon']}")
            if inv['animus'] != "None":
                print(f"    - Animus Bond   : {inv['animus']}")
            if inv['forbidden']:
                print(f"    - 🚫 FORBIDDEN: {', '.join(inv['forbidden'])}")
    else:
        print("  • All character physical profiles conform to standard OKF records.")

    # 5. Sensory Palette of the Setting
    print(f"\n🌿 5. SETTING SENSORY PALETTE (DAN ABNETT BENCHMARK):")
    s = brief["sensory_palette"]
    print(f"  • Atmospheric Weight: {s['atmosphere']}")
    print(f"  • Scents (Smell)    : 👃 " + ", ".join(s['smells']))
    print(f"  • Acoustics (Sound) : 👂 " + ", ".join(s['sounds']))
    print(f"  • Textures (Touch)  : ✋ " + ", ".join(s['textures']))
    print(f"  • Light & Contrast  : 👁️  {s['lighting']}")

    # 6. Core Scene Objectives
    print(f"\n🎯 6. SCENE CONFLICT & DRAMATIC BEATS:")
    if brief.get("key_conflicts"):
        for c in brief["key_conflicts"]:
            print(f"  [!] {c}")
    else:
        print("  [!] Advance central narrative arc while grounding characters in physical tactile labor.")
        
    print(f"\n  Micro-Beat Pacing Plan:")
    print("  • Beat 1 (0–20%)  : Tactile Sensory Entrance (Physical labor, weather, smell)")
    print("  • Beat 2 (20–60%) : Complication & Dialogue Subtext (Tension, unspoken secrets)")
    print("  • Beat 3 (60–85%) : The Mechanical / Emotional Pivot (Action, reveal, or decision)")
    print("  • Beat 4 (85–100%): Domestic Hearth / Dread Cliffhanger (Bridge to next chapter)")
    print("=" * 80 + "\n")


def generate_llm_authoring_prompt(brief: Dict[str, Any]) -> str:
    """Format Scene Brief as a zero-slop system prompt for Claude / LLM generation."""
    lines = []
    lines.append(f"# SCENE AUTHORING DIRECTIVE: Book {brief['book']} Chapter {brief['chapter']:02d} - \"{brief['title']}\"")
    lines.append("")
    lines.append("## 1. SCENE CONSTRAINTS & COORDINATES")
    lines.append(f"- **POV Character**: {brief['pov']} (Deep 3rd-person limited; strictly NO head-hopping)")
    lines.append(f"- **Primary Setting**: {brief['setting']}")
    lines.append(f"- **Timeline Anchor**: {brief['timeline_anchor']}")
    lines.append(f"- **Word Target**: 3,500 – 4,000 words")
    lines.append("")
    
    if brief.get("continuity_bridge"):
        lines.append("## 2. PREVIOUS CHAPTER HOOK (CONTINUITY BRIDGE)")
        lines.append("You MUST seamlessly continue from this exact physical situation:")
        lines.append("```text")
        lines.append(brief['continuity_bridge']['hook_text'])
        lines.append("```")
        lines.append("")
        
    lines.append("## 3. STRICT INTERPERSONAL WRITING RULES")
    for r in brief.get("relational_dynamics", []):
        lines.append(f"- **{r['pair']}** ({r['relation_type']} / {r['sub_type']}, Affinity: {r['sentiment']:+.2f}):")
        lines.append(f"  - Dynamic: {r['dynamic_state']}")
        if r.get("narrative_rule"):
            lines.append(f"  - **RULE**: {r['narrative_rule']}")
    lines.append("")
    
    lines.append("## 4. BIOMETRIC INVARIANTS (NEVER HALLUCINATE OR CHANGE)")
    for inv in brief.get("biometric_invariants", []):
        lines.append(f"- **{inv['name']}**: Eyes: {inv['eye_color']} | Hair: {inv['hair_color']} | Marks: {inv['signature_mark']} | Weapon: {inv['weapon']}")
        if inv['forbidden']:
            lines.append(f"  - 🚫 NEVER WRITE: {', '.join(inv['forbidden'])}")
    lines.append("")
    
    lines.append("## 5. MANDATORY SENSORY PALETTE")
    s = brief["sensory_palette"]
    lines.append(f"- **Atmosphere**: {s['atmosphere']}")
    lines.append(f"- **Aromas to activate**: {', '.join(s['smells'])}")
    lines.append(f"- **Acoustics**: {', '.join(s['sounds'])}")
    lines.append(f"- **Tactile / Kinetic**: {', '.join(s['textures'])}")
    lines.append("")
    
    lines.append("## 6. ANTI-SLOP & STYLE INVARIANTS")
    lines.append("- ZERO filter words ('he saw', 'she felt', 'he realized', 'could hear'). Describe the world directly.")
    lines.append("- ZERO tricolons ('cold, dark, and silent') or generic AI cliches ('a testament to', 'dance of shadows').")
    lines.append("- Ground emotion in physical reflex, tool handling, and subtextual dialogue.")
    
    return "\n".join(lines)


build_scene_brief = generate_scene_brief
format_scene_prompt = generate_llm_authoring_prompt


def inject_scene_brief(brief: Dict[str, Any]) -> bool:
    """Inject or refresh a compact authoring context card as an HTML comment in chapter markdown."""
    fpath = Path(brief.get("file_path", ""))
    if not fpath.is_file():
        return False

    raw = fpath.read_text(encoding="utf-8")
    pal = brief.get("sensory_palette", {})
    
    lines = [
        "<!-- CANONFORGE SCENE BRIEF",
        f"Chapter: {brief.get('title', fpath.name)} | POV: {brief.get('pov', 'Unknown')}",
        f"Setting: {brief.get('setting', 'Unspecified')} | Timeline: {brief.get('timeline_anchor', 'Standard')}",
        "Sensory Palette:",
        f"  • Smell : {', '.join(pal.get('smells', [])) or 'None'}",
        f"  • Sound : {', '.join(pal.get('sounds', [])) or 'None'}",
        f"  • Touch : {', '.join(pal.get('textures', [])) or 'None'}",
        f"  • Atmosphere: {pal.get('atmosphere', 'Grounded')}",
        "Active Conflicts & Micro-Beats:",
        "  1. Tactile Entrance (0-20%): Establish physical labor and atmospheric temperature",
        "  2. Dialogue Subtext (20-60%): High stakes, hidden agendas, unspoken secrets",
        "  3. Mechanical Pivot (60-85%): Irreversible plot choice or physical action",
        "  4. Climax / Hearth  (85-100%): Emotional landing or dread cliffhanger",
        "-->\n"
    ]
    brief_block = "\n".join(lines)

    # Clean existing brief if present
    cleaned = re.sub(r"<!-- CANONFORGE SCENE BRIEF[\s\S]*?-->\n*", "", raw)

    if cleaned.startswith("---"):
        parts = cleaned.split("---", 2)
        if len(parts) >= 3:
            new_content = f"---{parts[1]}---\n\n{brief_block}\n{parts[2].lstrip()}"
        else:
            new_content = f"{brief_block}\n{cleaned}"
    else:
        new_content = f"{brief_block}\n{cleaned}"

    fpath.write_text(new_content, encoding="utf-8")
    return True


# ==============================================================================
# CLI RUNNER
# ==============================================================================

