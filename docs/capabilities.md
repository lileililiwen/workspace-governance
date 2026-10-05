# Platform Capability and Release Evidence Vocabulary

This document is the canonical reference for the two optional blocks that a
project may add to its `.project.json` declaration:

- `capabilities` — what reusable capabilities the project intends to consume
  or provide, with native evidence pointers.
- `release_evidence` — the producer-neutral record that backs a deployment.

Workspace Governance owns the **vocabulary and policy**. Platform repositories
own the **implementations**. Products retain the **native build, test, and
release commands**. The audit only reports declared intent and the presence or
absence of native evidence; it never promotes a capability or release field to
`verified` on its own.

## Capability states

A capability declaration has the shape:

```json
"capabilities": {
  "<name>": {
    "owner": "platform | product | shared | external | <project-id>",
    "evidence_state": "declared | configured | verified | unverified | blocked",
    "evidence_ref": "relative/path/within/project",
    "consumes": [
      {
        "provider": "<registered-project-id>",
        "package": "Platform.Idempotency",
        "version": "0.1.0",
        "evidence_ref": "relative/path/within/project",
        "local_implementation": "src/Infrastructure/IdempotencyGuard.cs"
      }
    ]
  }
}
```

`consumes` is optional and additive. A declaration without it remains valid and
emits no adoption finding. `provider`, `package`, and `evidence_ref` are
required per entry; `version` and `local_implementation` are optional. An
absolute or `..`-bearing `evidence_ref` is refused and never normalized into a
portable form.

| State        | Meaning                                                                                       | Audit behaviour                                                          |
|--------------|------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------|
| `declared`   | Project intends to provide the capability.                                                    | No finding.                                                              |
| `configured` | Local artefacts exist; native evidence path is recorded.                                      | WARNING if `evidence_ref` is missing or its file is absent.              |
| `verified`   | Native evidence has been recorded.                                                            | ERROR if `evidence_ref` is missing or its file is absent (stale).        |
| `unverified` | Native evidence is required but not yet available.                                            | WARNING (`CAPABILITY_PENDING`).                                          |
| `blocked`    | The capability is intentionally not provided. Record the non-goal in the project handbook.    | WARNING (`CAPABILITY_BLOCKED`).                                          |

The standard capability names are `identity`, `admin`, `tenancy`, `billing`,
`jobs`, `storage`, and `release`, plus the **cross-cutting shared
capabilities** `telemetry`, `rate-limiting`, `idempotency`, and
`feature-flags`. A cross-cutting shared capability applies to a provider, a
product, a library, and a tool alike, and its id is bound by the capability
registry; every profile that declares a `supported_capabilities` list includes
these four so a consumer can record a lawful `consumes[]` adoption without a
spurious warning. The registry's role-shaped ids (`persistence-postgres`,
`health-checks`, `web-application-factory`, `postgres-test-fixture`) are
admitted to a profile on demand, when a consumer of that role records an
adoption. Projects may declare additional capability names following the same
`^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$` pattern. Declaring a capability outside the
project profile's `supported_capabilities` list is surfaced as
`CAPABILITY_UNSUPPORTED` (WARNING) so profile owners can keep the supported set
intentional.

## Release evidence fields

A release evidence record has the shape:

```json
"release_evidence": {
  "<field>": {
    "state": "declared | configured | verified | unverified",
    "value": "field-specific (string, list, or omitted)",
    "evidence_ref": "relative/path/within/project"
  }
}
```

| Field         | What it records                                                    | Required for deployment? |
|---------------|--------------------------------------------------------------------|--------------------------|
| `revision`    | Source revision (commit SHA, tag, or pointer).                     | Yes                      |
| `version`     | Semantic version of the release.                                  | No                       |
| `toolchain`   | Toolchain identity (e.g. `rust-1.75`, `python-3.11`).              | No                       |
| `artifacts`   | Build artifacts produced for the release.                         | Yes                      |
| `digests`     | Cryptographic digests of the artifacts.                            | Yes                      |
| `sbom`        | Software bill of materials reference.                              | No                       |
| `provenance`  | Build provenance / signature reference.                            | Yes                      |
| `checks`      | Verification commands or evidence the release was exercised with.  | Yes                      |
| `publication` | Where the artifacts were published (mirror, registry, etc.).        | Yes                      |

