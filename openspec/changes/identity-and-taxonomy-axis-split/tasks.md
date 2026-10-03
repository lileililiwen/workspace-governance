# Tasks: identity-and-taxonomy

## 0. Caveats and confirmations

- [x] **The two axis sets are ruled as designed.** The 6 roles and 6 stacks in
  `design.md` §4 are derived from the values observed on 2026-10-03 and are
  approved as the canonical sets (`design.md` §10, ruling 1).
  `TAXONOMY_AXIS_UNKNOWN` remains WARNING, so a later vocabulary addition
  cannot red the fleet.
- [x] **The three contested `shared-library` rows and `lileililiwen-site` are
  ruled.** `platform-contracts`, `rust-platform-libs` and
  `dotnet-platform-libs` take `role: platform` — `shared-library` is **not** a
  seventh role, because no consumer branches on it and the distinction that
  carries weight is already carried by the frozen `profile` values
  `dotnet-library` / `rust-platform`. `lileililiwen-site` takes
  `role: deployment`: it is a Hugo static site
  (`verification.command` is `hugo --gc --minify`, `CNAME` files, 16 `.html`,
  12 `.py`, no entry point, no compose, no Dockerfile) that ships no runnable
  artifact, and both authority surfaces already agree on
  `profile: deployment`. See `design.md` §10, rulings 1 and 4.
- [ ] **`TAXONOMY_MISMATCH` is ruled ERROR, so the migration must land in the
  same package.** Do not enable the finding before the 30 rows are resolved, or
  the audit fails for 30 repositories with no owner action recorded. The
  pre-migration count of 30 is a **fixture baseline**, not a sanctioned merge
  state: it is what the test asserts against, and it is not a state the branch
  may be merged in. See `design.md` §10, ruling 2.
- [x] **Assert id immutability as a set comparison, not a spot check.** The
  8 `campusMesh`-style entries (`campus-mesh`, `care-bridge`,
  `hestia-lab`, `lore-mix`, `lileililiwen-site`, `open-teacher-kit`,
  `retake-kit`, `trail-crew`) are already correct. Any rename of any id
  breaks `DECLARATION_ID`, capability-adoption provider bindings, the
  decisions register, and the promotion ledger simultaneously.
- [x] **The census is a migration aid, not an audit signal.** Record it per
  row in `design.md` §5.2, then delete the census from the runtime path. A
  tree-derived axis would make the declaration's own statement irrelevant.
- [x] **`profile_requirements` stays untouched.** Prove per repository that
  no required-file, CI, OpenSpec, or verification outcome changes. The axes
  are descriptive and must never become a requirements driver.
- [x] **The census must not be run against the fleet as an audit.** Use the
  bounded, read-only walk in `design.md` §5.1 only, with no project command
  executed and no sibling written.
- [ ] **Stage only this change directory.** The repository has a
  pre-existing uncommitted `.project.json` edit and an untracked
  `MATURITY_PROGRESS_SUMMARY.md`; they must not be swept into the change's
  commits.

## 1. BFS — Baseline and impact coverage

- [x] 1.1 Record the baseline counts before any edit: 81 declarations, 78
  registry entries, 1 entry whose `path` does not resolve
  (`jenkins-bootstrap`), 4 declarations with no registry entry
  (`argoscope`, `chronicleaf`, `devloom`, `kairovia`), 8 entries where
  `id != path`, 30 of 77 comparable entries where registry `profile` differs
  from declaration `kind`, and 33 of 81 declarations where `kind` differs
  from the declaration's own `profile`.
- [x] 1.2 Snapshot the registry id set and the `profile_requirements(profile)`
  tuple for all 78 entries into a fixture, so both can be compared after
  the migration. This fixture is the immutability and no-outcome-change
  oracle; without it neither claim is checkable.
- [x] 1.3 Map each requirement in `proposal.md` onto existing code:
  `validate_registry` (`scripts/workspace_check.py:275`),
  `validate_kind` (`:372`), `profile_requirements` (`:319`),
  `canonical_profiles_for`/`canonical_kinds_for` (`:64`, `:68`),
  `_vocabulary_for` (`:57`), and the `finding()` severity vocabulary (`:160`).
