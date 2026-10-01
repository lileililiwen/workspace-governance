# Workspace Governance Roadmap

> **Status (as of 2026-09-26):** Phases 1–4 are shipped and the workspace audit
> is at 0 errors. Packages 1 (`registry-and-declaration-integrity`), 2
> (`shared-rules-single-source`) and 3 (`portfolio-vocabulary-normalization`)
> are archived. Package 8 (`governance-front-door`)
> is archived as well. Packages 4–7 are specified
> implementation-ready in `docs/package-backlog.md` and are owned by
> `driftwatchdog`, `dotnet-platform-libs`, `rust-platform-libs` and
> `platform-contracts` respectively. Remaining follow-ups: re-promote the pilot
> projects at their current `HEAD`, replace the pilot-context `release_evidence`
> placeholders, and replace the 11 scaffold `HANDOFF.md` bodies.

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

After the active `standalone-project-boundary` work, consider
`shared-postgres-runtime-profile`: optional .NET/Rust/Python runtime templates
that connect to an operator-supplied PostgreSQL service without creating a
per-project database container. The current per-project database templates
remain the default. Each project must use its own database and role; endpoint
and credentials are environment-specific, and no Mac hostname is a product
default.

## Explicit non-goals

- No universal application framework.
- No central product database.
- No credential storage.
- No replacement for Jenkins, DriftWatchdog, Sisyphusfy, Ariadex, or language-specific toolchains.
- No automatic deployment merely because a project is registered.
