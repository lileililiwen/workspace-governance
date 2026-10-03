# Tasks: readme-claim-verification

## 0. Caveats and confirmations

- [ ] **Agree the level of `QUALITY_README_CLAIM_CONTRADICTED` before
  implementing it.** ERROR fails the unattended audit for 7 repositories
  until each README is corrected, and a sibling README edit needs
  authorization this owner does not hold. WARNING is the alternative
  (open decision 1). Decide first; do not discover the answer from a red
  audit.
- [ ] **Do not repair a README in this package.** The finding names the line
  and the contradicting evidence path; the repository owner decides which
  side is wrong. Editing a sibling is out of scope by `AGENTS.md`, and
  `capability-adoption-gate` already split the same problem away from
  `cross-repo-adoption-grant` for the same reason.
- [ ] **Two corpus expectations in the commissioning brief are wrong;
  `design.md` §5.1 records the measurement.** `chronicleaf` makes no false
  claim — its status block is current and scoped. `reelio`,
  `shopifireman` and `rostera` are not honest stubs: 87, 115 and 354 source
  files respectively sit under their own "no source" claims. The
  must-not-fire set is `kairosa` and `chronicleaf`. Confirm this before
  writing the corpus fixtures, because a fixture built on the brief would
  encode a rule that fires on `kairosa`.
- [ ] **`kairosa` is the case that decides the design.** It has 22 `.cs`
  files, 124 xUnit tests and a CI workflow, and an accurate status line —
  because the line scopes its absence to six surfaces that are genuinely
  absent. Any implementation that counts files repository-wide will fail its
  fixture. Claim scope is a requirement, not an optimisation.
- [ ] **Do not gate the rule behind the `quality` block.** Only 2 of 81
  declarations carry one; gating leaves 79 repositories unexamined and the
  rule dead. The claim is the trigger.
- [ ] **Bound the README read and the directory walk.** 64 KiB read
  ceiling, `DEFAULT_EXCLUDED_DIRS` plus the `discover_projects` skip list, no
  symlink following, no project command, no network, no write to any
  project.
- [ ] **Never narrow an existing vocabulary array.** `readme_claim_surfaces`
  and `readme_absence_phrases` are additive; `placeholder_markers`,
  `secret_field_substrings`, `profiles`, `kinds`, `standalone_statuses` and
  `integration_required_states` stay byte-identical.
- [ ] **Stage only this change directory.** The repository has a
  pre-existing uncommitted `.project.json` edit and an untracked
  `MATURITY_PROGRESS_SUMMARY.md`; they must not be swept into the change's
  commits.

## 1. BFS — Baseline and impact coverage

- [ ] 1.1 Record the baseline finding set for all 78 registered
  repositories before any edit, and assert that the 72 repositories outside
  the measured corpus are byte-identical after the change. Without this
  snapshot, "additive" is an assertion rather than a check.
- [ ] 1.2 Record the measured corpus: 9 repositories with negative status
  language, 7 contradicted, 19 contradicted surfaces, 1 untestable claim,
  2 clean — with the per-repository evidence paths from `design.md` §5.
  These numbers are the fixture oracle.
- [ ] 1.3 Map each requirement in `proposal.md` onto existing code:
  `Policy` / `parse_policy` / `evaluate` / `Report`
  (`scripts/product_code_quality.py:125`, `:187`, `:523`, `:159`),
  `DEFAULT_EXCLUDED_DIRS` (`:79`), `LANGUAGE_EXTENSIONS` (`:110`),
  `_is_path_safe` (`:251`), `_is_excluded` (`:260`), `_candidate_files`
  (`:301`), `redact` (`:514`), `validate_product_quality`
  (`scripts/workspace_check.py:1629`), `validate_kind` (`:372`),
  `read_manifest_dependencies` (`:868`), and `classify_standalone` (`:2030`)
  as the read-only-classification precedent.
- [ ] 1.4 Add failing tests before implementation: one fixture per corpus
  repository; a claim-scope fixture using `kairosa`'s exact wording; a
  code-block fixture; a future-tense fixture using `rostera/README.md:20`
  (must be ignored) alongside `:44` (must fire); an unknown-surface fixture
  using `chronicleaf`'s ten-item list; a `{"mode": "off"}` fixture; an
  invalid-`readme_claims` fixture; a `*.slnx`-only build fixture; and a
  vocabulary-load failure fixture for an empty `readme_claim_surfaces`.
- [ ] 1.5 Verify the implementation-handoff gate: Python 3.11,
  `workspace-governance`, no shared-library boundary crossed, no sibling
  repository written.

## 2. DFS — Requirement-by-requirement implementation

- [ ] 2.1 R1: add `readme_claim_surfaces` and `readme_absence_phrases` to
  `vocabulary.json`; surface them from `scripts/vocabulary.py` with the
  existing fail-closed duplicate and empty-list handling. Include
  `data-set` in the surface set and give it no evidence rule, so it reports
  untestable rather than unchecked (open decision 3).
- [ ] 2.2 R1: implement `_readme_claims` — the qualifying-claim extraction
  from `design.md` §4.1. Exclude fenced code blocks, HTML comments, block
  quotes, and future/hypothetical scoping. Report the README byte offset and
  1-based line number for every accepted claim, because the finding message
  must be actionable at a line.