- [x] 1.4 Confirm the additive shape: `role` and `stack` go into
  `properties` with matching `$defs` and **not** into `required`, so a
  declaration without them stays schema-valid and reports
  `TAXONOMY_AXIS_UNKNOWN` instead of `DECLARATION_SCHEMA`.
- [ ] 1.5 Add failing tests before implementation: axis canonical-set
  membership for registry and declaration, the `kind` derivation round-trip,
  a fixture reproducing the 30-repository disagreement set, a fixture
  asserting the 8 alias entries produce no taxonomy finding, and a
  vocabulary-load failure test for an empty `roles` array.
- [x] 1.6 Verify the implementation-handoff gate: Python 3.11,
  `workspace-governance`, no shared-library boundary crossed, no sibling
  repository edited.

## 2. DFS — Requirement-by-requirement implementation

- [x] 2.1 R1: add `roles` and `stacks` to `vocabulary.json`; surface them
  from `scripts/vocabulary.py` with the existing fail-closed duplicate and
  empty-list handling; add `canonical_roles_for` and `canonical_stacks_for`
  to `workspace_check.py`. Keep `kinds` and every other array
  byte-identical so no existing consumer sees a diff.
- [x] 2.2 R1: add `role` and `stack` to `schemas/project.schema.json` with
  matching `$defs`, not in `required`; extend `validate_registry` to read
  them; implement `validate_taxonomy` emitting WARNING
  `TAXONOMY_AXIS_UNKNOWN` for an absent or non-canonical value, naming the
  offending value and both canonical sets.
- [x] 2.3 R2: implement the `kind` derivation
  (`f"{stack}-{role}"`, or `role` when `stack` is `none`) and emit WARNING
  `TAXONOMY_LEGACY_VALUE` when a stack-qualified composite remains while
  both axes are present, and when a hand-authored `kind` disagrees with its
  own derived form. Update the `kind` schema description to state that it is
  derived and deprecated. Call `validate_taxonomy` from `validate_project`
  where `validate_kind` is called today; keep `validate_kind` so
  `KIND_UNKNOWN` keeps its shipped meaning.
- [x] 2.4 R4: emit ERROR `TAXONOMY_MISMATCH` from `validate_project` when a
  registry `role`/`stack` differs from the declaration's, naming both values
  and both keys. An axis present in only one of the two surfaces is
  `TAXONOMY_AXIS_UNKNOWN`, not a mismatch — an absent value is not a
  contradiction.
- [ ] 2.5 R5: write the resolved `role` and `stack` into the 81
  declarations and the 78 registry entries per `design.md` §5.2, recording
  the resolution rule used per row. Resolve the four unregistered entries
  (`argoscope`, `chronicleaf`, `devloom`, `kairovia`) as
  `product`/`dotnet` and add their registry entries so
  `DISCOVERED_UNREGISTERED` clears; remove or archive the `jenkins-bootstrap`
  entry so `PROJECT_MISSING` clears. Add no new code for either.
- [ ] 2.6 R3: assert id immutability before and after 2.5 — the registry id
  set must compare equal, every declaration `id` must still equal its
  registry `id`, and the 8 `campusMesh`-style entries must differ only by the
  two added axis fields. If any id moved, revert; do not "fix" the reference
  sites to match.
- [ ] 2.7 Update `docs/vocabulary.md` with the two axis tables, the
  derivation rule, the id-immutability rule, and the three new finding
  codes. Update `README.md` with one short paragraph and link rather than
  restate. Record the outcome in `HANDOFF.md` in the second commit.
- [x] 2.8 Record the change in `decisions.json` with the measured
  disagreement count, the contested rows, and the immutability rule, so the
  reasoning survives the migration.

## 3. BFS — Cross-surface regression and completeness

