# Tasks: Classify dirty gate-manifest debt

## 1. BFS — Baseline and impact coverage

- [x] Measure the full binder debt record and confirm six dirty-manifest reasons currently classify as `?`.
- [x] Define class G as a non-writing owner action and preserve unknown-reason behavior.
- [x] Bound file writes to workspace-governance; sibling manifests are evidence only.
- **Done when** class G, boundaries, and verification oracles agree across proposal, design, and spec.

## 2. DFS — Requirement-by-requirement implementation

- [x] Add regression tests for exact dirty-manifest classification, owner guidance, no remedy dispatch, and no target mutation.
- [x] Implement class G as a reporting-only debt class and preserve A-F and `?` behavior.
- [x] Include the regenerated `gate-debt.json` snapshot from the authorized full binder run.
- **Done when** dirty-manifest reasons are recognized and the driver never edits the target manifest.

## 3. BFS — Cross-surface regression and completeness

- [x] Run the full governance unit suite (849 passed, 1 skipped) and strict OpenSpec validation (14/14).
- [x] Run driver dry mode against the workspace debt record: eight dirty-manifest reasons are class G, and the three owner decisions remain classes C, E, and F; no unknown entries remain.
- [x] Run workspace self-check (0 errors, 0 warnings), the project governance check (0 errors, 0 warnings), auto-gate (PASS, 0 errors, 0 warnings), change-name validation, and `git diff --check`.
- [x] Verify all 76 sibling gate manifests remain unchanged after the driver dry run (0 digest changes).
- **Done when** implementation, report contract, and measured fleet state agree.

## 4. Verification

- [x] Record exact results and the two-commit evidence contract in `HANDOFF.md`; add the resulting commit references in its HANDOFF-only commit.
- [x] Commit explicit package paths and debt snapshot as commit 1; commit `HANDOFF.md` only as commit 2.
- [x] Keep the change active and unarchived.
