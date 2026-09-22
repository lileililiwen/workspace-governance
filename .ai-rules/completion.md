# Completion Rules

A governance change is complete only when:

- registry and schema requirements are covered;
- project declarations and generated deployment output are validated;
- required scenarios have tests;
- missing or invalid projects fail closed;
- `python3 -m unittest discover -s tests -v` passes;
- `python3 scripts/workspace_check.py --self-check` passes;
- deployment-related changes pass `python3 scripts/jenkins_manifest.py --check`;
- `git diff --check` passes;
- no secrets appear in tracked files;
- `HANDOFF.md` records exact evidence and unresolved adoption gaps.

Build/test/skeleton success is not runtime or release completion.

Each completed OpenSpec spec/change requires exactly two commits: first the implementation/tests/archive commit, then a HANDOFF.md-only pointer/evidence commit. Stop after commit 2.
