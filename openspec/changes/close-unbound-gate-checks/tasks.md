# Tasks: close-unbound-gate-checks

**This is prerequisite work, not business work.** Nothing below is a product
task. Each entry is a decision owed on `workspace-governance`'s gate, and each must be closed
before product work proceeds, so that later gate results are read against a
baseline that is actually standing.

## 0. Preconditions

- [x] 0.1 The debt is read from the committed record
  `workspace-governance/gate-debt.json` — not from gate output parsed by hand,
  and not from a fresh binder run.
- [x] 0.2 Every reason in §1 is quoted from that record rather than restated,
  so this change and the record cannot disagree.
- [x] 0.3 No `.ai-gate/gate.yaml` and no `.project.json` is modified by this
  change. It writes change files only.
- [ ] 0.4 An owner is named for `workspace-governance`, because a tie and an owner-only
  decision cannot be closed by a tool.

## 1. Close each unbound check

Each item names the file, the key, or the command. There is nothing to
re-derive.

### 1. `security` — UNBOUND

- **Reason, quoted from `gate-debt.json`:** no Python security tool is declared in this repository's pyproject.toml or requirements*.txt, and a Python dependency audit is not in the standard library
- **On disk today:** no `pyproject.toml` and no `requirements*.txt` in this
  repository, so no dependency-audit tool is declared anywhere the binder can
  read one from.

**Close it — declare the tool, then bind it.**

- [ ] 1.1 Add a `pyproject.toml` or `requirements-dev.txt` declaring `pip-audit`
  in the development dependency group, and commit it.
- [ ] 1.2 Write `commands: security: python3 -m pip_audit` in
  `.ai-gate/gate.yaml`, or a hand-written command of equivalent effect.
- [ ] 1.3 Re-run `python3 scripts/bind_gate_commands.py --root
  /home/paul/code` from `workspace-governance` and confirm `security` is no
  longer in this repository's `unresolved` list.
- [ ] 1.4 Run `driftwatchdog gate --dry-run` against this repository and confirm
  `security` is not reported as `UNBOUND`.

## 4. Definition of done

- [ ] 2.1 `gate-debt.json` reports **0** unresolved checks for `workspace-governance`.
- [ ] 2.2 `driftwatchdog gate --dry-run` reports no `UNBOUND` check for
  `workspace-governance`.
- [ ] 2.3 Every concern closed is closed by a **written** command or a
  **written** exemption in `.ai-gate/gate.yaml`. No gap is closed by deleting
  the file, silencing the gate, or leaving a script that exits `0` without
  checking anything.
- [ ] 2.4 The gate runs for this repository and its result is recorded here
  before product work starts.

## 5. Deliberately not done

- [ ] **No command is bound here.** Binding is the decision these tasks
  exist to request; a change that bound all 1 of them would have made the
  decisions, and the decisions are the owner's.
- [ ] **The change is not archived.** Archiving needs separate authorization.
