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
    "evidence_ref": "relative/path/within/project"
  }
}
```

| State        | Meaning                                                                                       | Audit behaviour                                                          |
|--------------|------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------|
| `declared`   | Project intends to provide the capability.                                                    | No finding.                                                              |
| `configured` | Local artefacts exist; native evidence path is recorded.                                      | WARNING if `evidence_ref` is missing or its file is absent.              |
| `verified`   | Native evidence has been recorded.                                                            | ERROR if `evidence_ref` is missing or its file is absent (stale).        |
| `unverified` | Native evidence is required but not yet available.                                            | WARNING (`CAPABILITY_PENDING`).                                          |
| `blocked`    | The capability is intentionally not provided. Record the non-goal in the project handbook.    | WARNING (`CAPABILITY_BLOCKED`).                                          |

The standard capability names are `identity`, `admin`, `tenancy`, `billing`,
`jobs`, `storage`, and `release`. Projects may declare additional capability
names following the same `^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$` pattern. Declaring
a capability outside the project profile's `supported_capabilities` list is
surfaced as `CAPABILITY_UNSUPPORTED` (WARNING) so profile owners can keep the
supported set intentional.

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

## Ownership

| Surface                      | Owner                                                                       |
|------------------------------|-----------------------------------------------------------------------------|
| Vocabulary and policy        | Workspace Governance (this repository).                                     |
| Capability implementation    | Platform repositories (`dotnet-platform-libs`, `labrys`, `alltools-platform`). |
| Capability adoption          | Each product repository via `.project.json` capabilities block.            |
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
