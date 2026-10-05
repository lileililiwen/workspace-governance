# Workspace Governance Handoff

## Current state

current_spec: identity-and-taxonomy-axis-split

**The test suite is green, and one decided row was the reason it was not.**
`test_the_gate_is_open_and_the_fleet_corpus_is_clean` was the only failure
across 761 tests. It runs `axis_migration.py --check` over the live 81-project
fleet, and that refused:

```
refused: lileililiwen-site: design.md §5.2 rule 4: ... records kind 'product'
but the declaration says 'deployment'; the fleet has drifted from the decided table
```

**The guard was right; the table was stale.** The owner corrected
`lileililiwen-site` to `stack: none` on two surfaces on 2026-10-05 — the sibling
declaration in `e9cc5df` ("a static site ships no implementation language", and
"Python runs only at build time for the content validators") and the registry in
`9bab1b7` ("The project's own `.project.json` already declares stack 'none', so
the two disagreed and `workspace_check` reported `TAXONOMY_MISMATCH`"). The
third surface, the §5.2 decided table, was not updated, so it still described a
superseded decision.

The mechanism is the guard's accepted set, not a code defect. Under ruling 7 a
decided row accepts its own recorded `kind` **and** the derived value of its own
`role` × `stack`. With `stacks: ['python']` that set is
`{'product', 'python-deployment'}`, while `role: deployment` with
`stack: none` derives the bare `'deployment'` under ruling 5. A value that is
correct on both live surfaces was therefore refused against its own table. The
fix is the data, not the guard: the §5.2 `stack` cell is now `none`, and the
guard accepts the bare derived role without being loosened.

The extent was measured before the edit, because `_assert_row_matches_fleet`
raises on the **first** refusal and hides everything behind it. A read-only
probe of every decided row against the live declaration and registry axes found
exactly **2** divergences, both this project's `stack`, and no other row.

Also changed, and why it had to change with the table:

- `migration/identity-and-taxonomy-axis-split.json`, the two
  `lileililiwen-site` rows: `stack`, `rule` and `source`.
  `declared_kind` stays `product` on purpose. `--write-plan` would regenerate
  the file from today's fleet and rewrite `declared_kind` to the post-migration
  `deployment` on all 81 rows, destroying the pre-migration measurement ruling 6
  exists to preserve, so the four changed fields were edited directly.
- `tests/test_identity_and_taxonomy.py`: the existing pin on this row moves from
  `"python"` to `"none"` — still an exact assertion, so drift off `none` still
  fails. Three tests were added, because the break had no cheap guard:
  `test_a_stack_none_row_accepts_the_bare_derived_role`,
  `test_a_stack_none_row_still_refuses_a_third_kind` (`kind: inventory` is still
  refused, so ruling 9 is not a blanket pass), and
  `test_the_decided_table_agrees_with_the_live_fleet_on_both_axes`, which pins
  the invariant whose absence let a clean corpus fail.
- **Negative control, run rather than asserted:** reverting only the §5.2
  `stack` cell turned **4** tests red. `design.md` was restored and verified
  byte-identical with `sha256sum -c`.
- Two scenarios added to `specs/identity-and-taxonomy/spec.md`, and §10 ruling 9
  records the correction and supersedes only the stack half of ruling 4. Ruling
  4's `role: deployment` is unchanged, and the census is re-measured at
  `python: 16`, `typescript: 1` — it grew from 12 because the validator set grew,
  and the conclusion does not change with it.

**This change is implemented and still not archived**, as are eight others:
`bind-declared-gate-checks`, `bind-declared-verification`,
`capability-adoption-gate`, `close-unbound-gate-checks`,
`cross-repo-adoption-grant`, `derived-kind-canonical-form`,
`readme-claim-verification`, `spec-purpose-backfill-gate`. Recorded here rather
than archived by this commit, because archiving is a separate decision from
fixing the two failures. `bind-declared-verification` holds only
`rollback-manifest.json` — no proposal, design, tasks or spec delta — and is the
one item `openspec validate --all --strict` reports as failing; it is untracked
and was left untracked, as `bind-declared-gate-checks/tasks.md:21` already
requires and as the entry further down this file already records.

**Left standing, not fixed here: 8 failures from work that landed in this tree
during the session that fixed the two named ones.** Measured 2026-10-05 15:06
with this commit's changes applied: `Ran 800 tests, FAILED (failures=8)` — 7 in
`test_promote_project`, 1 in `test_gate_debt_precondition`. None is caused by
this change; the same 7 fail with this commit's changes stashed. They come from
the in-flight `QUALITY_NEW_CHANGE_WITH_GATE_DEBT` precondition
(`scripts/workspace_check.py` +355, `scripts/gate_debt_baseline.py`,
`gate-debt-baseline.json`, `gate-debt-exceptions.json`, all uncommitted and
untracked at the time of writing), whose new committed input
`gate-debt-baseline.json` is **not** in
`test_promote_project.setup_sandboxed_governance_root`'s copy list, so the rule
fails closed on the sandbox and `promote_project` returns 2. Adding
`"gate-debt-baseline.json"` to that fixture's `for record in (...)` loop is the
one-line remedy. Not done here on purpose: those files belong to that change,
were being written minutes before this commit, and landing them would sweep
another piece of work into this commit. The suite is green for everything this
change owns — `tests.test_identity_and_taxonomy` is **70 passed, 0 failures**
and both originally reported failures now pass.

The prior active change, `derived-kind-canonical-form`, is implemented and
committed at `97f6c68`, **not archived**. It is a one-rule
checker fix: a `kind` outside the frozen 12-value `kinds` vocabulary is now
known when it is the value its own canonical `role`/`stack` derive, so the 17
`KIND_UNKNOWN` warnings the fleet audit reported — every one of them a correct
value — are gone. The four ways of *not* being self-consistent still report at
WARNING, `kinds` stays 12, and no declaration and no sibling repository was
written. See `openspec/changes/derived-kind-canonical-form/` and the evidence
entry below.

The `standalone-project-boundary` change is implemented and archived in
commit `fb5ff5c`. Workspace Governance now ships a fail-closed
standalone-readiness contract: a project may declare a `standalone`
block and an `integrations` array in `.project.json`, and the audit
classifies it as one of six canonical statuses — `standalone`,
`standalone-with-optional-integrations`, `library-dependent`,
`workspace-dependent`, `service-dependent`, `blocked` — without
executing any project command. The Forge governance adapter exposes
the same classification as four additive observation fields
(`standalone_status`, `standalone_observed_revision`,
`standalone_integrations`, `standalone_findings`); existing keys and
exit codes are unchanged. The schema, vocabulary, audit, and adapter
all stay backward compatible: existing declarations without the new
blocks remain valid and report `blocked` with a `STANDALONE_BLOCKED`
warning.

The `shared-postgres-runtime-profile` change is implemented and archived in
commit `d5508cc`. Workspace Governance now ships four `*-postgres-external`
runtime template families (`dotnet-web-postgres-external`,
`rust-web-postgres-external`, `python-web-postgres-external`,
`worker-postgres-external`) that connect an app container to a
supplied PostgreSQL service without starting a database container or volume.
`scripts/runtime_templates.py` now supports `optional_variables`, refuses a
conflicting `!.env*` unignore rule with `SECRET_IGNORE_CONFLICT` before any
write, idempotently amends the root `.gitignore` to ignore `.env`, writes a
blank-password `.env.example`, and records `database_source: external` in the
project declaration. The existing six per-project PostgreSQL container
templates are byte-identical and unchanged.

The `toolchain-decision-register` change is implemented and archived in
commit `27282ee`. Workspace Governance now ships `decisions.json` at the
governance root, a fail-closed `scripts/decisions.py` loader, and a
`workspace_check.py --decisions` summary path. The four toolchain
decisions resolved on 2026-09-30 are seeded with their owner projects,
downstream references, and policy-boundary notes; the D2 public-catalog
exclusion and the D3 capability-registry split are machine-checked by
`tests/test_decisions.py`.

The `repository-discoverability-governance` change is implemented and archived
in commit `1c434b5`. Workspace Governance now audits standard adopted projects
for `LICENSE`, source-backed `.project.json.discoverability`, and separate
GitHub publication evidence. `scripts/init_project.py` performs additive local
repair, while `scripts/github_metadata.py` requires authenticated `gh`,
preserves existing remotes/topics, and supports explicit check/apply/publish
modes without token handling or force-pushes.

The `runtime-template-library-and-renderer` change is implemented and archived
in commit `138844d`. It adds the reusable runtime source library under
`templates/runtime`, six typed Dockerfile/Compose families, and
`scripts/runtime_templates.py` with list/inspect/render/check operations.
Rendering is repository-relative, secret-free, atomic per output, and refuses
existing files unless explicitly named with `--replace`. It records configured
template metadata without changing deployment promotion state. No product
repository, Jenkins consumer, or DriftWatchdog implementation was changed.


The `work-on-main-baseline-rule` change is implemented and archived in
commit `bb4c406` as `2026-10-03-work-on-main-baseline-rule`, and the
canonical spec is `openspec/specs/rules-baseline/spec.md` (+4 added, 2
modified, 0 removed). An agent must now not create a branch or worktree to
do work **unless the user asks for one or designates one**. The rule is one
sentence, byte-identical in `templates/project/.ai-rules/workflow.md` (the
canonical source `init_project.py` copies), `templates/project/AGENTS.md`,
this repository's own `.ai-rules/workflow.md` and `AGENTS.md`, and the
global skill. It is machine-reported as the `work-on-main rule` clause of
`scripts/rules_drift.py`, which moves the fleet report from
`drift_findings=80` to `148` — a delta of exactly 68, none for this
repository.

**That clause enforces nothing, and the spec says so.** `rules_drift.py` is
wired into no gate: `workspace_check.py` imports only `scaffold_handoff`,
and the clause report is invoked by neither `workspace_check.py`,
`auto_gate.py`, nor CI. Under ruling D18, a verifier that no gate runs does
not gate. Wiring it is decision `D5` and the `rules-drift-gate-wiring`
follow-up in `ROADMAP.md`, deliberately a separate change because it turns a
148-finding triage report into a fleet-wide gate in one step. Until it
lands, the work-on-`main` rule is **stated and reported, not enforced**.

## Latest verification evidence

- `bind-declared-gate-checks` (`8e3aecd`) evidence. **This change was resumed,
  not started**: the generator and the spec directory existed uncommitted from an
  aborted session, and the gap was that a 47KB tool with no tests is exactly the
  thing that quietly rots. `tests/test_bind_gate_commands.py` now holds **92
  tests** over `tmp_path`-sized fixture repositories, with one tolerant walk of
  the real 81.

  The tool binds each gate check a repository *already declares* under
  `.ai-gate/gate.yaml` `checks:` to a command derived from what is on disk, and
  refuses to invent one. Measured fleet dry run, unchanged before and after the
  tests:

  | | |
  |---|---|
  | repositories | 81 |
  | RESOLVED | 51 |
  | PARTIAL | 25 |
  | UNRESOLVED | 0 |
  | refused | 0 |
  | NO_MANIFEST | 5 — `chronicleaf` `devloom` `kairovia` `lileililiwen.github.io` `ziban` |
  | unresolved checks | 48 |
  | left in place | 18 |
  | debt record | `<root>/gate-debt.json`, written only under `--apply` |

  The refusals are pinned harder than the successes, because a binder that
  fabricates a command is worse than no binder. **The negative control was run,
  not asserted.** Making `derive` return `python3 -m build` for a pure-Python
  package turned three tests red —
  `AssertionError: 'BOUND' != 'UNRESOLVED'` and
  `AssertionError: ' -m build' unexpectedly found in 'python3 -m build'` — and
  the binder was restored byte-identical before committing.

  Two field errors are locked in by name. **19 repositories use `*.slnx`, not
  `*.sln`**; `SOLUTION_SUFFIXES` is asserted to be `(".sln", ".slnx")` and a
  `.slnx`-only fixture must still produce `dotnet build Foo.slnx`. And
  **`loreMix` is `LoreMix.slnx` while labelled `typescript`** — a label-driven
  binder emits `npm run build` for it. The declared `stack` is therefore not an
  argument of any function in the tool. `FleetTest` walks the real workspace once
  and asserts invariants only, never a count, so it survives fleet churn; one of
  its assertions is that every path a bound command names actually exists in
  that repository.

  Suite: **615 → 707 passed, 155 → 158 subtests passed.** No test was weakened,
  skipped or filtered.

  Two reporting quirks the tests found, reported and **not** fixed, because
  fixing them means editing the generator rather than adding tests. A Python
  repository with only a `pyproject.toml` and no `tests/` directory is labelled
  `unknown` in the debt record's `shape` field, because `Shape.label()` reads
  `python_dirs`, which detection populates only from a test directory. And a
  second `--apply` immediately after the first sees its own writes as `DIRTY`,
  skips those repositories, and so writes a debt record that under-reports —
  two *dry* runs are byte-identical, which is what the tests assert.

  `scripts/bind_verification_command.py` changed only by the two-helper rename
  the generator needs to reuse its YAML editor. The sibling's own tests pass and
  its dry run still reports `BOUND: 0, ALREADY_BOUND: 76, CONFLICT: 0,
  REFUSED: 0`, so no behaviour moved.

  `openspec validate --changes --strict` reports this change valid. The tree's
  one failure is `bind-declared-verification`, an untracked directory from an
  earlier session that holds no `specs/` delta at all. It is not part of this
  change, is not staged by it, and was deliberately left alone.

- `spec-purpose-backfill-gate` (`6de0dd7`) evidence. Archiving a change writes
  `TBD - created by archiving change <name>.` into the `## Purpose` of every spec
  it produced, so a spec whose purpose is the string TBD reads as a finished
  spec. Measured 2026-10-03: 79 repositories carry an `openspec/specs` tree
  holding **1,958** spec files, of which **1,234** across **71** repositories
  still hold the marker — 1,229 in the current form with the trailing
  `Update Purpose after archive.` sentence, 5 in the earlier short form, and 7
  of them with a blank line between the heading and the marker. The archiver is
  third-party (`@fission-ai/openspec`), so the defect is held here.

  `SPEC_PURPOSE_PLACEHOLDER` is **ERROR** and names the spec file relative to
  its repository plus the change the marker records, so the remediation is
  "resolve this spec from this change". It is its own finding-code family, is
  skipped for a repository with no specs tree, and is deliberately not gated on
  `profile_requirements`: a descriptive rule must not become a requirements
  driver.

  The rule is **fenced off the fleet** by `SPEC_PURPOSE_AUDIT_ENABLED = False`,
  a committed repo-relative constant in `scripts/workspace_check.py` following
  the `TAXONOMY_AUDIT_ENABLED` pattern exactly, and it is the only hold — no
  environment variable, no skip flag, no exemption registry. The severity was
  not softened to WARNING to achieve it. Both states are measured on the real
  fleet, not only on a fixture: the audit reports **205 errors** with the fence
  closed and **1,439** with it open, which is 205 plus exactly the 1,234
  markers. The constant is committed back at `False`.

  `scripts/spec_purpose_backfill.py` is the shared owner of the remediation: a
  dry run is its only default, `--apply` is its only write path and is
  all-or-nothing, and every plan row records the source that resolved it. It
  prefers the archived change's own `## Why` prose — the marker holds the **bare**
  change name while the archive directory is **date-prefixed**, so the two are
  joined by stripping `YYYY-MM-DD-`, never by concatenation, which resolves zero
  files — and falls back to a requirement-derived sentence preserved
  byte-for-byte from the `openlearning` prior art. A change name matching two
  archive directories is refused **row-level**, so the other 1,232 rows stay
  reviewable; 1,089 clear the recorded 120-character `## Why` floor.

  Two defects in the recovered `ff33661` checkpoint were fixed. `--check`
  applied the drift refusal, so on a fully applied fleet — where every planned
  marker is legitimately absent — it exited 1 in all three states and could never
  report "applied"; `build_plan` now takes `verify_committed` and `--check`
  passes `False`, so not-applied is 3, applied is 0, and re-applied is
  idempotent at 0. And the marker pattern matched any line *starting* with the
  marker, so a real sentence appended after it was a finding, contradicting its
  own comment and the spec delta; the marker must now be the whole `## Purpose`
  section, with the change name bound to `[\w.-]+` — which a change name
  satisfies and prose cannot. Measured, this matches the same 1,234 fleet files
  and no others.

  **D18 is not satisfied, and this is recorded as a blocker rather than claimed
  as wiring.** The `governance-quality` concern in `driftwatchdog` filters its
  verdict to the closed allow-list `GOVERNANCE_QUALITY_DECLARED_CODES`, which
  holds four codes and excludes this one, and it treats the checker's exit 1 as
  an *expected* exit. With the new-code findings filtered out the concern yields
  `PASS`, so enabling this rule today would turn this repository's CI red while
  the fleet gate reported green. Adding `"SPEC_PURPOSE_PLACEHOLDER"` to that set
  is a separately authorized cross-repo step in a repository this change does not
  own, and `SPEC_PURPOSE_AUDIT_ENABLED` must stay `False` until it lands. The
  change is committed **unarchived** for the same reason: archiving would claim a
  finished gate that does not exist.

  52 new tests. The suite is **553 passing** from 501, with no existing
  assertion weakened; `--self-check` is 0 errors / 0 warnings; the fleet audit
  is unchanged at **205 errors / 18 warnings** with the fence closed;
  `openspec validate spec-purpose-backfill-gate --strict` passes. The 1,234-file
  fleet write is **not applied** — it is a cross-repo source edit requiring
  explicit authorization, exactly like the axis migration — and the 2 ambiguous
  rows are left for an owner to decide by hand.

- `derived-kind-canonical-form` (`97f6c68`) evidence. This is a **checker**
  defect, not 17 portfolio defects: every one of the 17 `KIND_UNKNOWN`
  warnings the fleet audit reported was a *correct* value.
  `identity-and-taxonomy-axis-split` made `kind` a derived, deprecated
  composite, so its authority is the `role`/`stack` pair — and the derivation
  is a product of two enumerated axis sets, 6 × 6 = **36** values, of which
  **27 are absent** from the deliberately frozen 12-value `kinds` list. A
  value that is correct by the current rule is therefore often not in the list,
  so holding a derived value to the list reported a defect no owner could act
  on. `forge` (`rust-platform`), `driftwatchdog` (`rust-tooling`) and this
  repository (`python-governance`) each carried a permanent warning.

  `validate_kind` now asks one more question before reporting: a `kind` outside
  `kinds` is **known** when it equals `derive_kind(role, stack)` with both axes
  present and both canonical. Each precondition is load-bearing, and the four
  ways of *not* being self-consistent all still report at WARNING — a
  hand-authored value that disagrees with its own axes, a one-off value in
  neither form, absent/half-declared/non-canonical axes, and an absent or
  non-string `kind`. `KIND_UNKNOWN` is not repurposed, renamed, or silenced,
  and the level stays WARNING. The axis lookup happens *after* the membership
  test, so a canonical `kind` still reads no axis set at all.

  `kinds` stays 12 and no declaration is written. Extending the list was the
  smaller diff and is ruled out in `design.md` §2: it would need re-extending
  for every future axis combination (the unbounded manual-maintenance point
  already found in `driftwatchdog`'s `GOVERNANCE_QUALITY_DECLARED_CODES`
  allow-list), it would freeze a derived field into a second source of truth,
  and it would break `test_existing_arrays_are_unchanged`, so adopting it means
  weakening a test to make a code change go green. Rewriting the 17
  declarations back to bare role words is rejected for the opposite reason: it
  reintroduces the role/stack conflation the split removed and would trade 17
  `KIND_UNKNOWN` for 17 `TAXONOMY_LEGACY_VALUE`.

  Nine tests pin both sides of the rule. **Verified to bite**: against the
  pre-fix body the two new-behaviour tests fail and the seven
  unchanged-behaviour tests pass, so the fix widens knowledge only where it
  should. The sweep test measures the whole 36-value space and asserts the
  unlisted count is non-zero, so it cannot pass on a vocabulary that already
  covered it.

  Measured: `python3 -m pytest tests` — **501 tests, OK** (492 prior + 9 new);
  fleet audit **errors=205 unchanged, warnings 35 → 18**, `KIND_UNKNOWN`
  **17 → 0**; `workspace_check --self-check` **0 errors / 0 warnings**;
  `openspec validate derived-kind-canonical-form --strict` passes;
  `openspec validate --changes --strict` 6/6; change names valid; `git diff
  --check` clean. The 18 remaining warnings are `HANDOFF_SCAFFOLD` 8,
  `DEPLOYMENT_PROMOTION_STALE` 7, `CAPABILITY_BLOCKED` 2,
  `DISCOVERABILITY_INVALID` 2, `CI_MISSING` 2,
  `QUALITY_README_CLAIM_UNSCOPED` 1 — none is a `KIND_UNKNOWN`, and no finding
  other than the 17 cleared ones moved. Spec delta MODIFIES the existing
  `Canonical kinds are enforced` requirement in
  `openspec/specs/portfolio-vocabulary/spec.md`; `identity-and-taxonomy` is not
  a target because that capability spec is still unarchived and its derived-kind
  requirement is unchanged by this fix. **Not archived, by instruction**, and
  `identity-and-taxonomy-axis-split` is likewise left unarchived.

  Evidence boundary: this change proves the checker no longer rejects a
  self-consistent derived value, and that it still rejects everything else. It
  does not prove that a repository's `kind` *means* anything — the axes remain
  descriptive and drive no required file, CI requirement, verification command,
  or evidence, deployment, or promotion state.

- `readme-claim-verification` (`f8df5ea`) evidence. A README status block is
  now checked against the tree. `QUALITY_README_CLAIM_CONTRADICTED` is ERROR
  and `QUALITY_README_CLAIM_UNSCOPED` is one aggregate coverage finding per
  run. `python3 -m unittest discover -s tests` — 489 tests, 0 failures (456
  prior + 33 new); `workspace_check --self-check` 0/0; `auto_gate --self-check`
  PASS; `check_skill_refs` ok; `openspec validate --all --strict` 18/18;
  `rules_drift` unchanged at 148; `jenkins_manifest --check` projects=0
  errors=0; `git diff --check` clean. At that commit the fleet audit moved
  `errors=211 warnings=17` → `errors=215 warnings=18`: +4 `CONTRADICTED`
  (argoset:31, care-bridge:17, retake-kit:42, devloom:9) and +1 aggregate
  `UNSCOPED` naming 3 statements. No other code changed count. **That +4 was
  itself a defect and is corrected at `833ca9c` below** — read the two numbers
  together, not the first alone.
  Read-only proved by hashing 17 real trees before and after a claim run.
  **The design's 7-repository corpus is stale and the change says so**: 6 of
  the 7 (`rostera`, `aesthra`, `reelio`, `pluggify`, `testify`,
  `shopifireman`, `care-bridge` were repaired 2026-10-03) now carry accurate
  claims.
  **The fleet is NOT red — the checker was wrong, and `833ca9c` fixed it.** The
  four `CONTRADICTED` findings recorded above were false positives, and the
  repair is in the check rather than in any README. The `deployment` evidence
  rule read the tree before the declaration, so a local `compose*.y(a)ml`
  counted as deployment evidence although all four repositories declare
  `deployable: false` (`devloom` holds a Compose *and* a `Dockerfile`, both
  local-only). The `application-source` synonyms carried bare `source`, so
  argoset's "live source adapters for named platforms" — provider language —
  resolved to the application-source surface. Both rules are narrowed, and
  neither fix blunts the check: rostera's original wording still yields its
  `build` and `ci` contradictions, and a repository declaring
  `deployable: true` while holding a Compose file is still a contradiction;
  both directions are pinned by regression tests.
  **Fleet audit is now `errors=211 warnings=18`** — the `errors=211`
  pre-change baseline exactly, with the four false-positive ERRORs gone. The
  added warning is the aggregate `QUALITY_README_CLAIM_UNSCOPED` naming 3
  statements that name no resolvable surface; it is a coverage metric, not an
  accusation, and it is meant to persist. Those four repositories need no
  README repair, and the repair queue in `tasks.md` §5.1 is withdrawn: editing
  an accurate document into a false one to satisfy a wrong rule is the
  failure this check exists to catch. Re-verified at `833ca9c`: 492 tests,
  0 failures (489 prior + 3 new regression tests), self-check 0/0, auto-gate
  PASS, drift unchanged at 148, `openspec validate --all --strict` 18/18.
  Nothing here gates on the check yet — binding it as a driftwatchdog gate
  check is deferred to that repository.

- `identity-and-taxonomy-axis-split` evidence. `role` and `stack`
  are now independent axes; `kind` is the derived, deprecated composite
  `<stack>-<role>`, or the bare `<role>` when stack is `none`. Three new codes:
  `TAXONOMY_MISMATCH` (ERROR), `TAXONOMY_LEGACY_VALUE`, `TAXONOMY_AXIS_UNKNOWN`
  (WARNING). **The migration has now been applied and the fleet committed**:
  81/81 declarations and 81/81 `projects.json` entries carry both axes;
  `argoscope`/`chronicleaf`/`devloom`/`kairovia` are registered as
  `product`/`dotnet` and `jenkins-bootstrap` is gone. From `/home/paul/code`
  the fleet audit moved **211 → 206 errors** (`errors=206 warnings=35`), with
  **zero** findings in any `TAXONOMY_*` family and `RULES_DRIFT_NEW` 0.
  **The check now enforces.** `TAXONOMY_AUDIT_ENABLED = True`; the flag is a
  committed constant, not an environment variable, and both of its states stay
  tested — held off, the same mismatched fixture is silent; on, it reports ERROR
  `TAXONOMY_MISMATCH`. `python3 scripts/axis_migration.py --check` exits 0.
  All 81 declarations satisfy `kind == derive_kind(role, stack)`, which is why
  `TAXONOMY_LEGACY_VALUE` is 0; the 13 `RULES_DRIFT_NEW` errors the four new
  registrations surfaced were cleared by adding the missing canonical
  `.ai-rules` paragraphs to those repositories, **not** by re-cutting the
  rules-drift baseline.
  `python3 -m unittest discover -s tests` — **492 tests, OK**;
  `openspec validate identity-and-taxonomy-axis-split --strict` passes;
  `git diff --check` clean. Three rulings were added during implementation, all
  in `design.md` §10: the migration also writes the derived `kind`, the drift
  guard consequently accepts the derived form so the tool stays idempotent, and
  `platform-rust` was a spec typo corrected to `rust-platform`. Two of those
  were owner rulings against the implementation as first written.
  Two things were **not** clean, both recorded in `tasks.md` §5 notes 7 and 8
  rather than fixed in passing: `workspace_check --self-check` was 1 error /
  1 warning (`devloom`'s non-canonical `lifecycle: scaffold`, now visible
  because the repository is registered; and this repository's own derived
  `python-governance` `kind`, which is absent from the deliberately
  byte-identical `vocabulary.json` `kinds` array), and
  `rollback-manifest.json` maps 77 of the 80 migrated siblings —
  `aegify`, `argoscope` and `argoset` have no before/after SHA pair, so a
  manifest-driven rollback would skip them.
  **Both of the self-check's two items are now clear at `97f6c68`**
  (`derived-kind-canonical-form`): `devloom` is registered `active`, and the
  self-check reads **0 errors / 0 warnings**. The `python-governance` warning
  was a checker defect — a correct derived value held to the frozen 12-value
  `kinds` list — not a declaration defect, so no portfolio file was written.
  `rollback-manifest.json` is extended to all 81 repositories at `4b6f49c` and
  is no longer outstanding.

- `rules-drift-gate-wiring` (`4a9edfc`) evidence. Archived as
  `2026-10-03-rules-drift-gate-wiring`; canonical spec
  `openspec/specs/rules-baseline/spec.md` (+4 added, 2 modified, 0 removed).
  The clause that `work-on-main-baseline-rule` added is now **enforced**, not
  merely reported. `rules-drift-baseline.json` holds the 140 clause-level gaps
  across 72 repositories; `workspace_check` emits ERROR `RULES_DRIFT_NEW` for
  any gap whose `(project, file, label)` is absent from it, and WARNING
  `RULES_DRIFT_BASELINE_STALE` when an entry is no longer reported. Of the
  148 total drift findings, 140 are clause-level and 8 are
  `HANDOFF_SCAFFOLD`, which is a different path and is not ratcheted.
  Measured: fleet audit **unchanged** at `errors=211 warnings=17` with zero
  `RULES_DRIFT_*` findings, and `rules_drift --check` still reports 148.
  `python3 -m unittest discover -s tests` — 389 tests, 0 failures (380 prior +
  9 new); `openspec validate --all --strict` 18/18 post-archive;
  `workspace_check --self-check` 0/0; `auto_gate --self-check --no-deployment`
  PASS; `check_skill_refs` ok; change names valid; `git diff --check` clean.
  Two implementation bugs were caught by the tests and are recorded in the
  commit: the stale-baseline comparison was reading a single-repository
  `--self-check` as if it were a fleet scan, and a fixture's stub rule files
  (`"w"` and `"c"`) read as six genuine clause gaps. Both fixed, and the
  fixture now loads the real shipped rule files so it cannot rot.
  The evidence boundary: this change proves the baseline is loaded fail-closed,
  that baselined debt does not block, and that unbaselined drift does. It
  cannot prove a repository's rule files are *read* by an agent, only that
  they are present and machine-checkable.

- `work-on-main-baseline-rule` (`bb4c406`) evidence:
  `python3 -m unittest discover -s tests` — 380 tests, 0 failures
  (376 prior + 4 new in `tests/test_rules_drift.py`: the clause reported
  when absent, absent when present, the opt-out marker suppressing it with
  the file's bytes unchanged, and both templates carrying the rule *and* its
  user-asks exception; plus 1 new test in `tests/test_decisions.py` keeping
  the 2026-09-30 date guarantee for the four seeded entries);
  `python3 scripts/workspace_check.py --self-check` — 0 errors, 0 warnings;
  `python3 scripts/auto_gate.py --self-check --no-deployment` — PASS;
  `python3 scripts/check_skill_refs.py` — `SKILL.md + 7 references` valid;
  `node scripts/check-openspec-change-names.mjs` — valid;
  `openspec validate --all --strict --no-interactive` — 18 passed, 0 failed
  post-archive (the change is archived and its delta merged into
  `openspec/specs/rules-baseline/spec.md`);
  `python3 scripts/rules_drift.py --root .. --check` — `drift_findings=148`,
  68 of them `work-on-main rule`, none for `workspace-governance`;
  `git diff --check` — clean before the handoff-only update. The canonical
  spec diff is purely additive: the `MUST NOT modify any project file`
  guarantee and the `<!-- workspace-governance:rules-customized -->` opt-out
  sentence are both intact. A 240-file sha256 snapshot across the whole
  fleet proves only this repository's own `AGENTS.md` and
  `.ai-rules/workflow.md` changed and **zero sibling files were touched**;
  `scripts/rules_drift.py` is a clause-only diff with no new environment
  variable, exemption registry or skip path. The first `openspec archive`
  run **aborted without writing**, because the delta was filed under a
  capability that did not exist; re-filing it under `rules-baseline` is why
  the archive reports `+4 added, ~2 modified, -0`.

- `python3 -m unittest discover -s tests -v` — 253 tests, 0 failures
  (217 prior + 36 new in `tests/test_standalone_project_boundary.py`:
  the six canonical statuses, the absolute-path and `..` escape
  rejections, optional and required integration branches, secret
  redaction, the bounded static scan, the adapter's new fields, the
  read-only guarantee, and the vocabulary loader).
- `python3 scripts/workspace_check.py --self-check` — 0 errors, 0 warnings
  (the governance repo carries no `standalone` block, so the
  audit is unchanged for it).
- `python3 scripts/auto_gate.py --self-check --no-deployment` — PASS.
- `python3 scripts/jenkins_manifest.py --check` — 0 projects, 0 errors
  (the standalone classification does not promote `deployable`).
- `node scripts/check-openspec-change-names.mjs` — valid.
- `openspec validate --all --strict --no-interactive` — 14 passed,
  0 failed (13 canonical specs, 1 active change; the
  `standalone-project-boundary` change is archived and now lives
  under `openspec/specs/`).
- `git diff --check` — clean before the handoff-only update.
- Portfolio audit (`--root .. --audit --json`) is unchanged in shape:
  211 errors and 17 warnings, with no new project-level finding
  codes introduced by this change. The `STANDALONE_*` codes only
  fire on declarations that opt in, and no adopted project in this
  workspace has opted in.
- `python3 scripts/workspace_check.py --self-check` — 0 errors, 0 warnings.
- `python3 scripts/workspace_check.py --decisions` — prints D1–D4 summary;
  `--json` produces a parseable document with `{id,title,status,date}` per
  entry.
- `python3 scripts/workspace_check.py --root .. --audit --json` — same 211
  errors / 17 warnings shape as before; no new project-level finding codes
  introduced by this change. The +4 errors / -1 warning vs the prior
  HANDOFF baseline is pre-existing sibling-repo drift, not from this
  change.
- `python3 scripts/runtime_templates.py list` — ten version-one template
  families (six container-backed, four external) listed from the registry.
- `node scripts/check-openspec-change-names.mjs` — valid.
- `openspec validate --all --strict --no-interactive` — 14 passed, 0 failed
  (12 canonical specs, 1 active change, `external-postgres-runtime-profile`
  archived and now lives under `openspec/specs/`).
- `python3 scripts/auto_gate.py --self-check --no-deployment` — PASS.
- `git diff --check` — clean before the handoff-only update.

Prior evidence (package 5, `post-mvp-readiness`):

- `python3 -m unittest discover -s tests` — 167 tests, 0 failures.
- `python3 scripts/check_skill_refs.py` — `SKILL.md + 7 references` valid.
- `gh auth status` — authenticated account `lileililiwen`.
- `gh repo create` created `https://github.com/lileililiwen/workspace-governance`,
  `main` was pushed through `origin`, and
  `python3 scripts/github_metadata.py . --check --json` reports
  `metadata_verified` with no differences. The local declaration records the
  verified GitHub publication state.
- Portfolio audit `python3 scripts/workspace_check.py --root .. --audit
  --json` — 207 errors and 18 warnings, intentionally exposing migration work:
  57 `LICENSE_MISSING`, 75 `DISCOVERABILITY_MISSING`, and 75
  `PUBLICATION_UNVERIFIED`, plus the pre-existing handoff/deployment and
  capability warnings.
- `python3 scripts/jenkins_manifest.py --check --root ..` — blocked by the
  same newly exposed portfolio metadata gaps; no deployment manifest changed.
- `python3 scripts/runtime_templates.py list` — six version-one template
  families listed from the registry.
- Runtime template tests — all six families rendered; generated Compose files
  passed `docker compose config` in the available Docker environment.
- `python3 scripts/workspace_check.py --self-check` — 0 errors, 0 warnings
  after adding deployment-template metadata validation.
- `openspec validate --changes --strict --no-interactive` — 1 passed, 0 failed
  before archive; the archived and canonical specs are now present.

Six changes shipped in sequence.

**1. `registry-and-declaration-integrity`** (archived
`openspec/changes/archive/2026-09-26-registry-and-declaration-integrity/`,
canonical spec `openspec/specs/registry-integrity/spec.md`). Registered the 11
discovered declarations, corrected six declaration identity/format defects,
created four missing declarations, added duplicate id/path guards, derived and
enforced the canonical project id in `init_project.py`, and made
`maturity_audit.py` report the authoritative `workspace_check` counts.
Unregistered discovery is now an ERROR via
`discovery.unregistered_policy: "fail"`.

**2. `shared-rules-single-source`** (archived
`openspec/changes/archive/2026-09-26-shared-rules-single-source/`, canonical
spec `openspec/specs/rules-baseline/spec.md`). Made `templates/project/**` the
only source of the shared rules and had `init_project.py` read it from disk,
deleting the duplicate embedded copy that had drifted from the on-disk
templates. Added `scripts/rules_drift.py`, a **non-destructive** clause-level
drift report with no `--apply`, and surfaced scaffold `HANDOFF.md` files from
the audit as `HANDOFF_SCAFFOLD`. Created `crossalheart`'s missing rules,
clearing the workspace audit's last two errors.

**3. `portfolio-vocabulary-normalization`** (archived
`openspec/changes/archive/2026-09-27-portfolio-vocabulary-normalization/`,
canonical spec `openspec/specs/portfolio-vocabulary/spec.md`). Added
`vocabulary.json` as the single machine-readable source for the 15 canonical
profiles, 12 canonical kinds, placeholder markers, and secret-field
substrings. `workspace_check.py` enforces `PROFILE_UNKNOWN` (ERROR),
`KIND_UNKNOWN` (WARNING), and `PROFILE_DOC_UNKNOWN` (ERROR) from it and exits
2 with `VOCABULARY` when it is missing or unusable; `product_code_quality.py`
defaults its markers from it while keeping per-project overrides;
`maturity_audit.py` reports the vocabulary version. Added the 9 missing
`profiles/*.json` documents and remapped 19 sibling declarations with
non-canonical `kind`/`profile` values (left uncommitted in their own
repositories, alongside the earlier declaration/rules edits).

**4. `governance-front-door`** (archived
`openspec/changes/archive/2026-09-27-governance-front-door/`, canonical spec
`openspec/specs/governance-front-door/spec.md`). Shipped
`skills/workspace-governance/SKILL.md` — one auto-triggering entry whose
routing table sends each governance situation to a per-concern reference —
plus six references that link owning scripts and canonical specs instead of
restating policy. Added `scripts/check_skill_refs.py`, which fails naming the
reference and the missing path when a cited path or command does not exist,
with `tests/test_skill_refs.py` covering the valid tree, the missing-script
negative, routing resolution, the safe default, and the
no-destructive-instructions boundary. Documented the manual install in
`README.md`. No checker, policy, spec, template, or sibling repository was
changed.

**5. `post-mvp-readiness`** (archived
`openspec/changes/archive/2026-09-27-post-mvp-readiness/`, canonical spec
`openspec/specs/readiness/spec.md`). Docs-only readiness for the shared
governance owner: a consolidated README Usage section with one copy-paste
example per command (every flag verified against the shipped `--help`;
the Forge adapter documents its stdin/stdout contract), a redacted
checked-in capture `docs/assets/terminal-self-check.txt` showing a real
`--self-check` (0 errors, 0 warnings) and `--audit --json` (0 errors,
16 warnings with the 9/7 breakdown) run plus one labelled illustrative
finding, an explicit screenshots-not-applicable note (CLI-only), and a
single vocabulary entry point (`docs/vocabulary.md` plus a README
section) that links the canonical sources and states the
intent-vs-evidence invariant. Also repaired the stale
`docs/package-backlog.md` dependency order (now records 1, 2, 3, 8
shipped). No script, checker, schema, template, registry, promotion,
or spec-behavior change; the pre-existing dirty `.project.json` and
untracked `MATURITY_PROGRESS_SUMMARY.md` were deliberately left
unstaged.

The read-only **Forge governance adapter**
(`scripts/forge_governance_adapter.py`) is unchanged; its canonical spec is
`openspec/specs/forge-governance-adapter/spec.md`.

**7. `shared-postgres-runtime-profile`** (archived
`openspec/changes/archive/2026-10-01-shared-postgres-runtime-profile/`,
canonical spec `openspec/specs/external-postgres-runtime-profile/spec.md`).
Adds four external-PostgreSQL runtime template families
(`dotnet-web-postgres-external`, `rust-web-postgres-external`,
`python-web-postgres-external`, `worker-postgres-external`) that connect an
app container to a supplied PostgreSQL service without starting a database
container, image, volume, or provisioning command. `runtime_templates.py`
gains `optional_variables` support (e.g. `db_port` defaulting to `5432`),
refuses a `!.env*` unignore rule with `SECRET_IGNORE_CONFLICT` before any
write, idempotently amends the root `.gitignore` to ignore `.env`, and
records `database_source: external` in the project declaration. The
generated `.env.example` has a blank `PGPASSWORD`; the compose file reads
`PGHOST`/`PGPORT`/`PGUSER`/`PGDATABASE`/`PGPASSWORD` from the runtime
environment and never substitutes a password. The deployment schema gains
`database_source` (`container` | `external`); the existing six per-project
container-backed templates are byte-identical. The `runtime-template-renderer`
spec was extended with external-profile scenarios; the canonical
`external-postgres-runtime-profile` spec captures the new contract. No
sibling repository, profile, capability schema, promotion-ledger, Jenkins
consumer, or DriftWatchdog implementation was changed.

**6. `toolchain-decision-register`** (archived
`openspec/changes/archive/2026-10-01-toolchain-decision-register/`,
canonical spec `openspec/specs/workspace-decision-register/spec.md`).
Adds `decisions.json` at the governance root, a fail-closed
`scripts/decisions.py` loader mirroring the vocabulary discipline, and a
`workspace_check.py --decisions` summary path. `workspace_check.py`
self-check reports `DECISIONS_REGISTER_MISSING` as ERROR when the file
is absent; portfolio audits emit a single `DECISIONS_REGISTER_ABSENT`
WARNING; broken shapes and unknown registry references are always
errors. Seeded with the four accepted toolchain decisions resolved on
2026-09-30 (D1 agent-runtime split, D2 self-hosted Zitadel with the
public-catalog exclusion restated in `policy_boundary`, D3
capability-registry home split with schema=platform-contracts and
instances=workspace-governance, D4 crates.io publication). The D2
exclusion and the D3 split are asserted by string in
`tests/test_decisions.py`. `docs/toolchain-decisions.md` is the human
view; `docs/capabilities.md` records the D3 ownership note. No
sibling repository, runtime template, profile, capability schema, or
promotion-ledger was changed; the public-site boundary in D2 is
restated from the root ownership table and not weakened.

**7. `standalone-project-boundary`** (archived
`openspec/changes/archive/2026-10-01-standalone-project-boundary/`,
canonical spec `openspec/specs/standalone-project-boundary/spec.md`).
Adds a fail-closed standalone-readiness contract: a project may declare
a `standalone` block and an `integrations` array in `.project.json`,
and the audit classifies it as one of six canonical statuses —
`standalone`, `standalone-with-optional-integrations`,
`library-dependent`, `workspace-dependent`, `service-dependent`,
`blocked` — without executing any project command. The schema adds
optional `standalone` and `integrations` blocks plus `$defs.standalone_status`
and `$defs.integration`; existing declarations remain valid (absent
block ⇒ `blocked` + `STANDALONE_BLOCKED` warning, never a pass).
`vocabulary.json` gains `standalone_statuses` (6 values) and
`integration_required_states` (2 values), and the loader fails closed
on missing, empty, non-array, or duplicate values. `workspace_check.py`
adds `validate_standalone` and `classify_standalone` plus 12 finding
codes (`STANDALONE_BLOCKED`, `STANDALONE_STATUS_INVALID`,
`STANDALONE_SHAPE`, `STANDALONE_ABSOLUTE_PATH`,
`STANDALONE_PATH_ESCAPE`, `STANDALONE_REQUIRED_SIBLING`,
`STANDALONE_REQUIRED_SERVICE`, `STANDALONE_OPTIONAL`,
`STANDALONE_INTEGRATION_PENDING`, `STANDALONE_EVIDENCE_MISSING`,
`STANDALONE_SECRET_VALUE`, `STANDALONE_DETECTED_SIBLING`). The
bounded static scan reads only `Cargo.toml`, `package.json`,
`pyproject.toml`, and `go.mod`; it never executes the project and
never overrides the declared status. The Forge governance adapter
exposes the same classification as four additive observation fields
(`standalone_status`, `standalone_observed_revision`,
`standalone_integrations`, `standalone_findings`); existing keys,
status mappings, and exit codes are unchanged, and
`build_standalone_observation` never raises. No sibling repository,
runtime template, profile, capability schema, promotion-ledger,
Jenkins consumer, or DriftWatchdog implementation was changed.

## Authored, not yet implemented

Four packages are fully authored as OpenSpec changes and are ready to implement
in a fresh conversation. Each lives in the repository that owns the work:

- `driftwatchdog/openspec/changes/gate-evidence-export/` (package 4).
- `dotnet-platform-libs/openspec/changes/platform-consumer-bootstrap/` (package 5).
- `rust-platform-libs/openspec/changes/rust-platform-consumer-baseline/` (package 6).
- `platform-contracts/openspec/changes/contracts-consumer-parity/` (package 7).

`docs/package-backlog.md` is the index and the coordination rules; the detail
lives in each change directory, so a package has exactly one source of truth.

## Evidence

- Package 12 (`standalone-project-boundary`) evidence:
  `python3 -m unittest discover -s tests` — 253 tests, 0 failures
  (217 prior + 36 new in `tests/test_standalone_project_boundary.py`:
  the six canonical statuses, the absolute-path and `..` escape
  rejections, optional/required integration branches, secret
  redaction, the bounded static scan, the adapter's new fields, the
  read-only guarantee, and the vocabulary loader);
  `python3 scripts/workspace_check.py --self-check` — 0 errors, 0 warnings
  (the governance repo carries no `standalone` block, so the audit
  is unchanged for it);
  `python3 scripts/auto_gate.py --self-check --no-deployment` — PASS;
  `python3 scripts/jenkins_manifest.py --check` — 0 projects, 0 errors
  (the standalone classification does not promote `deployable`);
  `node scripts/check-openspec-change-names.mjs` — valid;
  `openspec validate --all --strict --no-interactive` — 14 passed,
  0 failed (13 canonical specs, 1 active change;
  `standalone-project-boundary` archived and now lives under
  `openspec/specs/standalone-project-boundary/spec.md`);
  `git diff --check` — clean before the handoff-only update.
  The portfolio audit (`--root .. --audit --json`) is unchanged in
  shape: 211 errors and 17 warnings, with no new project-level
  finding codes introduced by this change (the `STANDALONE_*` codes
  only fire on declarations that opt in, and no adopted project in
  this workspace has opted in). The vocabulary loader now
  fail-closes on missing, empty, non-array, or duplicate
  `standalone_statuses` and `integration_required_states` (asserted
  by `tests/test_standalone_project_boundary.py::VocabularyStandaloneTests`).
  The Forge governance adapter always emits the four new fields
  alongside the existing keys; existing keys, status mappings, and
  exit codes are unchanged (asserted by
  `tests/test_forge_governance_adapter.py`); secret-shaped values
  in `standalone` and `integrations` fields are replaced by
  `[redacted]` in evidence lines, and the read-only guarantee is
  preserved (asserted by
  `tests/test_standalone_project_boundary.py::AdapterStandaloneObservationTests`).
  No sibling repository, runtime template, profile, capability
  schema, promotion-ledger, Jenkins consumer, or DriftWatchdog
  implementation was changed.

- Package 11 (`shared-postgres-runtime-profile`) evidence:
  `python3 -m unittest discover -s tests` — 217 tests, 0 failures
  (204 prior + 13 new in `tests/test_runtime_templates.py`: four
  `*-postgres-external` template metadata and rendering tests, an
  idempotence test for `.gitignore`, a `SECRET_IGNORE_CONFLICT` test
  for the unignore rule, a `TARGET_EXISTS`-before-`.gitignore` test
  for existing `compose.yaml`, a `db_port` default test, a
  secret-shaped-variable rejection test, and a container/internal
  template regression test);
  `python3 scripts/workspace_check.py --self-check` — 0 errors, 0 warnings;
  `python3 scripts/auto_gate.py --self-check --no-deployment` — PASS;
  `python3 scripts/jenkins_manifest.py --check` — 0 projects, 0 errors;
  `python3 scripts/runtime_templates.py list` — ten version-one
  template families (six container-backed, four external);
  `node scripts/check-openspec-change-names.mjs` — valid;
  `openspec validate --all --strict --no-interactive` — 14 passed, 0 failed
  (12 canonical specs, 1 active change; `shared-postgres-runtime-profile`
  archived and now lives under
  `openspec/specs/external-postgres-runtime-profile/spec.md`);
  `git diff --check` — clean before the handoff-only update. The portfolio
  audit (`--root .. --audit --json`) is unchanged in shape: 211 errors and
  17 warnings, with no new project-level finding codes introduced by this
  change (the +4 errors / -1 warning vs the prior HANDOFF baseline is
  pre-existing sibling-repo drift, not from this change). All four new
  external templates rendered end-to-end and passed `docker compose config`
  with a dummy `.env` (verified by `check_target`); the existing six
  per-project container-backed templates remained byte-identical to their
  pre-change bytes (verified by `git diff` against `HEAD~`); no password
  or secret-shaped value was ever supplied as a renderer argument, written
  to `.env.example`, or stored in `.project.json`; the renderer refuses
  before any file is written when the root `.gitignore` contains a
  `!.env*` rule or an existing `compose.yaml`/`Dockerfile` is not listed
  via `--replace`.

- Package 10 (`toolchain-decision-register`) evidence:
  `python3 -m unittest discover -s tests` — 204 tests, 0 failures
  (167 prior + 37 new in `tests/test_decisions.py`);
  `python3 scripts/workspace_check.py --self-check` — 0 errors, 0 warnings;
  `python3 scripts/workspace_check.py --decisions` — prints D1–D4; `--json`
  produces a parseable document with `{id,title,status,date}` per entry;
  `python3 scripts/auto_gate.py --self-check --no-deployment` — PASS;
  `node scripts/check-openspec-change-names.mjs` — valid;
  `openspec validate --all --strict --no-interactive` — 14 passed, 0 failed
  (10 canonical specs, 4 active changes; `workspace-decision-register`
  archived to `openspec/specs/workspace-decision-register/spec.md`);
  `git diff --check` — clean before the handoff-only update. The portfolio
  audit (`--root .. --audit --json`) is unchanged in shape: 211 errors and
  17 warnings, with no new project-level finding codes introduced by this
  change (the +4 errors / -1 warning vs the prior HANDOFF baseline is
  pre-existing sibling-repo drift, not from this change). The D2 public-
  catalog exclusion and the D3 capability-registry split are asserted by
  string in `tests/test_decisions.py`; the seeded downstream references
  all resolve to live registry ids.

- Package 9 (`post-mvp-readiness`) evidence:
  `python3 -m unittest discover -s tests` — 148 tests, 0 failures;
  `python3 scripts/workspace_check.py --self-check` — 0 errors, 0 warnings;
  `python3 scripts/workspace_check.py --root .. --audit --json` — 0 errors,
  16 warnings (9 `HANDOFF_SCAFFOLD`, 7 `DEPLOYMENT_PROMOTION_STALE`);
  `python3 scripts/jenkins_manifest.py --check --root ..` — 7 projects,
  0 errors; `python3 scripts/auto_gate.py --self-check --no-deployment` —
  PASS; `node scripts/check-openspec-change-names.mjs` — valid;
  `openspec validate --all --strict --no-interactive` — 9 passed, 0 failed
  (9 canonical specs, 0 active changes); `git diff --check` — clean.
  Every documented Usage command runs `--help` (adapter: stdin contract);
  every new README/docs relative link resolves on disk; no external image
  host; capture redacted and reproducible offline.
- Package 8 evidence still stands:
  `python3 scripts/check_skill_refs.py` — `skill refs ok: SKILL.md + 6 references`.
- `python3 -m unittest discover -s tests` — 148 tests, 0 failures (140 prior + 8 new in `tests/test_skill_refs.py`).
- `python3 scripts/workspace_check.py --self-check` — 0 errors, 0 warnings (unchanged).
- `python3 scripts/workspace_check.py --root .. --audit --json` — **0 errors**,
  16 warnings (9 `HANDOFF_SCAFFOLD`, 7 `DEPLOYMENT_PROMOTION_STALE`; unchanged
  by this docs-only change).
- `node scripts/check-openspec-change-names.mjs` — valid;
  `openspec validate --all --strict --no-interactive` — 9 passed, 0 failed
  (8 canonical specs, 1 active change).
- `git diff --check` — clean.
- Every cited `python3 scripts/*.py` command runs `--help` successfully
  (workspace_check, init_project, auto_gate, product_code_quality,
  maturity_audit, jenkins_manifest, rules_drift, check_skill_refs).
- Package 3 evidence still stands (140-test baseline, 0/0 self-check,
  0-error portfolio audit, vocabulary version 1, quality PASS, Jenkins
  manifest 7 projects 0 errors, auto-gate PASS, adapter observations).
- Commit `7e1bf63` was the pre-work HEAD; package 8 implementation is the
  first commit after it, followed by this HANDOFF-only commit.

## Portfolio impact observed

The `.ai-rules` baseline change is deliberately non-destructive. A first
implementation made whole canonical paragraphs mandatory and shipped `--apply`;
running it appended a duplicate canonical block to **60 project files**,
including well-maintained ones such as `mewo` whose text already expressed the
same rules. That was measured, judged a regression, and reverted byte-for-byte
before the change was re-scoped to a report-only clause check. The portfolio
`git diff` for `.ai-rules` is clean apart from `crossalheart`'s newly created
files.

9 adopted projects still carry scaffold `HANDOFF.md` bodies (reported as
`HANDOFF_SCAFFOLD`; two products recorded real handoffs since 2026-09-26).
The 7 `DEPLOYMENT_PROMOTION_STALE` warnings remain triaged:
re-promotion was not performed because it would record a deployable decision at
the current revision without a new release.

Sibling repositories still hold uncommitted declaration, rules, and vocabulary
remap files created by the first three changes (the 10 declarations plus
`crossalheart`'s rules and `.ai-gate`, plus 19 `kind`/`profile` remaps);
they were left uncommitted in their own repositories. Package 8 touched no
sibling repository.

## Next action

1. **`bind-declared-gate-checks` is implemented, tested, validated, and
   partly closed; still deliberately not archived.** The fleet write landed
   and `gate-debt.json` was regenerated against it.

   | Measurement | Before | After |
   |---|---|---|
   | `governance-quality` UNBOUND across the fleet | 41 | **0** |
   | Debt record, unresolved checks | 168 | **127** |
   | Debt record, repositories carrying debt | 59 | **54** |
   | Debt record vs the gate's own unbound set | equal | **equal (127 = 127)** |
   | `python3 -m pytest tests -q` | 725 passed | **734 passed**, 158 subtests, 0 failed |

   The 127 that remain are 80 `placeholder-threshold` / `product-code-boundary`
   pairs (40 each) plus 47 shape refusals. Every one names the file and key
   whose absence caused it — for the product-quality pair, the `quality` block
   missing from that repository's own `.project.json`, and the checker's exit-2
   behaviour without it.

   **The `checks:` boundary moved, and this is the design call to review.** The
   binder used to refuse to touch `checks:` at all, so a repository naming
   `profile: product` was failed by the gate for three unbound checks it could
   never close. That guarded the wrong boundary: the gate enforces one rule —
   `commands:` must not name a check the manifest does not select
   (`driftwatchdog/src/gate/aigate.rs:213`) — not "`checks:` is never written".
   The binder now writes both halves in one operation, and only when a checker
   is reachable; where none is, neither half is written, because a selection
   with no command is a worse state than the gap. The spec amendment says so
   plainly and names the test that guarded the wrong boundary.

   **Both command flags are load-bearing, and dropping either is a silent
   wrong answer.** Without `--root ..` the checker defaults to this
   repository and reports 81 false `PROJECT_MISSING` findings. Without
   `--project <repo>` it audits the whole workspace, and the gate's concern
   filters findings by **code, not project** — measured on this fleet, that
   charges `bargora` for 12 findings of which 0 are its own (4 from
   `chronicleaf`, 3 from `metiscope`, 3 from `openlearning`, 1 from
   `dotnet-platform-libs`). Scoped, the same repository reads PASS.

   **Re-measured on real gate runs, not dry runs.** The 8 repositories whose
   only failure was these bindings (`bargora`, `crossalheart`, `dharmatlas`,
   `hypora`, `mnemyx`, `mortalect`, `namevia`, `triplanify`) all read
   `governance-quality: PASS` after the binding, and each is blocked only by
   the two product-quality concerns that have no policy to run. All 76
   manifests were checked for the invariant that matters: **0** `commands:`
   entries name a check the manifest does not select.

   **Not done, on purpose.** No `quality` block was written anywhere, so the
   80 product-quality checks stay unbound — `product_roots`, `languages` and
   `placeholder_threshold` are per-repository owner decisions and 79 of 81
   repositories have not written one. `forge_governance_adapter.py` remains
   unbindable by construction (it reads stdin; the gate gives the child
   `Stdio::null()`) and is not wired. `README.md` is still not updated
   (3.7). Nothing was pushed; all 40 fleet commits are local on `main`.
2. Archive `derived-kind-canonical-form` and `identity-and-taxonomy-axis-split`
   when the owner is ready. Both are implemented, committed, and validated
   strictly; neither is archived. Archiving the first folds the MODIFIED
   `Canonical kinds are enforced` requirement into
   `openspec/specs/portfolio-vocabulary/spec.md`, and archiving the second is
   what finally lands the `identity-and-taxonomy` capability spec. Archiving
   them in that order keeps the derived-kind requirement on `main` from being
   split across two histories.
3. `spec-purpose-backfill-gate` (`6de0dd7`) is implemented, tested, and
   validated, and is deliberately **not archived**: the fence is shut and the
   gate-wiring dependency is unmet. Two things gate its archive, in order.
   First, `driftwatchdog`'s `GOVERNANCE_QUALITY_DECLARED_CODES` must gain
   `"SPEC_PURPOSE_PLACEHOLDER"`, or the concern reports `PASS` while this
   checker exits 1 — a cross-repo step this change does not own. Second, the
   1,234-file fleet write is a cross-repo source edit needing explicit
   authorization: review the dry run, then `--apply`, then set
   `SPEC_PURPOSE_AUDIT_ENABLED = True` in the same commit. Until both are done,
   do not enable the rule and do not archive the change.
4. Take packages 4–7 to their owning repositories via `docs/package-backlog.md`;
   each is a separate conversation and a separate repository.
5. Replace the 9 scaffold `HANDOFF.md` bodies as each product's own state is
   recorded (product-owned work).
6. Re-promote each pilot project at its current `HEAD` once its release pipeline
   produces real artifacts, and replace the pilot-context `release_evidence`
   placeholders.
7. Commit the sibling declaration/rules edits in their own repositories when
   those repositories' pending work is ready.

## Evidence boundary

This repository can prove registry/schema/checker behavior, capability
declaration shape, release-evidence shape, the deployable+release-evidence
gate, the product-code quality rule, the deployment promotion
mechanism, the rules-baseline drift report, and the Forge governance adapter
contract. It can prove the front-door skill routes to existing references
(`check_skill_refs.py`), but it cannot prove an agent will trigger the skill. It cannot prove that the seven promoted projects actually build, pass
tests, deploy, or are runtime-healthy; those claims require the promoted
projects' own verification commands and jenkins-local runtime observation. The
adapter likewise cannot prove a project's runtime or release health;
it only translates this repository's own audit findings.

## OpenSpec workflow

Select one active change with `openspec list`, run the local checker and
project gate before archive, validate strictly, archive canonical specs, then
create the required two commits. Each completed OpenSpec spec/change requires
exactly two commits: first the implementation/tests/archive commit, then a
HANDOFF.md-only pointer/evidence commit.

## The marker vocabulary is corrected and the fleet write is done

`placeholder-threshold` and `product-code-boundary` were 78 unbound checks in 39
repositories — the second-largest gap in the fleet. Both are answered by
`scripts/product_code_quality.py`, which is fail-closed and exits 2 without a
`quality` block in the repository's own `.project.json`.

`scripts/bind_gate_commands.py` derives the block (`derive_quality_block`) and
writes it with the command in one operation, both under `--apply` and both
behind the dirty check. `product_roots` and `languages` come from the same disk
detection the build commands use, with the manifest each root came from as
evidence. The `src` convention is per manifest kind: a `.csproj` at
`src/Foo/Foo.csproj` yields `src/Foo`, not `src/Foo/src`. `placeholder_threshold`
is a judgement, written as `0` — the deliberately strict default, relaxable per
project. No `exclude` and no marker list are invented.

**The vocabulary was the blocker, and it is corrected.** Over
`driftwatchdog/src/` the word `placeholder` matched **26** times and **zero** of
them was unfinished work: every one was prose describing the word
(`//! ... extends this placeholder`, `/// Ordered, comma-separated placeholder
names`) or the gate's own `placeholder-threshold` concern identifier in
`src/gate/adapters.rs`, against 1 `TODO` and 1 `FIXME` on the same tree.
`vocabulary.json` now holds `todo`, `fixme`, `xxx`, `hack`, `unimplemented!`,
`todo!`. `product_code_quality.py` is unchanged — it already resolved its
markers from that file at use time.

**This reduces the finding count, and the number is not hidden.** Across the 39
repositories written, marker findings fall **468 → 38** and repositories
reporting `FAIL` fall **28 → 13**. 430 of the 468 were the two ordinary English
words. It is a correction to a mis-specified vocabulary in the one file that
owns it: no threshold moved, no `exclude` was added, no test was skipped or
filtered, and every `TODO` and `FIXME` in the fleet is still reported. The spec
delta at
`openspec/changes/bind-declared-gate-checks/specs/portfolio-vocabulary/spec.md`
states this and keeps the correction-versus-filter distinction explicit.

A hand-written per-project `placeholder_markers` list is left exactly as its
author wrote it. Every `.project.json` in the fleet was grepped: exactly one
carries an inline list — `forge` — and it already names the six retained
tokens, so the earlier premise that it included `placeholder` and `stub` did not
hold, and there was no conflict to resolve.

### Fleet outcome

| Measurement | Before | After |
|---|---|---|
| Gate unbound checks | 125 | **47** |
| Gate repositories with an unbound check | 53 | **24** |
| `gate-debt.json` `unresolved_checks` | 125 | **47** |
| `gate-debt.json` `repositories_with_debt` | 53 | **24** |
| Set-equal against the gate | yes | yes |
| `placeholder-threshold` unbound | 39 | **0** |
| `product-code-boundary` unbound | 39 | **0** |
| Repositories fully wired (of 76 with a manifest) | 23 | **52** |

Set equality, never a count, against
`driftwatchdog/target/debug/driftwatchdog`. The `driftwatchdog` on `PATH` is a
2026-10-01 `cargo install` build that predates unbound reporting and answers 0
for the whole fleet; it is not a usable oracle.

Confirmed on real gate runs, not only on the checker. `openlearning`:
`placeholder-threshold FAIL — placeholder marker count 18 exceeds threshold 0`,
`unbound: ['tests']`. `pangoman`: `placeholder-threshold PASS — placeholder
marker count 0 at or below threshold 0`, `unbound: []`. Both checks execute and
return verdicts in both directions, which is the point of binding them.

**Regenerating the record can no longer write the fleet.** `--debt-only` threads
`apply=False` into `run()` and persists only `gate-debt.json`; it refuses to
combine with `--apply` (exit 2). `DebtOnlyTests` (4) pins that. Note the
`--apply` default `--debt-out` is `root/gate-debt.json`, so an apply run against
`--root /home/paul/code` writes a stray record at the workspace root — pass
`--debt-out` explicitly. The one produced here was removed with
`Path.unlink(missing_ok=True)`.

**Fleet scope, verified.** 39 repositories written, `.project.json` and
`.ai-gate/gate.yaml` only, one commit each on `main`, no push. Confirmed by
hashing both files across all 81 repositories before and after (78 files, 39
repositories, empty set difference against the authorised list) and by
`git show --name-only` on every one of the 39 commits. Pre-existing uncommitted
work in those repositories from earlier sessions — including
`openaccounting/Cargo.toml`, `rust-ecommerce/Cargo.toml` and the `*.bak-profile`
files — was left untouched.

Suite: **748 passed, 158 subtests, 0 failed** (741 on arrival). Seven tests
added: 3 in `PlaceholderTests`, 4 in `DebtOnlyTests`.
`test_placeholder_markers_unchanged` asserted the old list and is now
`test_placeholder_markers_are_unambiguous_debt_tokens`, pinning the retained set
and asserting `placeholder` and `stub` are absent. Negative control: putting
both words back raises marker findings 38 → 468 and red repositories 13 → 28;
the file was restored byte-identically and the suite returned to 748.

### The Rust boundary check reads the module tree now

The defect this section used to list as an owner's problem is fixed, in commit
`93e60cf`, and the fix is in the checker rather than in any repository. See
`openspec/changes/bind-declared-gate-checks/tasks.md` §8 and
`openspec/changes/bind-declared-gate-checks/specs/product-code-quality-boundary/spec.md`.

`product_code_quality.py` decided "is this Rust file test code" from the file
alone, so it could not see that `src/gate/governance/tests.rs` is only ever
compiled by `#[cfg(test)] mod tests;` in `src/gate/governance/mod.rs:627`. A
second, separate cause sat behind it: the guard was tracked per line rather than
per item, so an attribute written *between* the guard and its item disarmed it —
`#[cfg(test)]`, `#[path = "tests.rs"]`, `mod tests;` is one guarded item and was
read as none.

| `product-test-code` findings | Before | After |
|---|---|---|
| `driftwatchdog` | 24 | **0** |
| `rust-ecommerce` | 18 | **0** |
| `alltools-platform` | 2 | **1** |
| fleet total | 60 | **17** |

Real gate runs, `driftwatchdog/target/debug/driftwatchdog gate`:

| Repository | `product-code-boundary` | Still red for |
|---|---|---|
| `rust-ecommerce` | FAIL → **PASS** | `security` unbound, `source-file-size`, two adapter timeouts |
| `driftwatchdog` | FAIL (24 findings) → FAIL (0 test-code) | 2 placeholder markers in `src/gate/concerns.rs:20`, 8 files over 1000 lines |
| `alltools-platform` | FAIL | 1 real bare `#[test]` in `test_prompt.rs`, 11 markers |
| `argoset`, `crossify`, `fotofy`, `transitfy` | FAIL, unchanged | the **TypeScript** `describe(`/`it(` heuristic — a different defect |

The five repositories that were red on `product-test-code` alone with zero
markers — `argoset`, `crossify`, `fotofy`, `rust-ecommerce`, `transitfy` — split
one and four. Only `rust-ecommerce` was red for the Rust reason; the other four
are red on a TypeScript regex, which this change does not touch.

No `exclude`, no filename exception list, no test weakened. A `tests.rs` that
no `#[cfg(test)]` declaration reaches is still reported, which is what
`RustModuleTreeBoundaryTests::test_the_declaration_is_what_clears_it_not_the_file_name`
pins. Negative control on a **copy** of `src/gate/governance` in a temp
directory, never on `driftwatchdog` itself: **0 → 24 → 0** findings. A `tests/`
directory inside a product root needed no handling — `DEFAULT_EXCLUDED_DIRS`
already matches the `tests` path segment, so it is out of scope before the module
tree is consulted.

Suite: **759 passed, 158 subtests, 2 failed** (13 added here). Both failures
are independent of this change and reproduce with it stashed:

- `GateOracleTest::test_the_record_names_nothing_the_gate_calls_bound` —
  `gate-debt.json` calls `('metiscope', 'build')` debt the live gate does not.
  Pre-existing on `main`; it is about the debt record, not the Rust scan.
- `SequencingGateTests::test_the_gate_is_open_and_the_fleet_corpus_is_clean` —
  `refused: lileililiwen-site: … census: 12 .py records kind 'product' but the
  declaration says 'deployment'`. It reads the live sibling tree at
  `/home/paul/code`, and `lileililiwen.github.io` has gained `scripts/*.py`
  and `tests/*.py` from other work.

The `748 passed, 0 failed` figure quoted above was true when it was measured.

### Open for their owners

- **Four repositories are red on the TypeScript `describe(`/`it(` heuristic**
  with zero marker findings: `argoset` 2, `crossify` 1, `fotofy` 6,
  `transitfy` 6. The same class of false positive as the Rust one — a component
  whose own name or subject is "test" trips a two-token regex — in a language
  this change does not touch. Recorded in `tasks.md` §8; not fixed here.
- **`opendockify` is `REVIEW_REQUIRED` on `readme-claim-unscoped`** — its README
  line 52 makes a negative status statement naming no surface the checker can
  resolve. A README finding for that repository's owner, surfaced only now
  because the block made the check run.
- The change is **not archived**. Archiving needs separate authorization.
