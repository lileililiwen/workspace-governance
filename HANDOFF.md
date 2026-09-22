# Workspace Governance Handoff

current_spec: workspace-governance-foundation

## Current state

The governance repository contains the portfolio registry, schemas, bootstrap templates, mandatory checker, and Jenkins deployment manifest generator.
The registry inventories existing directories, but most existing repositories are not yet adopted because they do not contain `.project.json`.

## Next action

Run the adoption queue in registry order. For each active project, execute `scripts/init_project.py`, review the generated declaration, add the real verification command, then run the project-local gate and the workspace checker.

## Evidence boundary

This repository can prove registry/schema/checker behavior. It cannot prove that every registered project builds, passes tests, deploys, or is runtime-healthy. Those claims require project-specific evidence.

## OpenSpec workflow

Select one active change with `openspec list`, run the local checker and project gate before archive, validate strictly, archive canonical specs, then create the required two commits. Each completed OpenSpec spec/change requires exactly two commits: first the implementation/tests/archive commit, then a HANDOFF.md-only pointer/evidence commit.