A `deployable: true` project must have each required field either in
`verified` state, or in `configured` state with a present `evidence_ref`.
Anything else raises `RELEASE_EVIDENCE_INSUFFICIENT` (ERROR) and blocks the
Jenkins manifest.

## Capability adoption is measured, not declared

`capabilities.json` at the governance root binds each capability id to exactly
one provider and assigns it a posture. The audit joins **three** sources and
all three must agree before a capability counts as adopted:

1. the **registry** entry names exactly one provider and a posture;
2. the consumer's **own manifests** carry a pinned coordinate for the package;
3. the consumer's **declaration** records the pairing in `consumes[]`.

| Side present | Result | Finding |
|---|---|---|
| registry + manifest + `consumes[]` | adopted | none |
| registry + manifest, no `consumes[]` | adopted, undocumented | `CAPABILITY_ADOPTION_UNEVIDENCED` (WARNING) |
| registry + `consumes[]`, no manifest edge | declared, not wired | `CAPABILITY_ADOPTION_MISSING` |
| registry only | not consumed | `CAPABILITY_ADOPTION_MISSING` |
| declared local implementation, no edge | duplicated | `CAPABILITY_ADOPTION_MISSING`, message names the local path |

The measurement is **read-only**. It executes no project command, invokes no
package manager, resolves no lockfile or transitive graph, and makes no network
request. It reads only the dependency stanza of `Directory.Packages.props`,
`*.csproj`, `package.json`, `Cargo.toml`, `pyproject.toml`, and
`requirements*.txt`, within a bounded walk that skips build and vendor trees.
A manifest that exists but cannot be parsed is reported as *unproven*, never as
proof of absence and never as a failure.

A repository cannot mark itself compliant: `consumes[]` is a declaration, and
the manifest is the only trusted side. A hand-written consumption record with no
resolvable manifest edge is exactly the failure the gate exists to catch.

### Postures and the WARN → FAIL ramp

| Posture | Level of an adoption finding | Meaning |
|---|---|---|
| `exempt` | none | Requires a recorded `reason`. The pressure valve. |
| `expected` | WARNING | A new capability always starts here. |
| `required` | ERROR (fails `auto_gate.py`) | Requires a recorded graduation. |

Promotion to `required` needs **all three** of: a provider whose capability is
`verified` with a resolving `evidence_ref`; a recorded `audit_count` reaching
`graduation_audits` (default 3); and a matching entry appended to the
`graduations` list. **Elapsed wall-clock time is never a substitute** — an
audit that has not run is not evidence that a repository refused to adopt. A
capability whose posture says `required` without a valid graduation entry is
silently demoted back to `expected`, so lowering a counter or editing a date
cannot manufacture a fleet error.

The registry this repository currently ships records every measured capability
as `exempt` with reason `provider-unavailable`: no provider in the fleet
declares a `verified` capability yet, so charging consumers for a provider gap
would be noise. Moving one capability to `expected` is the single edit that
starts the ramp for it.

### Declining a capability

Legitimate non-adoption is a first-class, reviewable answer rather than
silence. A decline is the only exit the gate accepts besides adoption:

```json
"declines": [
  {
    "capability": "idempotency",
    "rationale": "dependency-direction",
    "evidence_ref": "docs/shared-ownership.md",
    "review_by": "2026-12-01"
  }
]
```

`evidence_ref` is **required** and must resolve inside the project root: an
assertion is not a boundary argument, which is the same failure mode as a
hand-declared adoption. `review_by` is advisory and never auto-expires a
decline — a stale decline is a governance conversation, not a machine decision.

The rationale vocabulary is closed:

