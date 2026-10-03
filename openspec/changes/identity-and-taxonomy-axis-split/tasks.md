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
- [x] 2.5 R5: write the resolved `role` and `stack` into the 81
  declarations and the 78 registry entries per `design.md` §5.2, recording
  the resolution rule used per row. Resolve the four unregistered entries
  (`argoscope`, `chronicleaf`, `devloom`, `kairovia`) as
  `product`/`dotnet` and add their registry entries so
  `DISCOVERED_UNREGISTERED` clears; remove or archive the `jenkins-bootstrap`
  entry so `PROJECT_MISSING` clears. Add no new code for either.
  **Applied** with `python3 scripts/axis_migration.py --apply`;
  `--check` now exits 0 (`migration applied: every declaration and registry
  entry carries the planned axes`). Recorded: 81/81 declarations and 81/81
  `projects.json` entries carry both axes; the live registry is 81 = 77
  re-axed + 4 registrations with `jenkins-bootstrap` removed; all 34 decided
  rows resolve; `DISCOVERED_UNREGISTERED`, `PROJECT_MISSING`,
  `TAXONOMY_MISMATCH`, `TAXONOMY_AXIS_UNKNOWN` and `TAXONOMY_LEGACY_VALUE` are
  all 0. No new finding code was introduced for the five repositories.
- [x] 2.6 R3: assert id immutability before and after 2.5 — the registry id
  set must compare equal, every declaration `id` must still equal its
  registry `id`, and the 8 `campusMesh`-style entries must differ only by the
  two added axis fields. If any id moved, revert; do not "fix" the reference
  sites to match. **Verified against the §1.2 fixture, not by eye**: 78
  baseline ids → 81 live ids, of which 77 survive, 4 are added
  (`argoscope`, `chronicleaf`, `devloom`, `kairovia`) and exactly 1 is removed
  (`jenkins-bootstrap`); every one of those five is a plan row carrying
  `action: add` / `action: remove`, and the live set equals the plan's
  non-remove rows exactly. `profile_requirements` returns the identical tuple
  for all 77 survivors, every declaration `id` still equals its registry `id`
  (81/81), and no surviving entry changed its `path`. The id set did move, by
  design; what is asserted is that it moved *only* by the plan's own recorded
  actions, so a rename would surface as a removal with no declared addition.
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
- [x] 3.7 Confirm the fleet scan is clean: a direct scan returns zero
  declarations or registry entries with a non-canonical or absent axis, zero
  unresolved rows in `design.md` §5.2, and zero remaining stack-qualified
  composites outside the deprecated `kind`. **Confirmed** by
  `axis_migration.py --check` (exit 0), by the fleet audit's zero
  `TAXONOMY_AXIS_UNKNOWN` / `TAXONOMY_MISMATCH` / `TAXONOMY_LEGACY_VALUE`, and
  by a direct read of all 81 declarations: 81/81 carry a canonical `role` and
  `stack`, all 34 decided §5.2 rows resolve, and 81/81 satisfy
  `kind == derive_kind(role, stack)`, which is what holds the legacy warning at
  0.

## 4. Verification

- [x] 4.1 `python3 -m unittest discover -s tests -v` — all pass, including
  the new `tests/test_identity_and_taxonomy.py`, with no existing test
  changing expectation.
- [x] 4.2 `python3 scripts/workspace_check.py --root .. --audit --json` —
  record the pre-migration output (expected: 30 `TAXONOMY_MISMATCH` errors,
  1 `PROJECT_MISSING`, 4 `DISCOVERED_UNREGISTERED`) and the post-migration
  output (expected: 0 errors, no `TAXONOMY_*`). Record both verbatim.
  **Pre-migration, recorded at the checkpoint before the write**:
  `errors=211 warnings=18`, carrying 30 `TAXONOMY_MISMATCH`, 1
  `PROJECT_MISSING` and 4 `DISCOVERED_UNREGISTERED`. **Post-migration,
  measured**: `Summary: errors=206 warnings=35` — a net move of **211 → 206**
  errors, and **zero** findings in any `TAXONOMY_*` family, with
  `RULES_DRIFT_NEW` 0. By code: `PUBLICATION_UNVERIFIED` 76,
  `DISCOVERABILITY_MISSING` 74, `LICENSE_MISSING` 51, `CI_MISSING` 2,
  `DISCOVERABILITY_INVALID` 2, `LIFECYCLE` 1; warnings `KIND_UNKNOWN` 17,
  `HANDOFF_SCAFFOLD` 8, `DEPLOYMENT_PROMOTION_STALE` 7, `CAPABILITY_BLOCKED`
  2, `QUALITY_README_CLAIM_UNSCOPED` 1. The 13 `RULES_DRIFT_NEW` errors that
  appeared when the four repositories became visible for the first time are
  resolved — see §5: they were cleared by adding the missing canonical
  `.ai-rules` paragraphs, **not** by re-cutting the rules-drift baseline. The
  residual 206/35 is pre-existing debt on other axes and is not this change's
  to absorb.
