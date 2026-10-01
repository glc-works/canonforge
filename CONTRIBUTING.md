# Contributing to OKF Studio

Thank you for your interest in contributing to **Open Knowledge Fiction (OKF) Studio**!

OKF Studio is built to elevate literary fiction with aerospace-grade determinism, deep sensory immersion, and zero author prose distortion. We welcome contributions from novelists, software engineers, and editors alike.

---

## Core Invariants

All contributions must respect three inviolable project principles:

1. **Lossless Prose Preservation**: Tooling must never truncate, summarize, or alter an author's raw prose in markdown files without explicit author intent.
2. **Zero Creative IP Contamination**: Never commit private manuscripts, proprietary world bibles, or confidential game databases into this repository. All tests and examples must use the public demo universe (`examples/aetheria`).
3. **Sub-100ms Deterministic Execution**: Audit and linting passes must remain blazing fast. Do not introduce heavy runtime dependencies or network calls into the core verification loop.

---

## Development Setup with `uv`

We recommend [uv](https://github.com/astral-sh/uv) by Astral for ultrafast Python development.

```bash
# Clone the repository
git clone https://github.com/glc-works/okf-studio.git
cd okf-studio

# Create virtualenv and install editable package
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

---

## Running Verification & Tests

Before opening a pull request, verify that all test suites pass:

```bash
# 1. Run unit test suite
python3 -m unittest discover tests

# 2. Verify the demo universe
python3 -m okf_studio.cli verify examples/aetheria

# 3. Test Deep POV and Sensory Radar
python3 -m okf_studio.cli sensory examples/aetheria/manuscript/book-1/chapters/ch01-the-sky-docks.md
python3 -m okf_studio.cli pov examples/aetheria/manuscript/book-1/chapters/ch01-the-sky-docks.md
python3 -m okf_studio.cli prose examples/aetheria/manuscript/book-1/chapters/ch01-the-sky-docks.md
```

All commands must exit with code `0`.

---

## Code Architecture

- **`okf_studio/engines/`**:
  - `sensory.py`: 5-domain sensory radar calculator.
  - `sensory_dictionary.py`: 697-lemma tokenized trie and dictionary loader.
  - `pov.py`: Deep POV psychic distance & filter-word auditor.
  - `prose.py`: Anti-slop cadence linter (tricolons, weak verbs, passive voice).
  - `toc.py`: Manifest and table-of-contents validation.
  - `compiler.py` & `exporter.py`: Lossless manuscript compilation.
- **`okf_studio/schemas/`**: JSON Schema definitions (OKF v0.3 chapter, lore, manifest).
- **`okf_studio/data/`**: Canonical YAML dictionaries.
- **`examples/aetheria/`**: Canonical reference universe (*Aetheria: Skies of Iron*).

---

## Submitting Pull Requests

1. Fork the repo and create your feature branch: `git checkout -b feat/sensory-custom-overlay`.
2. Commit your changes with clear, descriptive commit messages (following Conventional Commits).
3. Push to your branch and open a PR against `main`.
4. Fill out the [Pull Request Template](.github/PULL_REQUEST_TEMPLATE.md).
