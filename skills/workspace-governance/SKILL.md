---
name: workspace-governance
description: Entry point for workspace governance situations in this portfolio: project declarations and registry, kind/profile vocabulary, quality gates and release evidence, the shared rules baseline, platform adoption, and shared contracts. Routes each situation to the owning script or canonical spec.
---

# Workspace Governance

One front door, not a new authority. When the task touches the workspace
registry, a project declaration, a gate, evidence, shared rules, platform
adoption, or shared contracts, start here, follow the routing table to the
named reference, and run the reference's commands. Never invent a mechanism
beside an existing one.

## Routing table

| Situation | Route |
|---|---|
| Is the workspace healthy / why is the audit red | `skills/workspace-governance/references/declaration.md`, then `python3 scripts/workspace_check.py --root .. --audit` |
| Add or fix a project declaration | `skills/workspace-governance/references/declaration.md` (`scripts/init_project.py`, `schemas/project.schema.json`) |
| Gate, evidence, or release readiness | `skills/workspace-governance/references/gate-and-evidence.md` (driftwatchdog, `docs/capabilities.md`, `scripts/promote_project.py`) |
| Kind, profile, marker, or secret vocabulary | `skills/workspace-governance/references/vocabulary.md` (`vocabulary.json`) |
| Shared rules, `.ai-rules`, or handoff shape | `skills/workspace-governance/references/rules-baseline.md` (`scripts/rules_drift.py`, `openspec/specs/rules-baseline/spec.md`) |
| Shared library adoption (.NET / Rust) | `skills/workspace-governance/references/platform-adoption.md` (dotnet-platform-libs, rust-platform-libs) |
| Shared contracts or schemas | `skills/workspace-governance/references/contracts.md` (platform-contracts) |
| Unknown or ambiguous | Safe default: `python3 scripts/workspace_check.py --root .. --audit`, then `openspec list`. Say that no route matched; never guess. |

## Boundaries

- Read first: `python3 scripts/workspace_check.py --self-check` passes on a
  healthy checkout. The audit is authoritative; `scripts/maturity_audit.py`
  only reports its counts.
- Destructive and shared-state actions — pushing, deploying, promoting, or
  re-promoting — stay behind the existing explicit-approval boundary. This
  skill never instructs them; the references link the owning scripts and docs
  so an approved operator can run them.
- References link canonical scripts and specs; they never restate policy.
  `python3 scripts/check_skill_refs.py` proves every cited path exists.

## Install

This skill is versioned with the scripts it cites and is not installed
automatically. See `README.md` for the documented symlink-or-copy install
into the agent skills directory.
