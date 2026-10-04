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

## 5. The debt record under-reported: the defect this pass found

- [x] 5.1 **Measured, not assumed.** The gate (`driftwatchdog gate
  --dry-run`, the build at `driftwatchdog/target/debug/`) reports **55
  repositories and 170 unbound required checks**. The committed
  `gate-debt.json` named **25 repositories and 48 checks**. 122 pairs
  across 30 repositories were missing, and no pair was spurious. The
  `driftwatchdog` on `PATH` is a `cargo install` build from 2026-10-01
  that predates unbound reporting and answers 0 for the whole fleet; the
  scan must use the repository build.
- [x] 5.2 **The cause, with the evidence.** A manifest selects a check two
  ways: by listing it under `checks:`, and by naming a `profile:` whose
  default set the gate schedules anyway (`driftwatchdog/src/gate/manifest.rs`
  `selected_without_triggers` → `profile_defaults`). `read_manifest` read
  only the first. Every missing pair is a concern the gate's
  `product`/`rust-product` profile schedules: 41 `placeholder-threshold`,
  41 `product-code-boundary`, 40 `governance-quality` — the 41st is
  `driftwatchdog`, the one repository that lists `governance-quality` under
  `checks:` itself and is therefore the single `governance-quality` entry
  the old record did have. `aesthra` is the shape: six declared checks, all
  bound, three profile-scheduled checks the gate still fails on, and no
  entry in the record at all. A repository with no unresolved check of its
  own was dropped for "having no gaps", so the record read as complete.
- [x] 5.3 **The stated hypothesis was wrong and is not what was fixed.** The
  binder did report the no-rule/no-fallback class: `script_concern()`
  returns exactly the reason string quoted in the bug report, and that
  string is in `by_reason` for the one repository that declares
  `governance-quality` under `checks:`. Nothing was silently skipped for
  want of a rule; the class was invisible because those repositories never
  declared the concern in the first place.
- [x] 5.4 **The fix.** `PROFILE_DEFAULTS` mirrors the gate's
  `profile_defaults`, and `gate_required()` resolves the set the gate would
  fail on: the manifest's own `checks:`, plus the profile's defaults, minus
  what the gate excuses — a `checks: <id>: false` that deselects a profile
  default, a `not_applicable:` exemption with a reason, and
  `source-file-size`, which the gate executes in-process
  (`is_source_file_size_concern`) and never counts unbound. `"optional"`
  stays out because `read_manifest` reads only `true`, and the gate does
  not fail on a non-required check.
- [x] 5.5 **A profile-scheduled check is recorded, never written.** Proved
  against the binary: a manifest whose `commands:` names a check the
  manifest does not select is refused outright —
  `manifest parse error: commands.governance-quality references a check
  that is not selected`. Writing one would trade a reported gap for a
  manifest the gate cannot parse, so the reason tells the reader the fix
  instead: select it under `checks:`, add `scripts/check-<id>.*`, or
  exempt it.
- [x] 5.6 **The second, quieter hole: a dirty manifest.** The `is_dirty`
  check ran before the manifest was read, so a repository with uncommitted
  work returned with no concerns and vanished from the record while the gate
  still failed on it — the exact behaviour §5 below recorded as a
  reporting quirk. The write is still refused; the classification is not.
  An `--apply` run immediately after a previous one no longer writes a
  record that omits every repository it had just written to.
- [x] 5.7 **The record is regenerated and committed.**
  `python3 scripts/bind_gate_commands.py --root /home/paul/code --apply
  --debt-out /home/paul/code/workspace-governance/gate-debt.json` — run
  from a clean fleet, so the record is not built from a run that skipped its
  own writes. It now names **55 repositories and 170 checks**, equal to the
  gate's own count. A dry run first confirmed `0` repositories with a
  pending binding, so `--apply` wrote **no** sibling manifest; the fleet was
  re-checked afterwards and every `git status --porcelain -- .ai-gate/gate.yaml`
  across the 81 repositories is empty.
- [x] 5.8 **The regression is now impossible to reintroduce silently.**
  `ProfileSelectionTests` (12) pins the selection model on fixtures,
  including the repository whose only debt is profile-scheduled, the
  in-process check, the disabled check, the exemption, the optional check,
  and the refusal to write. `GateOracleTest` (5) compares the committed
  record **and a fresh dry run** against the real binary's unbound set, by
  set equality and never by count, so the fleet may grow or re-profile
  freely. It skips when the binary is not built, and skips with a named
  reason when the binary is too old to report unbound checks — proven first
  against a throwaway one-check repository, so the comparison can never run
  against a blind oracle.
- [x] 5.9 **Negative controls, run and then reverted.**
  (a) Making `gate_required` return the manifest's `checks:` alone — the
  pre-fix behaviour — turned 5 tests red, including
  `test_a_repository_whose_only_debt_is_profile_scheduled_is_still_listed`
  with `AssertionError: demo is missing from the debt record; the record
  names []` and `test_a_fresh_run_reproduces_the_gate_set` with the 122-pair
  diff and the message "the gate reports unbound checks a fresh run does not
  find; the record would be regenerated without them".
  (b) Moving the `is_dirty` check back above the classification turned
  `test_a_dirty_manifest_is_still_classified_and_recorded` red with
  `AssertionError: Lists differ: [] != [('demo', ['build', 'tests'])]`.
  Both controls were reverted and the suite returned to 722.
- [x] 5.10 **The shared fixture moved to `profile: minimal`.** It said
  `profile: product`, so every one of the 89 fixture tests gained three
  unresolvable concerns that had nothing to do with what each test was
  about. `minimal` is the built-in profile with an empty default set, which
  leaves `checks:` as the only selection in play and each test asserting
  exactly what it asserted before. The profile path is covered against
  `product` itself in `ProfileSelectionTests`. No assertion was weakened,
  skipped or filtered.
- [x] 5.11 Spec delta extended: a new requirement, *The debt record is
  complete against the gate's own unbound set*, with five scenarios, and
  *Only a concern the repository declared is bound* amended to say that a
  `profile:` is a declaration and that a profile-only check MUST NOT be
  written.

## 6. Deliberately not done

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
  - ~~A second `--apply` run immediately after the first sees its own writes
    as `DIRTY`, skips those repositories, and therefore writes a debt
    record that under-reports.~~ **Fixed in §5.6.** The dirty check now
    refuses only the write; the checks are classified and recorded either
    way, and `test_a_dirty_manifest_is_still_classified_and_recorded` pins
    it. Two dry runs and two `--apply` runs are now byte-identical.
- [ ] **Three `FleetTest` tests are red, and were red before this pass.**
  `test_every_path_a_bound_command_names_really_exists`,
  `test_no_bound_dotnet_command_is_missing_its_entry_file` and
  `test_the_fleet_exercises_the_slnx_path_at_scale` filter on
  `status == BOUND`. The fleet is now applied, so a dry run classifies
  every command as `ALREADY_BOUND` and the filter matches nothing:
  `AssertionError: 0 not greater than 0 : no path was checked at all`. The
  baseline on arrival was **704 passed, 3 failed**, not 707 green. The
  assertions are stale about the fleet's state, not about this defect, and
  they were left alone rather than edited inside a fix that has its own
  evidence. Widening the filter to `ALREADY_BOUND` is the obvious repair
  and belongs to whoever owns that file's fleet assumptions.
- [ ] **The change is not archived.** Archiving needs separate
  authorization.
