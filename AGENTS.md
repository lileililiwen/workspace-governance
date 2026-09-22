# Workspace Governance Agent Instructions

- Read `README.md`, `HANDOFF.md`, and the selected OpenSpec change before work.
- Use OpenSpec for non-trivial governance changes.
- Use BFS → DFS → BFS: map portfolio impact, implement one coherent contract, then re-audit all consumers.
- Run `python3 scripts/workspace_check.py --self-check` before completion.
- Run `python3 scripts/jenkins_manifest.py --check` for deployment-related changes.
- Existing projects keep declarations and exceptions; shared runtimes remain centralized.
- Build/test success is not runtime or release evidence.
- Keep exactly one `current_spec` line in `HANDOFF.md` while work is active.
- Each completed OpenSpec spec/change requires exactly two commits: first the implementation/tests/archive commit, then a HANDOFF.md-only pointer/evidence commit.
- Stop after the second commit.

Detailed rules: `.ai-rules/workflow.md` and `.ai-rules/completion.md`.
