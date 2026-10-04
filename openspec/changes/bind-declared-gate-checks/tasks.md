# Tasks: bind-declared-gate-checks

## 0. Caveats and constraints

- [x] **The declared `stack` is not an input.** `.project.json` `stack` is
  wrong for 27 of the 81 repositories by shape, so it is not passed into
  any detection function (`design.md` §2).
- [x] **No sibling repository is written.** The verification this change
  requires is a dry run across all 81 repositories. Applying the bindings
  to 69 sibling manifests is a separate authorization under the
  cross-repo boundary in `AGENTS.md`; `--apply` exists for it and this
  change does not exercise it over the fleet (`design.md` §10). It is
  exercised over `tmp_path` fixtures only.
- [x] **No concern is added or removed.** A concern is bound only if the
  repository's own `checks:` already selected it.
- [x] **A gap is recorded, never closed with a guess.** A wrong command
  is worse than an honest gap.
- [x] **No `rm`.** Cleanup uses `tempfile.mkdtemp()` plus
  `shutil.rmtree(..., ignore_errors=True)`.
- [x] **No commit sweeps unrelated work.** The tree carries an untracked
  `openspec/changes/bind-declared-verification/` directory from an
  earlier session. It is not staged and not committed by this change.
  `main` only, no branch, no `git add -A`, no attribution trailers, no
  push.

## 0b. Where the previous session stopped

The generator, the sibling rename and this spec directory were written. The
work was aborted before the tests and before either commit. This section
records the state the tests were added to.

- [x] The generator `scripts/bind_gate_commands.py` is complete and works.
  A fleet dry run over all 81 repositories resolves 51 and partially
  resolves 25, with 0 refused, 48 unresolved checks, 18 left in place and 5
  repositories with no manifest. Measured before the tests were written
  and again after, unchanged.
- [x] `scripts/bind_verification_command.py` differs from `HEAD` only by
  the two-helper rename (`_top_level_block_bounds` →
  `top_level_block_bounds`, `_entry_value` → `entry_value`) with every
  call site updated, so the new generator can reuse the existing YAML
  editor. The sibling's own tests pass and its own dry run still reports
  `BOUND: 0, ALREADY_BOUND: 76, CONFLICT: 0, REFUSED: 0`, so the rename
  changed no behaviour.
- [x] **The generator had no tests at all.** That is the gap this pass
  closes. `tests/test_bind_gate_commands.py` now holds 92 tests.

## 1. BFS — Baseline and blast radius

- [x] 1.1 Record the baseline before any edit: suite `Ran 615 tests … OK`;
  76 manifests; 421 required checks; 138 bound; **283 unbound across 69
  repositories**; 7 fully wired; 19 repositories on `.slnx` and 26 on
  `.sln`.
- [x] 1.2 Settle the "8 dotnet repositories with no `.sln`" premise by
  inspection rather than assumption: they are not broken. 19 repositories
  use `.slnx` and pin SDK `10.0.400`; the remaining 3 (`aegify`,
  `hestiaLab`, `smotoox`) genuinely have 2–4 `.csproj` files and no
  solution, which is a finding and not a search failure.
- [x] 1.3 Map every consumer of the sibling's YAML editor before reusing
  it: `bind_verification_command.py` is imported by
  `measure_bound_verification.py` and by
  `tests/test_bind_verification_command.py`, and neither imports the two
  private helpers.
- [x] 1.4 Record the awkward cases that must be handled by disk, not by
  label: `linglitch` (`backend/Linglitch.slnx` plus
  `frontend/package.json`), `loreMix` (root `LoreMix.slnx` plus nested
  `web/package.json`), `alltools-platform` (declared `python`; root Node
  with no `test` script, Rust workspace under `rust/`), `retakeKit`
  (root solution **and** root `package.json` with `test`).

## 2. DFS — One coherent contract

- [x] 2.1 `detect_shape(repo)` walks the disk once and returns the
  solutions, project files, crates, node manifests and their script keys,
  Python runner evidence, Flutter manifests and declared Python security
  tooling, skipping every vendored and cache directory in
  `design.md` §5.
- [x] 2.2 `candidates(concern, shape)` returns the entry points that can
  answer the concern, each with its evidence path, applying the
  dominance rule: filter by capability, prefer root-level, and refuse a
  tie (`design.md` §4).
- [x] 2.3 `derive(concern, shape)` maps a single surviving candidate to a
  command. Every rule is gated on a file existing; there is no default
  and no fallback.
- [x] 2.4 Concerns with no shape rule fall through to two file-gated
  derivations — `scripts/check-<concern-id>.*` and the named OpenSpec-name
  and product-quality scripts — and are otherwise `unresolved`.
- [x] 2.5 `ConcernOutcome` and `Outcome` keep the sibling's field names,
  with `Outcome` gaining only `concerns`, and `Report` gains
  `unresolved()` for the roll-up.
- [x] 2.6 Reuse the sibling's YAML editor rather than writing a second
  one: make `top_level_block_bounds` and `entry_value` public and import
  them with `yaml_scalar`, `discover_repos` and `is_dirty`.
- [x] 2.7 `render_manifest` inserts only the concerns that are missing, in
  the manifest's own `checks:` order, and writes the generated comment
  once. *Correction from the original wording:* `render_manifest` is **not**
  idempotent on its own, and should not be. Idempotence is a property of
  the run: the second run classifies the already-bound concern as
  `ALREADY_BOUND`, so there is no binding left to insert and the file is
  never rewritten. The tests pin the run, not the renderer.