- [ ] 2.3 R2 and R3: implement `_claim_surfaces` and the bounded evidence
  rules from `design.md` §4.2, reusing `DEFAULT_EXCLUDED_DIRS`,
  `LANGUAGE_EXTENSIONS`, `_is_path_safe`, `_is_excluded` and
  `read_manifest_dependencies` for `provider-integration`. Evaluate **only**
  the surfaces a claim names. Evidence: the `kairosa` fixture reports no
  contradicted surface despite 39 source files, a test root and a CI
  workflow.
- [ ] 2.4 R4: emit rule `readme-status-claim` findings, one per contradicted
  surface, with `level: ERROR`, `severity: FAIL`, and a message naming the
  README line, the surface, and the evidence path. When two claims name the
  same surface, report once against the first claim and name both line
  numbers.
- [ ] 2.5 R5: emit `QUALITY_README_CLAIM_UNSCOPED` for a claim naming only
  unknown surfaces, a claim naming a surface with no evidence rule, an
  unreadable or truncated README, and a negative status statement in a
  repository with no qualifying claim. `severity: REVIEW_REQUIRED`, never
  PASS.
- [ ] 2.6 R6: add the additive `readme_claims` block to
  `schemas/project.schema.json` (`mode: off | check`, optional `surfaces`),
  not in `required`. Implement `validate_readme_claims` in
  `workspace_check.py`, call it from `validate_project` for every registered
  project — following the unconditional `validate_kind` pattern, not the
  `quality`-gated one — and translate the report with the existing
  FAIL→ERROR / REVIEW_REQUIRED→WARNING mapping. Declare
  `QUALITY_README_CLAIM_CONTRADICTED` and `QUALITY_README_CLAIM_UNSCOPED`;
  add both to the finding-code table in `docs/vocabulary.md`.
- [ ] 2.7 R7: add a test asserting that a repository with a contradicted
  claim and `deployable: true`, an `evidence_status`, and a promotion-ledger
  entry reports the same evidence state as before. A README sentence is
  prose; it never becomes evidence.
- [ ] 2.8 Update `docs/product-code-quality.md` with the rule, the surface
  table, the two codes, the measured corpus, and the
  `readme_claims` block. Update `README.md` with one short paragraph and
  link rather than restate. Record the outcome in `HANDOFF.md` in the second
  commit.

## 3. BFS — Cross-surface regression and completeness

- [ ] 3.1 R6: prove additivity against the §1.1 baseline — the 72
  repositories outside the corpus produce a finding set identical to before,
  and `maturity_audit.py` still reports the single `workspace_check.py`
  result with no second opinion.
- [ ] 3.2 R3: prove claim scope holds for a partial claim. A README that
  denies only its API while shipping a web client MUST report the API
  contradiction and MUST NOT report anything about the web client.
- [ ] 3.3 Prove the two honest repositories stay clean:
  `QUALITY_README_CLAIM_CONTRADICTED` fires for none of the 72, and
  `kairosa` and `chronicleaf` produce the exact outcomes in `design.md` §5.
- [ ] 3.4 R7: prove no evidence state moves for the 7 contradicted
  repositories — no change to `lifecycle`, `evidence_status`,
  `deployable`, the promotion ledger, or any `CAPABILITY_ADOPTION_*`
  posture. `measure_capability_adoption` is not called with a claim result.
- [ ] 3.5 Prove the read-only and bounded properties: a recursive tree hash
  of a fixture project is identical before and after, no child process is
  spawned, a `..` or absolute path in `readme_claims` is refused without
  being read, a symlinked directory is not followed, and a README above
  64 KiB is truncated with the truncation stated in the finding.
- [ ] 3.6 Prove the fail-closed path: a missing or empty
  `readme_claim_surfaces` exits non-zero naming the file, and a claim whose
  only named surface is `data-set` reports
  `QUALITY_README_CLAIM_UNSCOPED` rather than passing.
- [ ] 3.7 Confirm the existing quality gate is untouched:
  `product_code_quality.py` still returns the same status, counts, and exit
  code for `forge` and `workspace-governance` — the only 2 declarations with
  a `quality` block — and a per-project `placeholder_markers` override is
  still honoured.
- [ ] 3.8 Confirm `auto_gate.py` needs no change: an
  `QUALITY_README_CLAIM_CONTRADICTED` ERROR fails the unattended gate
  through the existing `summary["errors"]` rule, and the report schema is
  unchanged.

## 4. Verification

- [ ] 4.1 `python3 -m unittest discover -s tests -v` — all pass, including
  `tests/test_readme_claim_verification.py`, with no existing test changing
  expectation.
- [ ] 4.2 `python3 scripts/product_code_quality.py <project_dir> --json` for
  one contradicted, one clean (`kairosa`), and one untestable
  (`chronicleaf`) fixture — one parseable report each, correct exit code,
  every message passed through `redact`.
- [ ] 4.3 `python3 scripts/workspace_check.py --root .. --audit --json` —
  record the pre-correction output (expected: 7 contradicted projects, 19
  surfaces, 1 `QUALITY_README_CLAIM_UNSCOPED`) verbatim, then the
  post-correction output after the repository owners fix their own READMEs.
  If the READMEs are not corrected in this cycle, record the pre-correction
  output as the final state and say so plainly rather than marking this
  complete.
- [ ] 4.4 `python3 scripts/workspace_check.py --self-check` — 0 errors, 0
  warnings for the governance repository itself.
- [ ] 4.5 `node scripts/check-openspec-change-names.mjs`,
  `openspec validate readme-claim-verification --strict`, and
  `git diff --check`.
- [ ] 4.6 Record actual outputs. Report any environment-blocked check with
  its exact next action rather than as passing.
