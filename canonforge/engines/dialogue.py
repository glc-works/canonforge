"""
play_dialogue.py

Authoritative Interactive Ink Story & Dialogue Runner for CanonForge Studio.
Parses and plays Inkle Ink (.ink) dialogue trees in the terminal, validates all
story branching pathways, and can export interactive HTML visual novel players.
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

from typing import Dict, List, Tuple, Optional, Any

def _find_project_dir() -> Path:
    cwd = Path.cwd().resolve()
    for parent in [cwd, *cwd.parents]:
        if (parent / "universe.yaml").exists() or (parent / "dialogue").exists():
            return parent
    return cwd

PROJECT_DIR = _find_project_dir()
DIALOGUE_DIR = PROJECT_DIR / "dialogue"

class InkKnot:
    def __init__(self, name: str):
        self.name = name
        self.lines: List[str] = []
        self.choices: List[Tuple[str, str]] = [] # (choice_text, target_divert)
        self.divert: Optional[str] = None
        self.var_mutations: List[Tuple[str, Any]] = []

class InkStory:
    def __init__(self, root_file: Path):
        self.root_file = root_file
        self.variables: Dict[str, Any] = {}
        self.knots: Dict[str, InkKnot] = {}
        self.start_knot: Optional[str] = None
        self._load_and_parse(root_file)

    def _parse_val(self, val_str: str) -> Any:
        val = val_str.strip().strip('"').strip("'")
        if val.lower() == "true":
            return True
        if val.lower() == "false":
            return False
        try:
            return int(val)
        except ValueError:
            try:
                return float(val)
            except ValueError:
                return val

    def _load_and_parse(self, file_path: Path):
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        current_knot: Optional[InkKnot] = None

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            i += 1

            if not line or line.startswith("//"):
                continue

            # Includes
            inc_match = re.match(r"^INCLUDE\s+([^\s]+)", line)
            if inc_match:
                inc_path = file_path.parent / inc_match.group(1)
                if inc_path.exists():
                    self._load_and_parse(inc_path)
                continue

            # Variable Declarations
            var_match = re.match(r"^VAR\s+([a-zA-Z_0-9]+)\s*=\s*(.+)$", line)
            if var_match:
                k, v = var_match.group(1), var_match.group(2)
                self.variables[k] = self._parse_val(v)
                continue

            # Knot definition
            knot_match = re.match(r"^===\s*([a-zA-Z_0-9]+)\s*===$", line)
            if knot_match:
                k_name = knot_match.group(1)
                current_knot = InkKnot(k_name)
                self.knots[k_name] = current_knot
                if not self.start_knot:
                    self.start_knot = k_name
                continue

            if not current_knot:
                continue

            # Variable Mutation inside knot: ~ x = val
            mut_match = re.match(r"^~\s*([a-zA-Z_0-9]+)\s*=\s*(.+)$", line)
            if mut_match:
                var_name, raw_val = mut_match.group(1), mut_match.group(2)
                current_knot.var_mutations.append((var_name, self._parse_val(raw_val)))
                continue

            # Choices: * [Text] -> divert or * Text -> divert
            choice_match = re.match(r"^[\*\+]\s*(?:\[([^\]]+)\]|([^\-\>]+))\s*$", line)
            if choice_match:
                choice_text = (choice_match.group(1) or choice_match.group(2)).strip()
                # Check next line for divert -> target
                target = None
                if i < len(lines) and "->" in lines[i]:
                    d_line = lines[i].strip()
                    d_match = re.search(r"->\s*([a-zA-Z_0-9]+)", d_line)
                    if d_match:
                        target = d_match.group(1)
                        i += 1
                if not target:
                    target = "END"
                current_knot.choices.append((choice_text, target))
                continue

            # Divert at end of knot: -> target
            div_match = re.match(r"^->\s*([a-zA-Z_0-9]+)$", line)
            if div_match:
                current_knot.divert = div_match.group(1)
                continue

            # Normal prose / speaker line
            current_knot.lines.append(line)

ANSI_COLORS = [
    "\033[96m", # Cyan
    "\033[93m", # Yellow
    "\033[91m", # Red
    "\033[92m", # Green
    "\033[95m", # Magenta
    "\033[94m", # Blue
]

def get_speaker_color(speaker: str) -> str:
    idx = sum(ord(c) for c in speaker) % len(ANSI_COLORS)
    return ANSI_COLORS[idx]

def play_terminal(story: InkStory):
    """Interactive CLI visual novel play session."""
    print("\n" + "=" * 75)
    print(f"CANONFORGE INK INTERACTIVE STORY ENGINE: {story.root_file.name}")
    print("=" * 75)

    current_knot_name = story.start_knot
    state = dict(story.variables)

    while current_knot_name and current_knot_name != "END":
        if current_knot_name not in story.knots:
            print(f"❌ Error: Divert to unknown knot '{current_knot_name}'.")
            break

        knot = story.knots[current_knot_name]

        # Apply variable mutations
        for var_name, new_val in knot.var_mutations:
            state[var_name] = new_val

        # Display lines
        for line in knot.lines:
            # Colorize speaker dialogue dynamically if speaker tag matches
            match = re.match(r"^([A-Z0-9_\-\s]{2,20}):\s*(.*)$", line)
            if match:
                color = get_speaker_color(match.group(1).strip())
                print(f"{color}{line}\033[0m")
            else:
                print(f"  {line}")

        # If choices exist, display and await user input
        if knot.choices:
            print("\n" + "-" * 50)
            print("YOUR CHOICE:")
            for idx, (c_text, _) in enumerate(knot.choices, 1):
                print(f"  [{idx}] {c_text}")

            print("-" * 50)
            # Variable state HUD
            hud_items = [f"{k}: {v}" for k, v in state.items() if not k.startswith("scene")]
            print(f"  [HUD State] {' | '.join(hud_items)}")

            while True:
                try:
                    choice_in = input("\nSelect option (1-" + str(len(knot.choices)) + ") > ").strip()
                    c_idx = int(choice_in) - 1
                    if 0 <= c_idx < len(knot.choices):
                        _, next_knot = knot.choices[c_idx]
                        current_knot_name = next_knot
                        print()
                        break
                    else:
                        print("Invalid selection. Try again.")
                except (ValueError, KeyboardInterrupt, EOFError):
                    print("\nExiting dialogue session.")
                    return
        elif knot.divert:
            current_knot_name = knot.divert
        else:
            break

    print("\n" + "=" * 75)
    print("DIALOGUE END REACHED. Final Story Variables:")
    for k, v in state.items():
        print(f"  • {k:<20} : {v}")
    print("=" * 75 + "\n")

def test_reachability(story: InkStory):
    """Deterministic path-walking to test all branches and verify reachability."""
    print(f"\n🔍 Testing all branching pathways in: {story.root_file.name}")
    visited_knots = set()
    errors = []

    def walk(knot_name: str, path: List[str]):
        if knot_name == "END":
            return
        if knot_name not in story.knots:
            errors.append(f"Broken divert -> '{knot_name}' from path: {' -> '.join(path)}")
            return

        visited_knots.add(knot_name)
        knot = story.knots[knot_name]

        if knot.choices:
            for _, target in knot.choices:
                walk(target, path + [f"{knot_name} (choice)"])
        elif knot.divert:
            walk(knot.divert, path + [f"{knot_name} (divert)"])

    walk(story.start_knot, [story.start_knot])

    print(f"  ✓ Total Knots Defined: {len(story.knots)}")
    print(f"  ✓ Knots Reached: {len(visited_knots)}")
    unreached = set(story.knots.keys()) - visited_knots
    if unreached:
        print(f"  ⚠️ Warning: {len(unreached)} unreachable dead knot(s): {', '.join(unreached)}")
    if errors:
        print(f"  ❌ Errors found ({len(errors)}):")
        for e in errors:
            print(f"     • {e}")
        return False
    else:
        print("  🎉 100% REACHABLE: All dialogue branches divert to valid targets and resolve cleanly!\n")
        return True

def export_html_player(story: InkStory, output_path: Path):
    """Generate a self-contained responsive HTML visual novel player."""
    knots_json = {}
    for k_name, knot in story.knots.items():
        knots_json[k_name] = {
            "name": knot.name,
            "lines": knot.lines,
            "choices": knot.choices,
            "divert": knot.divert,
            "mutations": knot.var_mutations
        }

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CanonForge: {story.root_file.stem} (Interactive Dialogue)</title>
    <style>
        :root {{
            --bg: #0f1117;
            --card: #181b26;
            --text: #e6edf3;
            --accent: #d29922;
            --border: #30363d;
        }}
        body {{
            background: var(--bg);
            color: var(--text);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Georgia, serif;
            margin: 0;
            padding: 20px;
            display: flex;
            justify-content: center;
        }}
        .container {{
            max-width: 800px;
            width: 100%;
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }}
        h1 {{
            color: var(--accent);
            font-size: 1.6rem;
            margin-top: 0;
            border-bottom: 1px solid var(--border);
            padding-bottom: 12px;
        }}
        .hud {{
            background: rgba(255,255,255,0.05);
            padding: 10px 16px;
            border-radius: 6px;
            font-size: 0.9rem;
            margin-bottom: 20px;
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            color: #8b949e;
        }}
        .dialogue-log {{
            min-height: 250px;
            margin-bottom: 24px;
            line-height: 1.7;
            font-size: 1.05rem;
        }}
        .line {{
            margin-bottom: 12px;
            animation: fadeIn 0.3s ease;
        }}
        .speaker {{ font-weight: bold; }}
        .prose {{ color: #c9d1d9; font-style: italic; }}
        .choices {{
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin-top: 20px;
        }}
        button.choice-btn {{
            background: #21262d;
            border: 1px solid var(--border);
            color: var(--text);
            padding: 14px 18px;
            border-radius: 8px;
            font-size: 1rem;
            cursor: pointer;
            text-align: left;
            transition: all 0.2s ease;
        }}
        button.choice-btn:hover {{
            background: #30363d;
            border-color: var(--accent);
            transform: translateX(4px);
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(6px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>CanonForge Story Player: {story.root_file.stem}</h1>
        <div class="hud" id="hud">Loading story state...</div>
        <div class="dialogue-log" id="log"></div>
        <div class="choices" id="choices"></div>
    </div>

    <script>
        const knots = {json.dumps(knots_json)};
        let state = {json.dumps(story.variables)};
        let currentKnot = "{story.start_knot}";

        function updateHUD() {{
            const hud = document.getElementById("hud");
            const items = Object.entries(state)
                .filter(([k]) => !k.startsWith("scene"))
                .map(([k, v]) => `<span><strong>${{k}}</strong>: ${{v}}</span>`);
            hud.innerHTML = items.join(" • ");
        }}

        function getSpeakerColor(speaker) {{
            let hash = 0;
            for (let i = 0; i < speaker.length; i++) {{
                hash = speaker.charCodeAt(i) + ((hash << 5) - hash);
            }}
            const hue = Math.abs(hash) % 360;
            return `hsl(${{hue}}, 75%, 70%)`;
        }}

        function renderKnot(knotName) {{
            if (!knotName || knotName === "END" || !knots[knotName]) {{
                document.getElementById("choices").innerHTML = "<p><em>--- Scene Concluded ---</em></p>";
                return;
            }}

            const knot = knots[knotName];
            const log = document.getElementById("log");
            const choicesContainer = document.getElementById("choices");

            // Apply mutations
            if (knot.mutations) {{
                knot.mutations.forEach(([varName, val]) => {{
                    state[varName] = val;
                }});
                updateHUD();
            }}

            // Render lines
            knot.lines.forEach(l => {{
                const div = document.createElement("div");
                div.className = "line";
                const match = l.match(/^([A-Z0-9_\\-\\s]{{2,20}}):\\s*(.*)$/);
                if (match) {{
                    const speaker = match[1].trim();
                    const color = getSpeakerColor(speaker);
                    div.innerHTML = `<span class="speaker" style="color: ${{color}}">${{l}}</span>`;
                }} else {{
                    div.className = "line prose";
                    div.textContent = l;
                }}
                log.appendChild(div);
            }});

            choicesContainer.innerHTML = "";

            if (knot.choices && knot.choices.length > 0) {{
                knot.choices.forEach(([text, target]) => {{
                    const btn = document.createElement("button");
                    btn.className = "choice-btn";
                    btn.textContent = text;
                    btn.onclick = () => {{
                        const chosenDiv = document.createElement("div");
                        chosenDiv.className = "line";
                        chosenDiv.innerHTML = `<strong>➤ You chose:</strong> <em>${{text}}</em>`;
                        chosenDiv.style.color = "var(--accent)";
                        chosenDiv.style.borderTop = "1px dashed var(--border)";
                        chosenDiv.style.paddingTop = "8px";
                        log.appendChild(chosenDiv);
                        renderKnot(target);
                    }};
                    choicesContainer.appendChild(btn);
                }});
            }} else if (knot.divert) {{
                renderKnot(knot.divert);
            }} else {{
                choicesContainer.innerHTML = "<p><em>--- Scene Concluded ---</em></p>";
            }}
        }}

        updateHUD();
        renderKnot(currentKnot);
    </script>
</body>
</html>
"""
    output_path.write_text(html_content, encoding="utf-8")
    try:
        rel_path = output_path.relative_to(PROJECT_DIR)
    except ValueError:
        rel_path = output_path
    print(f"🎭 Interactive HTML Dialogue Player exported to: {rel_path}")
    print(f"   Size: {output_path.stat().st_size / 1024:.1f} KB (Self-contained, opens in any web browser)")