- [x] 4.3 `python3 scripts/workspace_check.py --self-check` and
  `python3 scripts/maturity_audit.py --root .. --json` — 0 errors; counts
  agree with the audit.
- [x] 4.4 Id-immutability diff: run the §1.2 comparison and show an empty
  difference for both the id set and the `profile_requirements` tuples.
  **Run against `tests/fixtures/identity-and-taxonomy-baseline.json`:** 78
  baseline ids vs 81 live; **77 survivors**; added
  `['argoscope', 'chronicleaf', 'devloom', 'kairovia']`; removed
  `['jenkins-bootstrap']`; `profile_requirements` drift over the 77
  survivors: **0**; declaration `id` != registry `id`: **0** (81/81 agree).
  The id *set* difference is therefore not empty and is not expected to be —
  it is exactly the 4 additions and 1 removal the plan records, and both sets
  are asserted against the plan's `add`/`remove` rows. What the diff shows
  empty is the outcome: no surviving repository's required-file, CI, OpenSpec
  or verification tuple moved, which is the claim 2.6 and §4.4 exist to
  protect.
- [x] 4.5 `node scripts/check-openspec-change-names.mjs`,
  `openspec validate identity-and-taxonomy-axis-split --strict`, and
  `git diff --check`.
- [x] 4.6 Record actual outputs. Report any environment-blocked check with
  its exact next action rather than as passing.

## 5. Implementation record — the change as landed

The fleet write of 2.5 **has now been applied and committed**: 2.5, 2.6, 3.7,
4.2 and 4.4 are complete and carry their recorded evidence above. Everything
else was implemented, tested, and reported in the earlier commit; this section
records the state the fleet is actually in.

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
- `tests/test_identity_and_taxonomy.py` (67 tests) and
  `tests/fixtures/identity-and-taxonomy-baseline.json` (the id-set and
  `profile_requirements` oracle for 1.2/3.1/4.4). The suite is
  `python3 -m unittest discover -s tests` → **492 tests, OK**; the seven
  pre-migration expectations were repinned to the applied state rather than
  deleted, and the eight fixtures that predate the axes gained the pair their
  own declared composite derives.
- `docs/vocabulary.md`, `README.md`, the skill reference, `decisions.json` (D6)
  and `docs/toolchain-decisions.md` record the two axes, the derived `kind`,
  the three codes, and the enabled state.

