# Workspace Governance Handoff

current_spec: product-code-quality-gates

## Current state

The governance repository now owns a versioned, additive **platform capability
and release evidence vocabulary** for project declarations. Projects MAY
declare `capabilities` and `release_evidence` blocks in `.project.json`; the
audit reports the declared state and the presence or absence of native
evidence without ever promoting a capability or release field to `verified` on
its own. A `deployable: true` project must carry a complete `release_evidence`
record; otherwise the audit raises `RELEASE_EVIDENCE_INSUFFICIENT` and the
Jenkins manifest blocks the entry.

The change is documented at `docs/capabilities.md` and archived in
`openspec/changes/archive/2026-09-24-platform-capability-and-release-governance/`.
The canonical spec lives at `openspec/specs/platform-capability-manifest/spec.md`.

## Evidence

- `python3 -m unittest discover -s tests -v` — 18 tests, 0 failures.
- `python3 scripts/workspace_check.py --self-check` — 0 errors, 0 warnings.
- `python3 scripts/jenkins_manifest.py --check` — 0 errors, 0 deployable entries.
- `python3 scripts/auto_gate.py --self-check` — PASS.
- `node scripts/check-openspec-change-names.mjs` — valid.
- `openspec validate --all --strict --no-interactive` — 4 passed, 0 failed.
- `git diff --check` — clean; no secrets, host paths, or runtime credentials
  added.
- Commit `0c2eb85` (the implementation + tests + archive commit) contains the
  full bring-up of the `openspec/` working tree, including the three
  unarchived changes (`product-code-quality-gates`,
  `deployable-batch-onboarding`, `forge-governance-adapter`) so the change
  tree is intact in version control.

## Portfolio impact observed

The new `RELEASE_EVIDENCE_REQUIRED` rule already caught a pre-existing
portfolio inconsistency: an unregistered `mewo` project self-declared
`deployable: true` without `release_evidence`. The audit surfaces this as
`RELEASE_EVIDENCE_REQUIRED` (ERROR). This is the new rule working as designed;
it is not a regression introduced by this change. The next action below names
it explicitly.

## Next action

1. Pick up `product-code-quality-gates` (the next active OpenSpec change with
   0/18 tasks). Its proposal adds a `scripts/product_code_quality.py` checker
   for test-code leakage and placeholder thresholds in declared product roots.
2. While implementing that, decide whether the `mewo` self-declared
   `deployable: true` should be reverted to `false` (it is not in the registry
   and has no `jenkins_job` either) or whether `mewo` should be registered
   with a complete `release_evidence` block. Either resolution clears the
   `RELEASE_EVIDENCE_REQUIRED` finding.
3. Continue the adoption queue in registry order afterwards.

## Evidence boundary

This repository can prove registry/schema/checker behavior, capability
declaration shape, release-evidence shape, and the deployable+release-evidence
gate. It cannot prove that every registered project builds, passes tests,
deploys, or is runtime-healthy. Those claims require project-specific
evidence.

## OpenSpec workflow

Select one active change with `openspec list`, run the local checker and
project gate before archive, validate strictly, archive canonical specs, then
create the required two commits. Each completed OpenSpec spec/change requires
exactly two commits: first the implementation/tests/archive commit, then a
HANDOFF.md-only pointer/evidence commit.
