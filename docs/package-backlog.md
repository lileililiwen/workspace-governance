# Package Backlog

Index of the workspace-maturity packages. **Each package is an OpenSpec change
authored in the repository that owns the work**, so a fresh conversation
implements it there against that repository's `AGENTS.md`. This file is only the
index and the coordination rules; the proposal, design, tasks and spec live in
the change directory.

| # | Package | Owning repository | Change location | State |
|---|---|---|---|---|
| 1 | `registry-and-declaration-integrity` | workspace-governance | `openspec/changes/archive/2026-09-26-registry-and-declaration-integrity/` | shipped |
| 2 | `shared-rules-single-source` | workspace-governance | `openspec/changes/archive/2026-09-26-shared-rules-single-source/` | shipped |
| 3 | `portfolio-vocabulary-normalization` | workspace-governance | `openspec/changes/portfolio-vocabulary-normalization/` | authored |
| 4 | `gate-evidence-export` | driftwatchdog | `openspec/changes/gate-evidence-export/` | authored |
| 5 | `platform-consumer-bootstrap` | dotnet-platform-libs | `openspec/changes/platform-consumer-bootstrap/` | authored |
| 6 | `rust-platform-consumer-baseline` | rust-platform-libs | `openspec/changes/rust-platform-consumer-baseline/` | authored |
| 7 | `contracts-consumer-parity` | platform-contracts | `openspec/changes/contracts-consumer-parity/` | authored |
| 8 | `governance-front-door` | workspace-governance | `openspec/changes/governance-front-door/` | authored |

Package 4 was called `gate-run-evidence` in the original portfolio map; 5 was
`platform-adoption-dotnet`; 6 `platform-adoption-rust`; 7
`contracts-single-source`. The authored changes use the more precise names
above, because reading the target repositories showed the real gap is narrower
than the map assumed (for example driftwatchdog's `release-evidence-gate` spec
already owns the required-evidence and stale-revision guards, so package 4 is
the *export*, not the guard).

## Implement a package

1. Open the owning repository.
2. `openspec list` — that repository holds exactly one active change for the
   package; implement one change at a time.
3. Read the change's `proposal.md`, `design.md`, `tasks.md` and
   `specs/<capability>/spec.md`.
4. **Read `## 0. Caveats and confirmations` in `tasks.md` first.** Every change
   records there the non-obvious intent and the decisions a reviewer must confirm
   before implementing; the task groups below it assume those caveats are read.
5. Follow that repository's `AGENTS.md`: BFS → DFS → BFS, two commits
   (implementation + archive, then a `HANDOFF.md`-only commit), strict OpenSpec
   validation, no push.
6. Never implement a cross-repo package from another repository.

## Dependency order

- Shipped: 1, 2.
- 3 depends on 1 and 2; 4 depends on 3 (it exports in the vocabulary 3
  canonicalizes).
- 5 and 6 are independent of each other and of 3.
- 7 depends on 5 and 6 (it names their consumer wiring as the follow-up).
- 8 is last: it routes to the others.

## Coordination rules

- Consume the governance vocabulary; never re-declare a field name, a state, a
  `kind` or a `profile` locally.
- One repository per change; author the change where the work is owned.
- If a package reveals a second lifecycle, owner or acceptance oracle, stop and
  propose a follow-up package with a dependency edge rather than expanding it.
- Portfolio oracle after any package:
  `python3 scripts/workspace_check.py --root .. --audit --json` in
  `workspace-governance` must stay at 0 errors.
