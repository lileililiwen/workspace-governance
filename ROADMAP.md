# Workspace Governance Roadmap

> **Status (as of 2026-10-01):** Phases 1–4 are shipped. Packages 1
> (`registry-and-declaration-integrity`), 2 (`shared-rules-single-source`),
> 3 (`portfolio-vocabulary-normalization`), 8 (`governance-front-door`),
> 9 (`post-mvp-readiness`), 10 (`toolchain-decision-register`),
> 11 (`shared-postgres-runtime-profile`), and 12
> (`standalone-project-boundary`) are all archived in
> `openspec/changes/archive/` and indexed in `docs/package-backlog.md`.
> Packages 4–7 are specified implementation-ready in their owning
> repositories (`driftwatchdog`, `dotnet-platform-libs`,
> `rust-platform-libs`, and `platform-contracts` respectively).
> Remaining follow-ups: re-promote the pilot projects at their current
> `HEAD`, replace the pilot-context `release_evidence` placeholders, and
> replace the 9 scaffold `HANDOFF.md` bodies.

## Phase 1 — Registry and mandatory checks

- Register the existing project portfolio.
- Define project metadata and governance profiles.
- Validate required documents, OpenSpec names, CI, gate ownership, and deployment declarations.
- Generate a Jenkins-safe deployment manifest.

## Phase 2 — Adoption

- Add `.project.json` to every active product and shared project.
- Add the shared `driftwatchdog` gate declaration to each adopted project.
- Add repository-local `verify` commands and CI parity.
- Classify learning, scratch, archived, and deployment-only directories with lighter profiles.
- Add the `quality` block (see `docs/product-code-quality.md`) and bind the
  product-code quality checker in each adopted product's `.ai-gate/gate.yaml`.
  Missing migration metadata stays `REVIEW_REQUIRED`.

## Phase 3 — Control-plane integration

- Make `forge` consume `projects.json` and checker reports.
- Import OpenSpec status and `HANDOFF.md` pointers.
- Track maturity and evidence without claiming runtime completion from planning artifacts.
- Adopt the `capabilities` and `release_evidence` blocks (see
  `docs/capabilities.md`) so Forge observations can carry the same vocabulary
  as the workspace audit.
- Ship the `forge-governance-adapter` shim (see
  `openspec/specs/forge-governance-adapter/spec.md`) so a Forge control-plane
  can translate the per-project audit into a v0.1.0 governance observation
  without this repository gaining any UI or export surface of its own.

## Phase 4 — Deployment coordination

- Make `jenkins-local` consume `deployment/projects.json`.
- Require governance PASS before project job generation or deployment.
- Add per-project rollback and release evidence links.
- Record every `deployable: true` declaration in `deployment/promotions.json`
  via `scripts/promote_project.py`; the audit refuses hand-edited flags
  (`DEPLOYMENT_PROMOTION`) and surfaces stale revisions as a triage warning
  (`DEPLOYMENT_PROMOTION_STALE`).

## Proposed lower-priority runtime-template follow-up

> **Status (2026-10-01):** The follow-up is shipped as
> package 11 (`shared-postgres-runtime-profile`); see
> `openspec/changes/archive/2026-10-01-shared-postgres-runtime-profile/`
> and the canonical spec at
> `openspec/specs/external-postgres-runtime-profile/spec.md`. The four
> `*-postgres-external` families (`dotnet-web-postgres-external`,
> `rust-web-postgres-external`, `python-web-postgres-external`,
> `worker-postgres-external`) connect an app container to a
> supplied PostgreSQL service without starting a database container,
> image, volume, or provisioning command. The six per-project
> container-backed templates remain the default and are byte-identical
> to their pre-change bytes. Each project must still use its own
> database and role; endpoint and credentials are environment-specific
> and no Mac hostname is a product default.

## Proposed follow-up: wire the rules drift report into a gate

> **Status (2026-10-03):** Proposed, not started. Tracked as decision `D5` in
> `decisions.json` and as the change `rules-drift-gate-wiring`.
>
> `scripts/rules_drift.py` is currently a triage report that no gate calls.
> `scripts/workspace_check.py` imports only `scaffold_handoff` from it; the
> clause-level `drift()` report is invoked by neither `workspace_check.py`,
> `auto_gate.py`, nor CI. The `work-on-main rule` clause added by
> `openspec/changes/work-on-main-baseline-rule/` is therefore **reported, not
> enforced** — under ruling D18, a verifier that no gate runs does not gate.
>
> The proposed change calls `rules_drift.check()` from `workspace_check.run`
> and blocks through the existing `auto_gate.py --fail-on-warnings` path. It is
> deliberately not folded into `work-on-main-baseline-rule`, because it turns a
> 148-finding triage report into a fleet-wide gate in a single step, and that
> deserves its own change with its own baseline.

## Explicit non-goals

- No universal application framework.
- No central product database.
- No credential storage.
- No replacement for Jenkins, DriftWatchdog, Sisyphusfy, Ariadex, or language-specific toolchains.
- No automatic deployment merely because a project is registered.
