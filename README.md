# Workspace Governance

Workspace Governance coordinates a portable workspace selected at invocation
time. It owns the project registry, governance profiles, bootstrap templates,
evidence vocabulary, and deployment declarations.

It does not own product source code, language runtimes, shared gate runtimes, or production execution.

## Ownership

- `forge` is the portfolio control-plane consumer.
- `driftwatchdog` is the shared quality and evidence gate runtime.
- `sisyphusfy` is the agent iteration runtime.
- `ariadex` is the supervised runtime operator.
- `dotnet-platform-libs` is the reusable .NET library platform.
- `jenkins-local` performs Jenkins/Mac deployment execution.

## Capability and release evidence

Projects may add two optional blocks to `.project.json`:

- `capabilities` — declares reusable platform capabilities (identity, admin,
  tenancy, billing, jobs, storage, release, and project-defined names) with
  an owner and an evidence state. Declarations are intent, not implementation
  evidence. See `docs/capabilities.md` for the canonical vocabulary.
- `release_evidence` — a producer-neutral record (revision, version,
  toolchain, artifacts, digests, SBOM, provenance, checks, publication) that
  backs a deployment. A `deployable: true` project must carry a complete
  `release_evidence` block; otherwise `workspace_check.py` fails the project
  closed with `RELEASE_EVIDENCE_INSUFFICIENT` and `jenkins_manifest.py` will
  not emit the entry.

Both blocks are additive. Existing declarations without them remain valid;
the audit only surfaces findings for projects that opt in. The new fields do
not, and never will, promote a project to deployable on their own.

## Mandatory command

Run from this repository. The registry never stores a machine-specific root;
pass a workspace root relative to the current checkout, or an absolute path
only at invocation time:

```bash
python3 scripts/workspace_check.py --self-check
python3 scripts/workspace_check.py --root .. --audit --json
python3 scripts/auto_gate.py --root .. --report auto-gate-report.json
python3 -m unittest discover -s tests -v
```

With `explicit-plus-immediate-directories`, immediate child folders containing
common project markers are discovered automatically. New folders are reported
as `DISCOVERED_UNREGISTERED`; they do not require a registry edit and are not
treated as adopted or deployable until their local metadata and evidence pass.

`auto_gate.py` is the unattended entry point. It fails on governance or
deployment errors, writes a machine-readable report when requested, and is
scheduled by the repository workflow. Jenkins should run the same command
before project verification or deployment; no manual audit request is needed.

## Onboard a project

```bash
python3 scripts/init_project.py /path/to/project \
  --id my-project --profile rust-product --kind product
python3 scripts/workspace_check.py --root .. --project my-project
```

The initializer is non-destructive and writes only missing governance declarations and rules.
It never copies gate runtimes, installers, credentials, or universal rule implementations into a product repository.

## Jenkins

`deployment/projects.json` is the safe handoff to `jenkins-local`. Generate it only after the governance check:

```bash
python3 scripts/jenkins_manifest.py --check
```

Jenkins still owns synchronization, secrets, Compose, database provisioning, job registration, and deployment.
The governance project only says which projects are eligible and which verification command must pass.

## Status boundary

Registry presence is not implementation evidence. The checker records declarations and policy status; project gates must provide build, test, integration, provider, runtime, and release evidence separately.
