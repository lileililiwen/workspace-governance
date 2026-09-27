# Workspace Governance Handoff

current_spec: none

## Current state

Three changes shipped in sequence.

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

**3. `portfolio-vocabulary-normalization`** (archived
`openspec/changes/archive/2026-09-27-portfolio-vocabulary-normalization/`,
canonical spec `openspec/specs/portfolio-vocabulary/spec.md`). Added
`vocabulary.json` as the single machine-readable source for the 15 canonical
profiles, 12 canonical kinds, placeholder markers, and secret-field
substrings. `workspace_check.py` enforces `PROFILE_UNKNOWN` (ERROR),
`KIND_UNKNOWN` (WARNING), and `PROFILE_DOC_UNKNOWN` (ERROR) from it and exits
2 with `VOCABULARY` when it is missing or unusable; `product_code_quality.py`
defaults its markers from it while keeping per-project overrides;
`maturity_audit.py` reports the vocabulary version. Added the 9 missing
`profiles/*.json` documents and remapped 19 sibling declarations with
non-canonical `kind`/`profile` values (left uncommitted in their own
repositories, alongside the earlier declaration/rules edits).

The read-only **Forge governance adapter**
(`scripts/forge_governance_adapter.py`) is unchanged; its canonical spec is
`openspec/specs/forge-governance-adapter/spec.md`.

## Authored, not yet implemented

Five packages are fully authored as OpenSpec changes and are ready to implement
in a fresh conversation. Each lives in the repository that owns the work:

- `openspec/changes/governance-front-door/` (package 8, here).
- `driftwatchdog/openspec/changes/gate-evidence-export/` (package 4).
- `dotnet-platform-libs/openspec/changes/platform-consumer-bootstrap/` (package 5).
- `rust-platform-libs/openspec/changes/rust-platform-consumer-baseline/` (package 6).
- `platform-contracts/openspec/changes/contracts-consumer-parity/` (package 7).

`docs/package-backlog.md` is the index and the coordination rules; the detail
lives in each change directory, so a package has exactly one source of truth.

## Evidence

- `python3 -m unittest discover -s tests` — 140 tests, 0 failures (122 prior + 18 new in `tests/test_vocabulary.py`).
- `python3 scripts/workspace_check.py --self-check` — 0 errors, 0 warnings.
- `python3 scripts/workspace_check.py --root .. --audit --json` — **0 errors**,
  16 warnings (9 `HANDOFF_SCAFFOLD`, 7 `DEPLOYMENT_PROMOTION_STALE`), down from
  18 warnings before this change (two products recorded real `HANDOFF.md`
  bodies since 2026-09-26 through product-owned work; no `KIND_UNKNOWN`,
  `PROFILE_UNKNOWN`, or `PROFILE_DOC_UNKNOWN` remains).
- `python3 scripts/maturity_audit.py --root .. --json` — reports the same
  0 errors / 16 warnings as the audit; `vocabulary_version` is 1.
- `python3 scripts/product_code_quality.py . --json` — PASS for the governance
  repo (markers now default from the vocabulary).
- `python3 scripts/jenkins_manifest.py --check --root /home/paul/code` —
  7 projects, 0 errors.
- `python3 scripts/auto_gate.py --self-check --no-deployment` — PASS.
- Forge adapter observations verified for a clean project (`mewo`, pass), a
  remapped project (`forge`, pass), a warning-carrying project (`mortalect`,
  pass with `HANDOFF_SCAFFOLD` evidence), an unregistered id (`ghost`,
  unknown), and a pending-adoption project (`crossalheart`, blocked).
- `node scripts/check-openspec-change-names.mjs` — valid;
  `openspec validate --all --strict --no-interactive` — 9 passed, 0 failed
  (7 canonical specs, 2 active changes).
- `git diff --check` — clean.
- Commit `e74901e` was the pre-work HEAD; package 3 implementation is the
  first commit after it, followed by this HANDOFF-only commit.

## Portfolio impact observed

The `.ai-rules` baseline change is deliberately non-destructive. A first
implementation made whole canonical paragraphs mandatory and shipped `--apply`;
running it appended a duplicate canonical block to **60 project files**,
including well-maintained ones such as `mewo` whose text already expressed the
same rules. That was measured, judged a regression, and reverted byte-for-byte
before the change was re-scoped to a report-only clause check. The portfolio
`git diff` for `.ai-rules` is clean apart from `crossalheart`'s newly created
files.

9 adopted projects still carry scaffold `HANDOFF.md` bodies (reported as
`HANDOFF_SCAFFOLD`; two products recorded real handoffs since 2026-09-26).
The 7 `DEPLOYMENT_PROMOTION_STALE` warnings remain triaged:
re-promotion was not performed because it would record a deployable decision at
the current revision without a new release.

Sibling repositories still hold uncommitted declaration, rules, and vocabulary
remap files created by these three changes (the 10 declarations plus
`crossalheart`'s rules and `.ai-gate`, plus 19 `kind`/`profile` remaps);
they were left uncommitted in their own repositories.

## Next action

1. Implement package 8 (`governance-front-door`) from its authored
   change, then archive it with the two required commits.
2. Take packages 4–7 to their owning repositories via `docs/package-backlog.md`;
   each is a separate conversation and a separate repository.
3. Replace the 9 scaffold `HANDOFF.md` bodies as each product's own state is
   recorded (product-owned work).
4. Re-promote each pilot project at its current `HEAD` once its release pipeline
   produces real artifacts, and replace the pilot-context `release_evidence`
   placeholders.
5. Commit the sibling declaration/rules edits in their own repositories when
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
