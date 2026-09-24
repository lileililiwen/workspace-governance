# Workspace Governance Handoff

current_spec: forge-governance-adapter

## Current state

The governance repository now owns a fail-closed **deployment promotion
mechanism** at `scripts/promote_project.py`. A project becomes
`deployable: true` only through a recorded transaction: the script runs
the per-project audit, verifies a compose file, requires an explicit
`--evidence-ref`, mutates the `deployment.*` block in the project's
`.project.json`, and appends a tamper-evident entry to
`deployment/promotions.json`. The audit gains two new rules:
`DEPLOYMENT_PROMOTION` (ERROR) refuses a hand-edited `deployable: true`
without a matching ledger entry, and `DEPLOYMENT_PROMOTION_STALE`
(WARNING) surfaces a recorded revision that differs from the project's
current `HEAD` (triage information, never a silent block). A SHA-256
sidecar (`deployment/promotions.sha256`) records the entries hash; any
divergence raises `PROMOTIONS_LEDGER_TAMPERED` (ERROR) on the next read.

The change is documented at `docs/deployment-promotion.md` and archived
in `openspec/changes/archive/2026-09-24-deployable-batch-onboarding/`.
The canonical spec lives at
`openspec/specs/deployable-batch-onboarding/spec.md`.

The pilot batch is on the record. Seven second-batch products
(`alethefy`, `crossify`, `cvunify`, `hermexa`, `hypora`, `lexora`,
`openaccounting`) are promoted with `actor:
workspace-governance/batch` and `evidence_ref: local:HEAD:<sha>`; their
`.project.json` files now declare `deployable: true` and a `configured`
`release_evidence` block pointing at pilot-context placeholder artefacts
that name the source revision at promotion and the project's
verification command. `deployment/projects.json` is regenerated with
seven eligible projects. The pre-existing `mewo` self-declared
`deployable: true` is reverted to `false` (in the mewo repository, not
in this commit) to clear the `DEPLOYMENT_PROMOTION`, `DEPLOYMENT_JOB`,
and `RELEASE_EVIDENCE_REQUIRED` findings; mewo is not in the registry,
so the new audit rule did not apply to it.

## Evidence

- `python3 -m unittest discover -s tests` — 69 tests, 0 failures
  (19 new promotion scenarios + 50 existing).
- `python3 scripts/workspace_check.py --self-check` — 0 errors,
  0 warnings.
- `python3 scripts/jenkins_manifest.py --check --root /home/paul/code`
  — 7 projects, 0 errors.
- `node scripts/check-openspec-change-names.mjs` — valid.
- `openspec validate --all --strict --no-interactive` — 4 passed,
  0 failed (3 specs + 1 active change).
- `git diff --check` — clean; no secrets, host paths, or runtime
  credentials added.
- Commit `6c5aac4` (the implementation + tests + archive commit) brings
  in the promote script, the ledger validator and sidecar, the
  `DEPLOYMENT_PROMOTION` / `DEPLOYMENT_PROMOTION_STALE` audit rules, the
  pilot batch promotions, the regenerated `deployment/projects.json`,
  the new `docs/deployment-promotion.md`, and the archive/spec for the
  OpenSpec change.

## Portfolio impact observed

The promoted projects audit with one `DEPLOYMENT_PROMOTION_STALE`
warning each: the recorded revision in the ledger is the pre-promote
SHA, and the promote commit in each pilot project moved the `HEAD`
forward. The warning is honest triage information — promotion is still
a valid human decision, and the next `promote_project.py` invocation
with the new `HEAD` will append a renewal entry. The
`mewo` `DISCOVERED_UNREGISTERED` finding remains; mewo is not in the
registry and a future change must decide whether to register it with a
complete `release_evidence` block or leave it unadopted. Other
pre-existing audit errors on `campusMesh`, `rust-platform-libs`,
`vowra`, `crossalheart`, `dharmatlas`, `hookit`, and
`lileililiwen-site` are unchanged by this change.

## Next action

1. Pick up `forge-governance-adapter` (the next active OpenSpec change
   with 0/16 tasks). Its proposal adds a small read-only shim that
   translates audit results into Forge's governance-provider contract.
2. Re-promote each pilot project at its current `HEAD` to clear the
   per-project `DEPLOYMENT_PROMOTION_STALE` warnings (optional; the
   warnings are triage, not blocking).
3. Replace the pilot-context `release_evidence` placeholder files with
   real release artefacts as each project's release pipeline produces
   them.
4. Decide whether to register `mewo` with a complete `release_evidence`
   block or leave it unadopted; the revert in the mewo repository
   removes the hand-claim but the project remains
   `DISCOVERED_UNREGISTERED` until the registry is updated.

## Evidence boundary

This repository can prove registry/schema/checker behavior, capability
declaration shape, release-evidence shape, the deployable+release-evidence
gate, the product-code quality rule, and the deployment promotion
mechanism. It cannot prove that the seven promoted projects actually
build, pass tests, deploy, or are runtime-healthy; those claims require
the promoted projects' own verification commands and jenkins-local
runtime observation.

## OpenSpec workflow

Select one active change with `openspec list`, run the local checker and
project gate before archive, validate strictly, archive canonical specs, then
create the required two commits. Each completed OpenSpec spec/change requires
exactly two commits: first the implementation/tests/archive commit, then a
HANDOFF.md-only pointer/evidence commit.
