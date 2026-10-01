## Summary of Changes

A clear and concise description of what this pull request does.

## Engine / Area Affected

- [ ] CLI Orchestrator (`okf ...`)
- [ ] Sensory Radar Engine (`okf sensory`)
- [ ] Deep POV Auditor (`okf pov`)
- [ ] Anti-Slop Prose Linter (`okf prose`)
- [ ] Manifest & TOC Gate (`okf verify`)
- [ ] Compilation & Export (`okf compile / export`)
- [ ] Documentation / Examples

## Quality & Invariants Checklist

- [ ] **Prose Preservation Guarantee**: No changes introduce lossy alterations or truncation to author markdown files.
- [ ] **Zero Creative IP Leak**: No private manuscripts, characters, or proprietary lore are committed in this PR.
- [ ] **Tests Added / Updated**: New features or bug fixes include test coverage in `tests/`.
- [ ] **Verification Passed**: Ran `uv run python3 -m unittest discover tests` and `./examples/aetheria/ax verify` (or `python3 -m okf_studio.cli verify examples/aetheria`) with 100% pass rate.
- [ ] **Performance**: New audit rules or dictionary lookups execute in <100ms.
