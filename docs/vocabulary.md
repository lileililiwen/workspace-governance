# Registry and Evidence Vocabulary

One entry point for the registry/evidence terms used across this
repository. Each definition links its canonical source rather than
restating policy; the sources own the wording.

**Invariant: a declaration is intent, not evidence.** Registry
presence and a `.project.json` declaration record what a project
claims. Build, test, integration, provider, runtime, and release
health are proven only by the project's own verification command
and runtime observation. Nothing in this repository promotes a
project to deployable on metadata alone.

| Term | Meaning | Canonical source |
|---|---|---|
| Declaration (`.project.json`) | Intent: what a project claims (identity, verification command, deployment flags, capabilities, evidence blocks). | `schemas/project.schema.json`, `openspec/specs/registry-integrity/spec.md` |
| `evidence_status` | Verification state of the declaration: `declared`, `configured`, `verified`, `unverified` (plus the `planned` value still found in un-remediated siblings). | `docs/capabilities.md` |
| `capabilities` | Declared reusable platform capabilities (`identity`, `admin`, `tenancy`, `billing`, `jobs`, `storage`, `release`, and project-defined names) with an owner and an evidence state. | `docs/capabilities.md` |
| `release_evidence` | Producer-neutral record (revision, version, toolchain, artifacts, digests, SBOM, provenance, checks, publication) backing a deployment. | `docs/capabilities.md` |
| `deployable: true` | Requires **both** a matching promotion-ledger entry **and** a complete `release_evidence` block; neither alone suffices. | `openspec/specs/deployable-batch-onboarding/spec.md`, `docs/deployment-promotion.md` |
| Promotion ledger | Tamper-evident record of promotion decisions in `deployment/promotions.json` (with `deployment/promotions.sha256` sidecar). | `docs/deployment-promotion.md` |
| Finding code | A stable audit result name with a level (`ERROR`/`WARNING`), e.g. `DECLARATION_ID`, `KIND_UNKNOWN`, `HANDOFF_SCAFFOLD`, `DEPLOYMENT_PROMOTION_STALE`. | `openspec/specs/registry-integrity/spec.md` |
| `kind` / `profile` | Descriptive project classification drawn from the canonical sets (12 kinds, 15 profiles). | `vocabulary.json`, `openspec/specs/portfolio-vocabulary/spec.md` |
| Quality gate (`quality` block) | Opt-in product-code rule (test code in product scope, placeholder debt); fail-closed, never a guessed pass. | `docs/product-code-quality.md`, `openspec/specs/product-code-quality-boundary/spec.md` |
| Governance front door | The single auto-triggering skill entry routing each governance situation to its per-concern reference. | `skills/workspace-governance/SKILL.md`, `openspec/specs/governance-front-door/spec.md` |
| Forge adapter observation | Read-only translation of this repository's audit findings for Forge's governance-provider contract; not runtime or release evidence. The v0.1.0 contract now also carries additive `standalone_status`, `standalone_observed_revision`, `standalone_integrations`, and `standalone_findings` fields. | `openspec/specs/forge-governance-adapter/spec.md`, `openspec/specs/standalone-project-boundary/spec.md` |
| Standalone classification (`standalone` / `integrations`) | Optional `standalone` block and `integrations` array in `.project.json` record how a project operates without sibling checkouts or private services. The audit classifies the project as one of six canonical statuses (`standalone`, `standalone-with-optional-integrations`, `library-dependent`, `workspace-dependent`, `service-dependent`, `blocked`) without executing project commands. Declarations are intent, not evidence; an absent block reports `blocked` + `STANDALONE_BLOCKED` warning, never a pass. | `openspec/specs/standalone-project-boundary/spec.md` |
