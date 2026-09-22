# Workspace Governance

Workspace Governance coordinates the repositories under `/home/paul/code`.
It owns the project registry, governance profiles, bootstrap templates, evidence vocabulary, and deployment declarations.

It does not own product source code, language runtimes, shared gate runtimes, or production execution.

## Ownership

- `forge` is the portfolio control-plane consumer.
- `driftwatchdog` is the shared quality and evidence gate runtime.
- `sisyphusfy` is the agent iteration runtime.
- `ariadex` is the supervised runtime operator.
- `dotnet-platform-libs` is the reusable .NET library platform.
- `jenkins-local` performs Jenkins/Mac deployment execution.

## Mandatory command

Run from this repository. The registry is portable; pass the actual workspace root when auditing a checkout:

```bash
python3 scripts/workspace_check.py --self-check
python3 scripts/workspace_check.py --root /home/paul/code --audit --json
python3 -m unittest discover -s tests -v
```

The audit intentionally reports existing projects that have not yet adopted `.project.json`.
Those projects are migration work, not silently treated as compliant.

## Onboard a project

```bash
python3 scripts/init_project.py /path/to/project \
  --id my-project --profile rust-product --kind product
python3 scripts/workspace_check.py --root /home/paul/code --project my-project
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