def main():
    parser = argparse.ArgumentParser(description="CanonForge Interactive Ink Dialogue Player")
    parser.add_argument("--file", "-f", help="Path to .ink dialogue file")
    parser.add_argument("--test", "--validate", action="store_true", help="Automated graph traversal and reachability test")
    parser.add_argument("--export-html", action="store_true", help="Export standalone interactive HTML player")
    args = parser.parse_args()

    if args.file:
        file_path = PROJECT_DIR / args.file if not Path(args.file).is_absolute() else Path(args.file)
    else:
        # Auto-discover first .ink file in dialogue directory
        ink_candidates = list(DIALOGUE_DIR.glob("*.ink")) if DIALOGUE_DIR.exists() else []
        if ink_candidates:
            file_path = ink_candidates[0]
        else:
            print("❌ Error: No .ink dialogue file specified and none found in dialogue/ folder.")
            sys.exit(1)
    if not file_path.exists():
        print(f"❌ Error: Dialogue file not found: {file_path}")
        sys.exit(1)

    story = InkStory(file_path)

    if args.test:
        test_reachability(story)
    elif args.export_html:
        out_html = DIALOGUE_DIR / f"{file_path.stem}.html"
        export_html_player(story, out_html)
    else:
        play_terminal(story)

if __name__ == "__main__":
    main()
