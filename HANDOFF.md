# Workspace Governance Handoff

current_spec: none

## Current state

The governance repository now ships a read-only **Forge governance
adapter** at `scripts/forge_governance_adapter.py`. The script reads
one AdapterRequest on stdin (`contract: "0.1.0"`, `action: "check"`,
`project_id`, `project_path`), runs the existing in-process audit for
the named project, and writes exactly one observation document to
stdout. Status mapping: any audit ERROR attributed to the project →
`fail`; adoption gap or `DISCOVERED_UNREGISTERED` → `blocked`; clean
adopted → `pass`; project unknown to the registry and not on disk →
`unknown` (still exit 0). The adapter never registers, adopts,
mutates, or writes to this repository, and redacts secret-shaped
substrings (the checker's `SECRET_WORDS` rule plus any
immediately-associated value) from every evidence line.

The change is archived in
`openspec/changes/archive/2026-09-24-forge-governance-adapter/` and the
canonical spec lives at
`openspec/specs/forge-governance-adapter/spec.md`. The README adds an
optional-consumers section with the exact `forge governance use
workspace-governance <root> --adapter ...` invocation. ROADMAP Phase 3
records the shipped adapter as part of the Forge control-plane
integration.

## Evidence

- `python3 -m unittest discover -s tests` — 97 tests, 0 failures
  (28 new adapter scenarios + 69 existing).
- `python3 scripts/workspace_check.py --self-check` — 0 errors,
  0 warnings.
- `python3 scripts/auto_gate.py --self-check --no-deployment` —
  PASS.
- `python3 scripts/jenkins_manifest.py --check --root /home/paul/code`
  — 7 projects, 0 errors.
- `node scripts/check-openspec-change-names.mjs` — valid.
- `openspec validate --all --strict --no-interactive` — 4 passed,
  0 failed (4 canonical specs, 0 active changes).
- `git diff --check` — clean; no secrets, host paths, or runtime
  credentials added.
- End-to-end smoke against `alethefy`, `workspace-governance`,
  `forge`, and `hermora` — four valid observations, each with the
  expected status; an unknown project returns `unknown` with exit 0;
  a malformed request returns exit 2 with a single-line stderr note.
  The governance tree hash is byte-identical before and after the
  smoke run.
- Commit `15b09f1` (the implementation + tests + archive commit)
  brings in the adapter script, the 28-scenario test module, the
  optional-consumers README section, the Phase 3 ROADMAP update, the
  archived OpenSpec change, and the canonical spec.

## Portfolio impact observed

No audit findings changed: the adapter is read-only, the new test
module exercises synthetic workspaces under a sandboxed governance
root, and `workspace_check.py --self-check` is unchanged. The
pre-existing `DEPLOYMENT_PROMOTION_STALE` warnings on the seven pilot
projects, the `DISCOVERED_UNREGISTERED` finding for `mewo`, and the
pre-existing audit errors on `campusMesh`, `rust-platform-libs`,
`vowra`, `crossalheart`, `dharmatlas`, `hookit`, and
`lileililiwen-site` are all unchanged by this change. Forge's
governance surface now has a real, fail-closed data source for those
findings.

## Next action

1. Re-promote each pilot project at its current `HEAD` to clear the
   per-project `DEPLOYMENT_PROMOTION_STALE` warnings (optional; the
   warnings are triage, not blocking).
2. Replace the pilot-context `release_evidence` placeholder files with
   real release artefacts as each project's release pipeline produces
   them.
3. Decide whether to register `mewo` with a complete `release_evidence`
   block or leave it unadopted; the revert in the mewo repository
   removes the hand-claim but the project remains
   `DISCOVERED_UNREGISTERED` until the registry is updated.
4. Identify the next governance change to author. The four
   `openspec/specs/*` directories are the existing capabilities of
   this repository (registry, capability manifest, release evidence,
   product-code quality, deployment promotion, Forge adapter). The
   next OpenSpec change should be proposed only after the open
   `next-action` items above are triaged.

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