| Rationale | Boundary |
|---|---|
| `ownership` | The provider's owner will not accept the responsibility. |
| `privacy` | Adoption would move data across a declared boundary. |
| `lifecycle` | The two projects ship and deprecate on incompatible schedules. |
| `dependency-direction` | Adopting would invert the dependency direction. |
| `naming-symmetry` | Extraction is motivated by symmetry, not by a consumer boundary. |
| `not-applicable` | The capability does not apply to this repository's role. |
| `provider-unavailable` | No published, verified provider exists. |

A decline is **repo-local and capability-scoped**. It never suppresses a finding
for any other capability, and never suppresses a finding in any other
repository. That containment is deliberate: a fleet-wide "this is a platform
problem" exemption is how cross-cutting disagreement becomes invisible.

### Adoption findings

| Code | Level | Meaning |
|---|---|---|
| `CAPABILITY_ADOPTION_MISSING` | WARNING (`expected`) / ERROR (`required`) | No consumption edge for a registered capability. Names the provider, the package, and any declared local implementation. |
| `CAPABILITY_ADOPTION_UNEVIDENCED` | WARNING | The manifest proves consumption but `consumes[]` is missing, has no `evidence_ref`, or a manifest could not be read. The edge is real; the record is not. |
| `CAPABILITY_ADOPTION_EVIDENCE_STALE` | WARNING | A `consumes[].evidence_ref` is absolute, escapes the project root, or no longer resolves. |
| `CAPABILITY_ADOPTION_DECLINE_UNRECORDED` | WARNING | A project's own documentation states a non-adoption boundary but no `declines[]` record exists. Names the document. |
| `CAPABILITY_ADOPTION_UNRESOLVED` | WARNING (review-required) | The capability id does not bind to exactly one provider. Never escalates to an error, and is never attributed to the project under audit. |
| `CAPABILITY_REGISTRY_INVALID` | ERROR (governance) | `capabilities.json` is missing, unparseable, or empty. There is no empty-registry fallback. |

`CAPABILITY_ADOPTION_UNRESOLVED` is the deliberate fail-*soft* branch. Three
incompatible definitions of "capability" exist in this workspace today, and
this check does not merge them. A finding that cannot be attributed to one
provider is not the consumer's fault to fix, so it is reported for review and
never escalated. The audit still **never promotes a capability to `verified`
on its own** — a measured adoption is a declared intent to restore an artifact,
not a proof that the restore succeeded.

## Ownership

| Surface                      | Owner                                                                       |
|------------------------------|-----------------------------------------------------------------------------|
| Vocabulary and policy        | Workspace Governance (this repository).                                     |
| Capability implementation    | Platform repositories (`dotnet-platform-libs`, `labrys`, `alltools-platform`). |
| Capability adoption          | Each product repository via `.project.json` capabilities block.            |
| Capability registry (instances) | Workspace Governance — `capabilities.json`, next to `projects.json`.    |
| Release evidence generation  | The product or platform that produces the artifacts.                        |
| Deployment promotion         | `jenkins-local` consuming `deployment/projects.json`.                        |

## Capability registry ownership split (D3)

The capability registry is split between two owners, recorded as
`D3` in `docs/toolchain-decisions.md`:

- **Entry schema.** `platform-contracts` owns the shape of a capability
  declaration — the family of names, the `owner`/`evidence_state`/
  `evidence_ref` fields, and any future additive fields. Consumers that
  validate a capability declaration read the schema from
  `platform-contracts`.
- **Registered instances.** This repository (`workspace-governance`)
  owns the live records of which projects declare which capabilities,
  stored next to `projects.json`. The audit cross-references every
  declared capability against the profile's `supported_capabilities`
  list, but it does not own the schema.

The two are never merged into a single file. The `D3` entry in
`decisions.json` is the machine-checkable binding; `tests/test_decisions.py`
asserts the split is present.

## Non-goals

- No automatic dependency injection or package installation.
- No deployment promotion from metadata alone.
- No replacement for Driftwatchdog, Jenkins, Forge, or native toolchains.
- The audit does not, and will not, promote a capability or release field to
  `verified` based on planning artifacts.
- Measuring non-adoption is not permission to fix it. Repointing a consumer
  onto a provider is a separate, bounded authorization — see
  `docs/adoption-grant.md`.
