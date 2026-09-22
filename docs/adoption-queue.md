# Adoption Queue

## Adopted in the first coordination slice

These projects now have `.project.json`, a selected governance profile, and a real verification command:

1. `forge` — portfolio control-plane candidate.
2. `driftwatchdog` — shared quality/evidence gate runtime.
3. `sisyphusfy` — agent iteration runtime.
4. `ariadex` — supervised runtime operator.
5. `dotnet-platform-libs` — reusable .NET library platform.
6. `labrys` — application/runtime platform candidate.
7. `jenkins-local` — deployment execution layer.
8. `alltools-platform` — application-specific platform.

## Second batch adopted

The next deployment-capable batch now has declarations and profile checks:

- `alethefy`
- `crossify`
- `cvunify`
- `hermexa`
- `hypora`
- `lexora`
- `openaccounting`

These projects are structurally adopted, but remain non-deployable until their declared verification commands and release evidence are run and reviewed.

## Third batch adopted

- `hermora`
- `hestia-lab`
- `lore-mix`
- `metiscope`
- `mortalect`
- `opendockify`

These projects are also structurally adopted and remain non-deployable pending runtime evidence.

## Remaining work

The workspace audit still fails for repositories without `.project.json`. This is intentional: registration alone is not adoption. For each remaining active project:

1. Run `scripts/init_project.py` with the correct profile and kind.
2. Replace the generated verification command with the repository's real command.
3. Review privacy, security, architecture, and deployment exceptions.
4. Run `scripts/workspace_check.py --project <id>`.
5. Run the project-local verification and CI.
6. Mark the registry entry `adoption: adopted` only after the evidence is recorded.

Learning, scratch, archived, and deployment-support directories should use the `inventory` or `deployment` profile instead of being forced into a product profile.

## Deployment readiness

No project is emitted into `deployment/projects.json` until its declaration sets `deployment.deployable: true`, names an existing Compose file and Jenkins job, and passes the project checker. The initial generated manifest is therefore empty by design.