- [x] 3.1 Prove no project changed its outcome: for all 78 entries,
  `profile_requirements(profile)` returns the identical tuple from the §1.2
  fixture, and the audit's `REQUIRED_FILE`, `CI_MISSING`,
  `OPENSPEC_MISSING` and `VERIFICATION_COMMAND` findings are unchanged.
  Only `TAXONOMY_*` findings may appear.
- [x] 3.2 Prove identity is untouched: `decisions.json` still validates
  against the registry id set, `deployment/promotions.json` still resolves,
  and the 8 alias entries report no identity or taxonomy finding.
- [x] 3.3 Prove the vocabulary cannot be silently empty: a fixture with a
  missing, unparseable, or empty `roles`/`stacks` makes the tool exit
  non-zero naming the file, and never falls back to an empty set.
- [x] 3.4 Prove the axes do not leak into evidence: no `evidence_status`,
  `deployable`, promotion, or capability-adoption outcome changes for any
  repository, and `measure_capability_adoption` is not called with an axis
  value.
- [x] 3.5 Confirm `maturity_audit.py` still reports the single
  `workspace_check.py` result and computes no second opinion, and that the
  Forge adapter's observation keys, exit codes (0/2/3) and redaction
  behaviour are untouched.
- [x] 3.6 Confirm `init_project.py` still derives the same ids: init a
  fixture directory named `hestiaLab` and confirm the written declaration
  still uses `hestia-lab` with the real `path` recorded.
- [ ] 3.7 Confirm the fleet scan is clean: a direct scan returns zero
  declarations or registry entries with a non-canonical or absent axis, zero
  unresolved rows in `design.md` §5.2, and zero remaining stack-qualified
  composites outside the deprecated `kind`.

## 4. Verification

- [x] 4.1 `python3 -m unittest discover -s tests -v` — all pass, including
  the new `tests/test_identity_and_taxonomy.py`, with no existing test
  changing expectation.
- [ ] 4.2 `python3 scripts/workspace_check.py --root .. --audit --json` —
  record the pre-migration output (expected: 30 `TAXONOMY_MISMATCH` errors,
  1 `PROJECT_MISSING`, 4 `DISCOVERED_UNREGISTERED`) and the post-migration
  output (expected: 0 errors, no `TAXONOMY_*`). Record both verbatim.
- [x] 4.3 `python3 scripts/workspace_check.py --self-check` and
  `python3 scripts/maturity_audit.py --root .. --json` — 0 errors; counts
  agree with the audit.
- [ ] 4.4 Id-immutability diff: run the §1.2 comparison and show an empty
  difference for both the id set and the `profile_requirements` tuples.
- [x] 4.5 `node scripts/check-openspec-change-names.mjs`,
  `openspec validate identity-and-taxonomy-axis-split --strict`, and
  `git diff --check`.
- [x] 4.6 Record actual outputs. Report any environment-blocked check with
  its exact next action rather than as passing.

## 5. Implementation record — the change as landed

The fleet write in 2.5 is **not** applied by this change, so 2.5, 2.6, 3.7,
4.2 and 4.4 stay open: they can only be completed in the separately
authorized step that applies `scripts/axis_migration.py`. Everything else is
implemented, tested, and reported.

**What landed in this repository**

- `vocabulary.json` gains `roles` (6) and `stacks` (6); every pre-existing
  array is byte-identical. `scripts/vocabulary.py` loads both fail-closed
  (non-empty, no duplicates, no empty-set fallback) via `AXIS_ENUM_KEYS`.
- `schemas/project.schema.json` gains `role`/`stack` with `$defs`
  `taxonomy_role`/`taxonomy_stack`, **not** in `required`; the `kind`
  description now states that it is derived and deprecated, and `kind` stays
  in `required` (ruling 5).
- `scripts/workspace_check.py` declares `TAXONOMY_AXIS_UNKNOWN`,
  `TAXONOMY_MISMATCH` and `TAXONOMY_LEGACY_VALUE`; adds
  `canonical_roles_for`, `canonical_stacks_for`, `derive_kind`, `split_kind`,
  `validate_registry_taxonomy` and `validate_taxonomy`; reads the two axes in
  `validate_registry` and `validate_project`; keeps `validate_kind` so
  `KIND_UNKNOWN` keeps its meaning. `profile_requirements` is untouched.
