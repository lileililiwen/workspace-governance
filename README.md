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

## Product-code quality gate

Projects may opt in to the product-code quality gate by adding a `quality`
block to `.project.json` and binding `python3 scripts/product_code_quality.py
<dir>` in their `.ai-gate/gate.yaml`. The gate detects two failure modes
the structural audit cannot: test code in product scope (including lexical
Rust `#[cfg(test)]` containment) and placeholder debt across product files
(TODO, FIXME, XXX, HACK, placeholder, stub, unimplemented!, todo!). The
checker is fail-closed: missing or invalid policy, unsupported language,
traversal in exclusions, or an unreadable product file is REVIEW_REQUIRED,
never a guessed pass. See `docs/product-code-quality.md` for the full
contract, JSON schema, and per-language rules.

## Registry and declaration integrity

`projects.json` is the single source of project identity, and the audit fails
closed on:

- a declaration whose `id` differs from its registry `id` (`DECLARATION_ID`);
- a declaration missing `schema_version: 1` or the required `verification` and
  `deployment` blocks (`DECLARATION_SCHEMA`);
- a real command supplied under a non-schema key (`VERIFICATION_COMMAND`);
- an adopted registry entry with no `.project.json` (`DECLARATION_MISSING`);
- a discovered declaration with no registry entry (`DISCOVERED_UNREGISTERED`);
- two registry entries sharing an `id` (`PROJECT_DUPLICATE`) or a `path`
  (`PROJECT_PATH_DUPLICATE`).

The canonical `id` is derived from the directory name (`hestiaLab` →
`hestia-lab`). `init_project.py` refuses an explicit `--id` that conflicts with
the derived id; a directory name that is not convertible (for example a dotted
host name) may use an explicitly recorded alias.

`scripts/maturity_audit.py` reports the error and warning counts produced by
`workspace_check.py`; it never computes a second, independent result, so the
two views cannot disagree.

## Mandatory command

Run from this repository. The registry never stores a machine-specific root;
pass a workspace root relative to the current checkout, or an absolute path
only at invocation time:

```bash
python3 scripts/workspace_check.py --self-check
python3 scripts/workspace_check.py --root .. --audit --json
python3 scripts/auto_gate.py --root .. --report auto-gate-report.json
python3 scripts/product_code_quality.py <project_dir> --json
python3 -m unittest discover -s tests -v
```

### Optional: Forge governance-provider adapter

This repository ships a read-only shim that exposes the per-project audit
through Forge's published v0.1.0 governance-provider contract. The
adapter is not a CI surface — it only answers a single `check` request
on stdin and prints one observation document on stdout:

```bash
echo '{"contract":"0.1.0","action":"check","project_id":"<id>","project_path":"<path>"}' \
  | WORKSPACE_ROOT=<workspace-root> \
    python3 scripts/forge_governance_adapter.py
```

The exit code is `0` for every answerable evaluation (including `fail`,
`blocked`, and `unknown`), `2` for a malformed request, and `3` for an
audit crash (which Forge classifies as `unavailable`). The adapter never
writes, registers, adopts, or mutates anything in this repository, and
redacts secret-shaped substrings from every evidence line. Point Forge
at the script with:

```text
forge governance use workspace-governance <workspace-root> \
  --adapter <repo>/scripts/forge_governance_adapter.py
```

See `openspec/specs/forge-governance-adapter/spec.md` for the contract
shape and `tests/test_forge_governance_adapter.py` for the mapping
matrix.

With `explicit-plus-immediate-directories`, immediate child folders containing
common project markers are discovered automatically. The registry's
`discovery.unregistered_policy` decides the level: this workspace sets `fail`,
so an unregistered declaration is `DISCOVERED_UNREGISTERED` **ERROR** and must
be registered (or explicitly classified) before the audit passes. A discovered
folder is never treated as adopted or deployable until its local metadata and
evidence pass.

`auto_gate.py` is the unattended entry point. It fails on governance or
deployment errors, writes a machine-readable report when requested, and is
scheduled by the repository workflow. Jenkins should run the same command
before project verification or deployment; no manual audit request is needed.

## Onboard a project

```bash
python3 scripts/init_project.py /path/to/project \
  --profile rust-product --kind product
python3 scripts/workspace_check.py --root .. --project my-project
```

`--id` is optional and defaults to the kebab-case directory name; an explicit
`--id` must match the derived id unless the directory name is not convertible.

The initializer is non-destructive and writes only missing governance declarations and rules.
It never copies gate runtimes, installers, credentials, or universal rule implementations into a product repository.

## Deployment promotion

A project becomes `deployable: true` only through a recorded promotion
transaction. The script `scripts/promote_project.py` runs the project
audit, verifies the compose file, requires an explicit evidence reference,
mutates the `deployment.*` block in `.project.json`, and appends a
tamper-evident entry to `deployment/promotions.json`. Hand-edits that set
`deployable: true` without a matching ledger entry fail the audit with
`DEPLOYMENT_PROMOTION`; a stale revision (the project's HEAD moved after
promotion) raises the triage-only `DEPLOYMENT_PROMOTION_STALE` warning.

```bash
python3 scripts/promote_project.py <project-id> \
  --evidence-ref "<revision-or-build pointer>" \
  [--compose-file <name>] [--jenkins-job <name>] [--actor <name>] [--force]

python3 scripts/promote_project.py <project-id> --demote
```

The script never runs a project verification itself; it records the
evidence reference the operator supplies, so the audit boundary stays
with the project's own verification pipeline.

## Jenkins

`deployment/projects.json` is the safe handoff to `jenkins-local`. Generate it only after the governance check:

```bash
python3 scripts/jenkins_manifest.py --check
```

The manifest enumerates only projects with a current `deployable: true`
declaration backed by a promotion ledger entry. Jenkins still owns
synchronization, secrets, Compose, database provisioning, job registration,
and deployment. The governance project only says which projects are
eligible and which verification command must pass.

## Status boundary

Registry presence is not implementation evidence. The checker records declarations and policy status; project gates must provide build, test, integration, provider, runtime, and release evidence separately.
