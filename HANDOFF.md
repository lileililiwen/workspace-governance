# Workspace Governance Handoff

current_spec: deployable-batch-onboarding

## Current state

The governance repository now owns a portable, fail-closed **product-code
quality gate** at `scripts/product_code_quality.py`. The gate detects two
failure modes the structural audit cannot: test code leaking into product
source (including lexical Rust `#[cfg(test)]` containment) and placeholder
debt across product files (TODO, FIXME, XXX, HACK, placeholder, stub,
unimplemented!, todo!). The checker has three outcomes (`PASS`, `FAIL`,
`REVIEW_REQUIRED`) and three exit codes (0/1/2); a missing or invalid
`quality` block, an unsupported language, an exclusion that escapes the
project root, or an unreadable product file is `REVIEW_REQUIRED`, never a
guessed pass. The audit translates `FAIL` to `ERROR` and `REVIEW_REQUIRED`
to `WARNING` so the existing finding vocabulary is unchanged.

The change is documented at `docs/product-code-quality.md` and archived in
`openspec/changes/archive/2026-09-24-product-code-quality-gates/`. The
canonical spec lives at `openspec/specs/product-code-quality-boundary/spec.md`.
The workspace-governance repository binds the checker to its own `scripts/`
product root as the canonical example.

## Evidence

- `python3 -m unittest discover -s tests -v` — 50 tests, 0 failures (32 new
  product-quality scenarios + 18 existing).
- `python3 scripts/workspace_check.py --self-check` — 0 errors, 0 warnings.
- `python3 scripts/jenkins_manifest.py --check` — 0 errors, 0 deployable entries.
- `python3 scripts/auto_gate.py --self-check` — PASS.
- `node scripts/check-openspec-change-names.mjs` — valid.
- `openspec validate --all --strict --no-interactive` — 4 passed, 0 failed.
- `git diff --check` — clean; no secrets, host paths, or runtime credentials
  added.
- Commit `8ef7f5b` (the implementation + tests + archive commit) brings in the
  checker, the schema, the audit integration, the docs, the self-binding, the
  init template update, and the canonical spec.

## Portfolio impact observed

The new rule is opt-in: projects that omit the `quality` block are untouched.
The previous HANDOFF's pre-existing `mewo` `RELEASE_EVIDENCE_REQUIRED` finding
remains outstanding and is the next-action candidate for the upcoming
`deployable-batch-onboarding` change, which adds the promotion ledger and the
checker rule that prevents `deployable: true` from being hand-edited into
existence.

## Next action

1. Pick up `deployable-batch-onboarding` (the next active OpenSpec change with
   0/18 tasks). Its proposal adds `scripts/promote_project.py`, an
   `deployment/promotions.json` ledger, and a `DEPLOYMENT_PROMOTION` checker
   rule.
2. While implementing, decide whether the `mewo` self-declared
   `deployable: true` should be reverted to `false` (it is not in the
   registry and has no `jenkins_job`) or whether `mewo` should be registered
   with a complete `release_evidence` block. Either resolution clears the
   pre-existing `RELEASE_EVIDENCE_REQUIRED` finding.
3. After archive, the only remaining proposed change is `forge-governance-adapter`
   (a small read-only shim translating audit results into Forge's
   governance-provider contract).

## Evidence boundary

This repository can prove registry/schema/checker behavior, capability
declaration shape, release-evidence shape, the deployable+release-evidence
gate, and the new product-code quality rule. It cannot prove that every
registered project builds, passes tests, deploys, or is runtime-healthy.
Those claims require project-specific evidence.

## OpenSpec workflow

Select one active change with `openspec list`, run the local checker and
project gate before archive, validate strictly, archive canonical specs, then
create the required two commits. Each completed OpenSpec spec/change requires
exactly two commits: first the implementation/tests/archive commit, then a
HANDOFF.md-only pointer/evidence commit.