- `scripts/axis_migration.py` is the migration artifact: it reads the decided
  rows out of `design.md` §5.2/§5.3, resolves every other declaration with the
  §5.1 order, refuses to plan if the fleet has drifted from the decided table
  or if any existing `id`/`path` pair would move, prints the plan by default,
  and writes only with `--apply`. `--check` reports whether the migration has
  been applied (exit 3 while any row is outstanding).
- `migration/identity-and-taxonomy-axis-split.json` is the committed plan:
  81 declaration rows, each with the resolved `role`/`stack`, the rule, the
  source, and the census evidence; plus 77 registry axis rows, 4 additions and
  1 ghost removal.
- `tests/test_identity_and_taxonomy.py` (65 tests) and
  `tests/fixtures/identity-and-taxonomy-baseline.json` (the id-set and
  `profile_requirements` oracle for 1.2/3.1/4.4).
- `docs/vocabulary.md`, `README.md`, the skill reference, `decisions.json` (D6)
  and `docs/toolchain-decisions.md` record the two axes, the derived `kind`,
  the three codes, and the not-yet-enabled state.

**The ruling-2 sequencing gate.** `TAXONOMY_MISMATCH_LEVEL` is fixed at
`"ERROR"` and the severity is never softened. The whole taxonomy audit is held
off the fleet by the committed constant `TAXONOMY_AUDIT_ENABLED = False` in
`scripts/workspace_check.py` — a repo-relative input, never an environment
variable. The ordering is enforced by the checker itself, not by a comment:
with the flag on, the same unmigrated fleet that is silent with the flag off
reports ERROR `TAXONOMY_MISMATCH` and turns the gate red
(`SequencingGateTests.test_gate_open_reports_error_on_the_same_unmigrated_fleet`).
`--apply` prints the reminder to flip the flag in the same commit.

**Deviations and open items, recorded rather than resolved silently**

1. **Tests were written after the implementation, not before** (1.5 stays
   unchecked). The cases it names all exist; the TDD ordering it asks for did
   not happen.
2. **1.6 says Python 3.11.** The interpreter in this environment is
   3.12.3. The code stays 3.11-compatible (no syntax newer than 3.11 is used),
   but the suites were executed on 3.12.3.
3. **Two values are derived rather than stated by the table.**
   `platform-contracts` is `stack: python` although `design.md` §5.2 records
   `python` or `none`; the §5.1 rule-4 census in the decided row's own
   evidence (14 `.py`) selects `python`, the row is marked
   `owner_confirmation_required`, and a test pins that it is the only such row.
   `pluggify` is `role: product` because `typescript-monorepo` ends in a layout
   word that §9 defers as an axis, and `design.md` §4's own role census
   (66 `product`) pins the value that remains legal. With ruling 4 applied the
   role census is 65 `product` / 2 `deployment`; §4's pre-ruling table reads
   66/1.
4. **`design.md` §8 expects "no `TAXONOMY_*` finding" once the migration
   lands.** The migration does not rewrite `kind` (design §1), and ruling 5
   makes the derived form the authority a hand-authored `kind` is measured
   against, so a declaration whose `kind` is a bare role while its resolved
   stack is not `none` will report WARNING `TAXONOMY_LEGACY_VALUE`. The ERROR
   count does reach 0; the warning count does not. Whether `kind` is rewritten
   during the migration is an owner decision this change does not take.
5. **The derivation order is stated two ways in the spec.**
   `proposal.md` ruling 5, `design.md` §4 and §10, and the spec's own worked
   example use `<stack>-<role>`; one scenario in the spec (`role: platform`,
   `stack: rust`, "naming the derived value `platform-rust`") uses
   `<role>-<stack>`. The implementation follows `<stack>-<role>`, the form
   three other statements and the round-trip example agree on.
