# Workspace Governance Roadmap

## Phase 1 — Registry and mandatory checks — current

- Register the existing project portfolio.
- Define project metadata and governance profiles.
- Validate required documents, OpenSpec names, CI, gate ownership, and deployment declarations.
- Generate a Jenkins-safe deployment manifest.

## Phase 2 — Adoption

- Add `.project.json` to every active product and shared project.
- Add the shared `driftwatchdog` gate declaration to each adopted project.
- Add repository-local `verify` commands and CI parity.
- Classify learning, scratch, archived, and deployment-only directories with lighter profiles.

## Phase 3 — Control-plane integration

- Make `forge` consume `projects.json` and checker reports.
- Import OpenSpec status and `HANDOFF.md` pointers.
- Track maturity and evidence without claiming runtime completion from planning artifacts.

## Phase 4 — Deployment coordination

- Make `jenkins-local` consume `deployment/projects.json`.
- Require governance PASS before project job generation or deployment.
- Add per-project rollback and release evidence links.

## Explicit non-goals

- No universal application framework.
- No central product database.
- No credential storage.
- No replacement for Jenkins, DriftWatchdog, Sisyphusfy, Ariadex, or language-specific toolchains.
- No automatic deployment merely because a project is registered.