- [x] 2.8 `write_debt_record` emits `gate-debt.json` with `totals`,
  `by_reason` and `repositories`, sorted, with no timestamp.
- [x] 2.9 Exit codes: 0 clean, 2 unusable root, 3 debt remains, with no
  flag that suppresses 3 (`design.md` §9).

## 3. BFS — Re-audit every consumer

- [x] 3.1 Pin the contract with tests covering: the label is not read; a
  `.slnx` is a solution; a vendored `conftest.py` is not evidence; the
  workspace flag follows `[workspace]`; a nested manifest carries its
  `cd`; the exact `package.json` script key is used; a missing `test`
  script produces no command; two candidates stay unresolved; a
  root-level candidate wins; a candidate that cannot answer is dropped
  first; a pure-Python `build` is unresolved; a mixed unittest/pytest
  repository binds `pytest`. → `DetectionTests` (12), `DerivationTests`
  (19), `RefusalTests` (11), `AmbiguityTests` (6).
- [x] 3.2 Pin the write contract: dry run writes nothing; `--apply`
  writes; a second run is byte-identical; a differing existing command is
  a conflict and is not overwritten; an undeclared concern is never bound;
  a `false` check stays `false`; a dirty manifest is skipped; the
  generated comment is not duplicated. → `WriteContractTests` (13),
  `GitWriteContractTests` (3), `WorkspaceWriteTests` (4).
- [x] 3.3 Pin the debt record: every unresolved concern appears with its
  reason, `by_reason` totals match the check count, the file is sorted
  everywhere, two dry runs over an unchanged fleet are byte-identical, and
  there is no timestamp. → `DebtRecordTests` (10).
- [x] 3.4 Suite green: `707 passed, 158 subtests passed`, up from
  `615 passed, 155 subtests passed`. 92 tests added; none weakened, none
  skipped, none filtered to reach green.
- [x] 3.5 Negative control, run and then reverted. Making `derive` return
  `python3 -m build` for a pure-Python package turned three tests red:
  `test_a_pure_python_build_is_unresolved` with
  `AssertionError: 'BOUND' != 'UNRESOLVED'`,
  `test_a_pure_python_repository_never_acquires_a_build_command` with
  `AssertionError: ' -m build' unexpectedly found in 'python3 -m build'`,
  and `test_the_verbose_line_names_an_unresolved_reason`. The binder was
  restored byte-identical and the suite returned to 707.
- [x] 3.6 Fleet dry run across all 81 repositories, with per-repository
  evidence for at least 6 repositories across different stacks and the
  three awkward cases named in §1.4. → `FleetTest` (6) walks the real
  workspace once and asserts invariants only, never a count, so it
  survives fleet churn: no repository is refused; every path a bound
  command or its evidence names exists in that repository; at least one
  `.slnx` repository still receives a .NET command; no bound `dotnet`
  command omits its entry file; every unresolved concern carries a reason;
  every bound concern carries a command and its evidence.
- [ ] 3.7 `README.md` documents the generator, the debt record and the
  exit codes. **Not done in this pass.** The aborted session's gap was the
  missing tests, and this pass closed that gap; this is documentation
  about a tool that is not yet applied to the fleet. Left open
  deliberately rather than half-written.

## 4. BFS — Spec and validation

- [x] 4.1 Spec delta at `specs/gate-command-binding/spec.md`, a new
  capability: the fleet has no gate-command-binding spec, and the
  existing `rules-baseline` capability governs the rules text, not gate
  commands.
- [x] 4.2 `openspec validate bind-declared-gate-checks --strict` passes.
- [x] 4.3 `openspec validate --changes --strict` passes for the whole
  tree. (`openspec list --changes --strict` is not valid on the pinned
  CLI v1.6.0; `openspec list --changes` is the available form.)
- [x] 4.4 Two commits on `main`: spec, implementation, tests and the
  sibling rename first, then `HANDOFF.md` only. No archive commit, no
  branch, no push.

## 5. Deliberately not done

- [ ] **The 283 bindings are not applied to the 69 sibling
  repositories.** That is a separate authorization. The debt record is
  the durable, reviewable statement of what is still unbound, and the
  tool exits 3 until it is applied.
- [ ] **Three `.csproj`-only repositories stay unresolved** for `build`
  and `tests`. Their fix is a `.sln` or `.slnx` in the repository, not a
  generator rule.
- [ ] **`retakeKit` and `linglitch` stay unresolved** for the concerns
  with two candidates. Choosing one is an owner decision about which
  system the gate should run; the debt record names both candidates.
- [ ] **No `stack` label is corrected.** A wrong `stack` is a finding for
  the portfolio change, not for this one, and correcting it here would
  write `.project.json` files across the fleet.
- [ ] **Two reporting quirks the tests found are reported, not fixed**,
  because fixing them means editing the generator rather than adding
  tests. Both are in `HANDOFF.md`:
  - A Python repository with only a `pyproject.toml` and no `tests/`
    directory is labelled `unknown` in the debt record's `shape` field,
    because `Shape.label()` reads `python_dirs`, which detection only
    populates from a test directory.
  - A second `--apply` run immediately after the first sees its own writes
    as `DIRTY`, skips those repositories, and therefore writes a debt
    record that under-reports. Two *dry* runs are byte-identical, which is
    what the tests assert.
- [ ] **The change is not archived.** Archiving needs separate
  authorization.