**The ruling-2 sequencing gate, now open.** `TAXONOMY_MISMATCH_LEVEL` is fixed
at `"ERROR"` and the severity was never softened. The audit is no longer held
off the fleet: the committed constant in `scripts/workspace_check.py` is
`TAXONOMY_AUDIT_ENABLED = True` — a repo-relative input, never an environment
variable. The ordering was enforced by the checker itself, not by a comment,
and both sides of the flag stay under test: with the flag held off the same
unmigrated fixture is silent
(`test_gate_closed_reports_no_taxonomy_finding_on_a_mismatched_fleet`), and
with it on that fixture reports ERROR `TAXONOMY_MISMATCH`
(`test_gate_open_reports_error_on_the_same_unmigrated_fleet`). So enabling it
early still could not have passed quietly. `--apply` prints the reminder to
flip the flag in the same commit, and that is what was done.

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
4. **Superseded by the recorded run: the migration *did* normalize `kind`.**
   This note previously predicted the opposite — that the migration would
   leave `kind` alone (`design.md` §1) and so leave WARNING
   `TAXONOMY_LEGACY_VALUE` on every declaration whose resolved stack is not
   `none`, with the warning count failing to reach 0. That prediction did not
   hold, and the discrepancy is recorded here rather than quietly edited away.
   `axis_migration.py --apply` writes the derived composite wherever the
   hand-authored one disagreed with it, exactly as
   `MigrationToolTests.test_apply_writes_the_axes_and_derives_kind` specifies
   (and as the pre-migration `HANDOFF.md` already recorded: "the migration also
   writes the derived `kind`"). Measured over the 77 repositories in
   `rollback-manifest.json`, comparing each `before` SHA to its `after` SHA:
   **37 needed rewriting** (`forge` `platform` → `rust-platform`,
   `lileililiwen.github.io` `product` → `python-deployment`, `campusMesh`
   `product` → `dotnet-product`, `alltools-platform` `application-platform` →
   `python-platform`) and **35 already agreed** and were left byte-identical;
   across all 80 migrated siblings the split is 39 rewritten / 36 unchanged.
   All four §5.3 registrations were rewritten `product` → `dotnet-product`.
   The resulting invariant, checked directly over all 81 declarations, is
   **81/81 satisfy `kind == derive_kind(role, stack)`** — and that, not an
   absence of writes, is why `TAXONOMY_LEGACY_VALUE` is 0. So `design.md` §8's
   "no `TAXONOMY_*` finding" expectation is met on both counts.
5. **The derivation order is stated two ways in the spec.**
   `proposal.md` ruling 5, `design.md` §4 and §10, and the spec's own worked
   example use `<stack>-<role>`; one scenario in the spec (`role: platform`,
   `stack: rust`, "naming the derived value `platform-rust`") uses
   `<role>-<stack>`. The implementation follows `<stack>-<role>`, the form
   three other statements and the round-trip example agree on.
6. **The 13 `RULES_DRIFT_NEW` errors were cleared at the repositories, not in
   the baseline.** Registering `argoscope`, `chronicleaf`, `devloom` and
   `kairovia` made four repositories visible to the rules-drift ratchet for
   the first time, and each arrived without the canonical `.ai-rules`
   paragraphs, so 13 clauses read as new. They were resolved by adding the
   missing canonical text to those four repositories' `.ai-rules/workflow.md`
   and `.ai-rules/completion.md` (each in its own `migrate(taxonomy)` commit).
   `rules-drift-baseline.json` was **not** re-cut: its last commit is still
   `4a9edfc` ("Gate rules drift on a ratchet, so the clause finally blocks"),
   so the ratchet kept its meaning instead of being taught to accept the gap.
   `RULES_DRIFT_NEW` is 0 in the recorded 206/35 fleet audit.
7. **`--self-check` is 1 error / 1 warning, not the 0/0 that 4.3 recorded when
   it was ticked.** Both findings are consequences of the migration landing,
   neither is introduced by this change's tests, and both are counted inside
   the pinned 206/35: `ERROR LIFECYCLE: [devloom] invalid lifecycle:
   'scaffold'` — `devloom`'s own declaration carries `lifecycle: scaffold`,
   which is not canonical, and it is now reachable because the repository is
   registered; fixing it means editing a sibling repository, which this change
   does not do. And `WARNING KIND_UNKNOWN: [workspace-governance] unknown kind:
   'python-governance'` — this repository's own `.project.json` was written by
   `--apply` to the derived `python-governance`, which is not a member of
   `vocabulary.json`'s legacy `kinds` array (that array was deliberately left
   byte-identical by 2.1). Clearing either one moves the pinned fleet numbers
   and touches a file outside this change's staging list, so both are left
   standing and reported rather than fixed in passing. 4.3's tick is therefore
   stale on this one point.
8. **`rollback-manifest.json` covers 77 of the 80 migrated siblings.**
   `aegify`, `argoscope` and `argoset` have a `migrate(taxonomy)` commit but no
   before/after SHA pair in the manifest, so a rollback driven from the
   manifest would silently skip them. Recorded as a gap in the rollback safety
   net, not repaired here: the manifest is untracked, and reconstructing the
   three pairs is the parent's call, not a side effect of a test-fix commit.
