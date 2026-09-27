# Shared rules baseline

## Read first

- `templates/project/AGENTS.md` — the only source of the shared rules text.
- `.ai-rules/workflow.md` — BFS → DFS → BFS, the OpenSpec lifecycle, and the
  two-commit rule.
- `.ai-rules/completion.md` — what "complete" requires.
- `openspec/specs/rules-baseline/spec.md` — the canonical contract.

## Run

- `python3 scripts/rules_drift.py --root .. --check` — a non-destructive,
  clause-level drift report. It changes no project file.
- Scaffold `HANDOFF.md` bodies surface from the audit as `HANDOFF_SCAFFOLD`;
  replacing them is product-owned work.

## Rules of the road

- `templates/project/` is the single source; `scripts/init_project.py` reads
  it from disk. Never copy a second set of the rules into a script.
- Repositories may document the shared rules in their own words; the drift
  report is triage, not a mandate to paste canonical paragraphs.
