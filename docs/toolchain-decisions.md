# Toolchain Decision Register

This document is the human view of the four toolchain decisions resolved
on 2026-09-30. The machine-readable source of truth is `decisions.json` at
the governance root; this file restates each entry in prose so reviewers
do not have to read JSON. Both stay in sync because the loader enforces
the shape and `tests/test_decisions.py` asserts the D2 `policy_boundary`
text and the D3 ownership split.

| ID | Title                                       | Status     | Date       | Owner                  |
|----|---------------------------------------------|------------|------------|------------------------|
| D1 | Agent runtime of record                     | accepted   | 2026-09-30 | workspace-governance   |
| D2 | Self-hosted identity provider               | accepted   | 2026-09-30 | workspace-governance   |
| D3 | Capability registry home                    | accepted   | 2026-09-30 | workspace-governance   |
| D4 | Crate publication mode                      | accepted   | 2026-09-30 | workspace-governance   |

Inspect or script the register with:

```bash
python3 scripts/workspace_check.py --decisions
python3 scripts/workspace_check.py --decisions --json
```

## D1 — Agent runtime of record

Adopt a declared split between the two agent runtimes: **ariadex** owns
interactive long-running developer sessions, while **sisyphusfy** owns
headless per-task loops with independent verification. Each runtime is
registered in `projects.json` and ships its own profile; the split is a
workspace-level policy so the two runtimes are not interchangeable and
shared code is forbidden across them without an explicit supersede.

## D2 — Self-hosted identity provider

Adopt **Zitadel** as the self-hosted identity provider, run as a shared
workspace runtime on `jenkins-local`, and exposed to product repositories
as the single workspace SSO seam.

**Policy boundary.** The shared identity provider covers internal
workspace products only. The public GitHub Pages catalog
(`lileililiwen-site` and any sibling published as a static site) remains
**excluded** from shared login and must not consume workspace SSO, shared
analytics, or any cross-product identity data. This exclusion restates the
root `HANDOFF.md` ownership table and is the binding interpretation of
this decision.

**Downstream references.** One registered OpenSpec change is named so far:
`dotnet-platform-libs` is the home of the `identity-oidc-client` change
that proves the OIDC client seam in a C# product. The runtime profile and
per-product OIDC client changes are still planned in B3 of the
`TOOLCHAIN_ROADMAP.md` and will be added to the register when each is
authored.

## D3 — Capability registry home

Split the capability registry between two owners. **`platform-contracts`**
owns the entry schema (the shape of a capability declaration).
**`workspace-governance`** owns the registered instances (the live records
of which projects declare which capabilities, kept next to `projects.json`).

**Policy boundary.** Capability entry schemas are owned by
`platform-contracts`; registered capability instances are owned by
`workspace-governance`. Consumers must read the schema from
`platform-contracts` and the instances from this repository; the two are
never merged into a single file.

**Downstream references.** `platform-contracts: capability-registry-v1`
is the schema change that backs this decision. It is still planned in B4
of `TOOLCHAIN_ROADMAP.md` and is recorded here so the audit can flag a
silently rewritten ownership split.

## D4 — Crate publication mode

Publish the `rust-platform-libs` crates to **crates.io** instead of
vendoring them as path dependencies. The repository is Apache-2.0, so the
legal preconditions for public publication are satisfied; consumer
adoption migrates off path dependencies only after the new
`registry-publication` change lands.

**Downstream references.** `rust-platform-libs: registry-publication` is
the prerequisite change that records the version policy, CI publishing
secret, `publish = false` flip, and name-squat check.

## Register rules

1. The register is owned by `workspace-governance` and lives at
   `decisions.json` at the governance root.
2. `workspace_check.py --self-check` fails closed if the file is missing
   (`DECISIONS_REGISTER_MISSING`).
3. Ids are permanent. Changing an accepted decision requires a NEW entry
   whose predecessor is marked `superseded`; the old text stays in place
   so the historical record is intact.
4. `status` is one of `proposed`, `accepted`, `rejected`, `superseded`.
5. `owner_project` and every `downstream[].repo` MUST be a registered
   `projects.json` id; `downstream[].change` MUST be kebab-case.
6. The D2 `policy_boundary` field is machine-checkable: a test asserts
   that the public-catalog exclusion is present. Editing the decision
   without keeping the exclusion will fail the test.
7. No code in this repository edits the register outside a code review;
   history integrity is git review plus the immutability rule, not
   runtime enforcement.
