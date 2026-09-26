# Workspace Governance Handoff

current_spec: none

## Current state

The `registry-and-declaration-integrity` change is archived at
`openspec/changes/archive/2026-09-26-registry-and-declaration-integrity/` and
its canonical spec lives at `openspec/specs/registry-integrity/spec.md`. It
registered the 11 discovered declarations, corrected six declaration
identity/format defects, created four missing declarations, added duplicate
id/path guards, derived and enforced the canonical project id in
`init_project.py`, and made `maturity_audit.py` report the authoritative
`workspace_check` counts. Unregistered discovery is now an ERROR because the
registry sets `discovery.unregistered_policy: "fail"`.

The previously shipped read-only **Forge governance adapter**
(`scripts/forge_governance_adapter.py`) is unchanged: it answers one `check`
request on stdin (`contract: "0.1.0"`), maps audit ERROR → `fail`, adoption gap
→ `blocked`, clean adopted → `pass`, absent project → `unknown`, and redacts
secret-shaped substrings from every evidence line. Its canonical spec is
`openspec/specs/forge-governance-adapter/spec.md`.

## Evidence

- `python3 -m unittest discover -s tests` — 112 tests, 0 failures (15 new
  across registry-integrity, init_project and maturity_audit modules).
- `python3 scripts/workspace_check.py --self-check` — 0 errors, 0 warnings.
- `python3 scripts/workspace_check.py --root .. --audit --json` — 2 errors /
  7 warnings, down from 14 / 18; zero findings for the change's six in-scope
  codes (`DECLARATION_MISSING`, `DECLARATION_ID`, `DECLARATION_SCHEMA`,
  `VERIFICATION_COMMAND`, `DISCOVERED_UNREGISTERED`,
  `DEPLOYMENT_PROMOTION_STALE`).
- `python3 scripts/maturity_audit.py --root .. --json` — reports the same
  2 errors / 7 warnings as the audit; `evidence_planned` is 0.
- `python3 scripts/jenkins_manifest.py --check --root /home/paul/code` —
  7 projects, 0 errors.
- `python3 scripts/auto_gate.py --self-check --no-deployment` — PASS.
- `node scripts/check-openspec-change-names.mjs` — valid;
  `openspec validate --all --strict --no-interactive` — 5 passed, 0 failed
  (5 canonical specs, 0 active changes).
- Forge adapter smoke — `pass` (`ziban`), `fail` (`crossalheart`'s remaining
  `REQUIRED_FILE`), `unknown` (absent project).
- `git diff --check` — clean; no secrets, host paths or runtime credentials
  added.
- Commit `039ae39` (the implementation + tests + archive commit) brings in the
  registry and declaration changes, the checker and initializer updates, the
  delegated maturity report, the 15 new tests, the README/ROADMAP/adoption-queue
  updates, the archived change, and the canonical spec.

## Portfolio impact observed

Ten sibling declarations changed as data: `campusMesh`, `careBridge`,
`citylens`, `retakeKit`, `trailCrew` and `vowra` were corrected, and
`dharmatlas`, `hookit`, `openTeacherKit` and `lileililiwen.github.io` gained a
declaration. Those files live in their own repositories and were left
uncommitted there, alongside those repositories' pre-existing pending work.

Two audit errors remain: the deferred `crossalheart` `REQUIRED_FILE`
(`.ai-rules/workflow.md`, `.ai-rules/completion.md`), owned by package
`shared-rules-single-source`. Seven `DEPLOYMENT_PROMOTION_STALE` warnings remain
as triage: re-promotion was deliberately not performed because it would record a
deployable decision at the current revision without a new release.

## Next action

1. Author and implement package `shared-rules-single-source`: make `.ai-rules/*`
   and stub `HANDOFF.md` derive from one canonical template set (73 files hold
   31 distinct contents today) and clear the `crossalheart` `REQUIRED_FILE`
   error. It depends on the now-shipped registry integrity work.
2. Then package `portfolio-vocabulary-normalization` (22 kinds / 17 profiles,
   and the duplicated placeholder/secret/capability vocabulary).
3. Then package `gate-run-evidence` (real driftwatchdog runs feeding
   `release_evidence`).
4. Re-promote each pilot project at its current `HEAD` once its release pipeline
   produces real artifacts, and replace the pilot-context `release_evidence`
   placeholders.
5. Commit the sibling declaration edits named in "Portfolio impact observed" in
   their own repositories when those repositories' pending work is ready.

## Evidence boundary

This repository can prove registry/schema/checker behavior, capability
declaration shape, release-evidence shape, the deployable+release-evidence
gate, the product-code quality rule, the deployment promotion
mechanism, and the Forge governance adapter contract. It cannot prove
that the seven promoted projects actually build, pass tests, deploy, or
are runtime-healthy; those claims require the promoted projects' own
verification commands and jenkins-local runtime observation. The
adapter likewise cannot prove a project's runtime or release health;
it only translates this repository's own audit findings.

## OpenSpec workflow

Select one active change with `openspec list`, run the local checker and
project gate before archive, validate strictly, archive canonical specs, then
create the required two commits. Each completed OpenSpec spec/change requires
exactly two commits: first the implementation/tests/archive commit, then a
HANDOFF.md-only pointer/evidence commit.
