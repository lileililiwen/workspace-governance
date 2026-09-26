# Workspace Governance Handoff

current_spec: none

## Current state

Two changes shipped in sequence.

**1. `registry-and-declaration-integrity`** (archived
`openspec/changes/archive/2026-09-26-registry-and-declaration-integrity/`,
canonical spec `openspec/specs/registry-integrity/spec.md`). Registered the 11
discovered declarations, corrected six declaration identity/format defects,
created four missing declarations, added duplicate id/path guards, derived and
enforced the canonical project id in `init_project.py`, and made
`maturity_audit.py` report the authoritative `workspace_check` counts.
Unregistered discovery is now an ERROR via
`discovery.unregistered_policy: "fail"`.

**2. `shared-rules-single-source`** (archived
`openspec/changes/archive/2026-09-26-shared-rules-single-source/`, canonical
spec `openspec/specs/rules-baseline/spec.md`). Made `templates/project/**` the
only source of the shared rules and had `init_project.py` read it from disk,
deleting the duplicate embedded copy that had drifted from the on-disk
templates. Added `scripts/rules_drift.py`, a **non-destructive** clause-level
drift report with no `--apply`, and surfaced scaffold `HANDOFF.md` files from
the audit as `HANDOFF_SCAFFOLD`. Created `crossalheart`'s missing rules,
clearing the workspace audit's last two errors.

The read-only **Forge governance adapter**
(`scripts/forge_governance_adapter.py`) is unchanged; its canonical spec is
`openspec/specs/forge-governance-adapter/spec.md`.

## Authored, not yet implemented

Two packages are fully authored as OpenSpec changes and are ready to implement
in a fresh conversation:

- `openspec/changes/portfolio-vocabulary-normalization/` (package 3) — canonical
  `kind`/`profile` sets plus a single `vocabulary.json` sourcing the placeholder
  and secret word lists.
- `openspec/changes/governance-front-door/` (package 8) — one auto-triggering
  skill that routes to the governance references.

Four cross-repo packages are specified implementation-ready in
`docs/package-backlog.md`: 4 `gate-run-evidence` (`driftwatchdog`), 5
`platform-adoption-dotnet`, 6 `platform-adoption-rust`, 7
`contracts-single-source`. Each is authored and implemented in its own
repository, never from here.

## Evidence

- `python3 -m unittest discover -s tests` — 122 tests, 0 failures.
- `python3 scripts/workspace_check.py --self-check` — 0 errors, 0 warnings.
- `python3 scripts/workspace_check.py --root .. --audit --json` — **0 errors**,
  18 warnings (11 `HANDOFF_SCAFFOLD`, 7 `DEPLOYMENT_PROMOTION_STALE`), down from
  14 errors / 18 warnings before the two changes.
- `python3 scripts/maturity_audit.py --root .. --json` — reports the same
  0 errors / 18 warnings as the audit; `evidence_planned` is 0.
- `python3 scripts/rules_drift.py --root .. --check` — 81 triage findings
  (clause-level drift across adopted projects); every project file is unchanged
  by the run.
- `python3 scripts/jenkins_manifest.py --check --root /home/paul/code` —
  7 projects, 0 errors.
- `python3 scripts/auto_gate.py --self-check --no-deployment` — PASS.
- `node scripts/check-openspec-change-names.mjs` — valid;
  `openspec validate --all --strict --no-interactive` — 6 passed, 0 failed
  (6 canonical specs, 0 active changes).
- `git diff --check` — clean.
- Commits: `039ae39` and `91d9fd9` (implementation + tests + archive), each
  followed by a HANDOFF-only commit.

## Portfolio impact observed

The `.ai-rules` baseline change is deliberately non-destructive. A first
implementation made whole canonical paragraphs mandatory and shipped `--apply`;
running it appended a duplicate canonical block to **60 project files**,
including well-maintained ones such as `mewo` whose text already expressed the
same rules. That was measured, judged a regression, and reverted byte-for-byte
before the change was re-scoped to a report-only clause check. The portfolio
`git diff` for `.ai-rules` is clean apart from `crossalheart`'s newly created
files.

11 adopted projects still carry scaffold `HANDOFF.md` bodies (reported as
`HANDOFF_SCAFFOLD`). The 7 `DEPLOYMENT_PROMOTION_STALE` warnings remain triaged:
re-promotion was not performed because it would record a deployable decision at
the current revision without a new release.

Sibling repositories still hold uncommitted declaration and rules files created
by these two changes (the 10 declarations plus `crossalheart`'s rules and
`.ai-gate`); they were left uncommitted in their own repositories.

## Next action

1. Implement package 3 (`portfolio-vocabulary-normalization`) from its authored
   change, then archive it with the two required commits.
2. Implement package 8 (`governance-front-door`) the same way.
3. Take packages 4–7 to their owning repositories via `docs/package-backlog.md`;
   each is a separate conversation and a separate repository.
4. Replace the 11 scaffold `HANDOFF.md` bodies as each product's own state is
   recorded (product-owned work).
5. Re-promote each pilot project at its current `HEAD` once its release pipeline
   produces real artifacts, and replace the pilot-context `release_evidence`
   placeholders.
6. Commit the sibling declaration/rules edits in their own repositories when
   those repositories' pending work is ready.

## Evidence boundary

This repository can prove registry/schema/checker behavior, capability
declaration shape, release-evidence shape, the deployable+release-evidence
gate, the product-code quality rule, the deployment promotion
mechanism, the rules-baseline drift report, and the Forge governance adapter
contract. It cannot prove that the seven promoted projects actually build, pass
tests, deploy, or are runtime-healthy; those claims require the promoted
projects' own verification commands and jenkins-local runtime observation. The
adapter likewise cannot prove a project's runtime or release health;
it only translates this repository's own audit findings.

## OpenSpec workflow

Select one active change with `openspec list`, run the local checker and
project gate before archive, validate strictly, archive canonical specs, then
create the required two commits. Each completed OpenSpec spec/change requires
exactly two commits: first the implementation/tests/archive commit, then a
HANDOFF.md-only pointer/evidence commit.
