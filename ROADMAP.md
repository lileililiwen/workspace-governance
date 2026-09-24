# Workspace Governance Roadmap

> **Status (as of 2026-09-24):** Phases 1–4 are all shipped. The current
> open items are the post-promotion follow-ups (re-promote pilots at
> their current `HEAD`, replace pilot-context `release_evidence`
> placeholders, decide the registry status of `mewo`) and the authoring
> of the next OpenSpec change. The HANDOFF.md `current_spec` line is
> `none` until the next change is proposed.

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

## Explicit non-goals

- No universal application framework.
- No central product database.
- No credential storage.
- No replacement for Jenkins, DriftWatchdog, Sisyphusfy, Ariadex, or language-specific toolchains.
- No automatic deployment merely because a project is registered.
