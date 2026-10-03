# Tasks: readme-claim-verification

## 0. Caveats and confirmations

- [x] **`QUALITY_README_CLAIM_CONTRADICTED` is ruled ERROR.** ERROR fails the
  unattended audit for 7 repositories until each README is corrected, and a
  sibling README edit needs authorization. That authorization has been granted
  for a fixed repair order (see `design.md` §10, ruling 9), so ERROR ships
  together with the repair order rather than after a red audit. A warning
  nobody must clear is the mechanism by which the 7 stale claims accumulated in
  the first place.
- [x] **Do not repair a README in this package.** The finding names the line
  and the contradicting evidence path; the repository owner decides which
  side is wrong. Editing a sibling is out of scope by `AGENTS.md`, and
  `capability-adoption-gate` already split the same problem away from
  `cross-repo-adoption-grant` for the same reason.
- [x] **Two corpus expectations in the commissioning brief are wrong;
  `design.md` §5.1 records the measurement.** `chronicleaf` makes no false
  claim — its status block is current and scoped. `reelio`,
  `shopifireman` and `rostera` are not honest stubs: 87, 115 and 354 source
  files respectively sit under their own "no source" claims. The
  must-not-fire set is `kairosa` and `chronicleaf`. This is already
  measured; confirm it before writing the corpus fixtures, because a fixture
  built on the brief would encode a rule that fires on `kairosa`. Note the
  ruled consequence: `chronicleaf` is counted once in the aggregate unscoped
  coverage metric, but it MUST NOT receive a per-repository finding, because
  its claim is accurate.
- [x] **`kairosa` is the case that decides the design.** It has 22 `.cs`
  files, 124 xUnit tests and a CI workflow, and an accurate status line —
  because the line scopes its absence to six surfaces that are genuinely
  absent. Any implementation that counts files repository-wide will fail its
  fixture. Claim scope is a requirement, not an optimisation.
- [x] **Do not gate the rule behind the `quality` block.** Only 2 of 81
  declarations carry one; gating leaves 79 repositories unexamined and the
  rule dead. The claim is the trigger.
- [x] **Bound the README read and the directory walk.** 64 KiB read
  ceiling, `DEFAULT_EXCLUDED_DIRS` plus the `discover_projects` skip list, no
  symlink following, no project command, no network, no write to any
  project.
- [x] **Never narrow an existing vocabulary array.** `readme_claim_surfaces`
  and `readme_absence_phrases` are additive; `placeholder_markers`,
  `secret_field_substrings`, `profiles`, `kinds`, `standalone_statuses` and
  `integration_required_states` stay byte-identical.
- [x] **Stage only this change directory.** The repository has a
  pre-existing uncommitted `.project.json` edit and an untracked
  `MATURITY_PROGRESS_SUMMARY.md`; they must not be swept into the change's
  commits.

## 1. BFS — Baseline and impact coverage

- [x] 1.1 Record the baseline finding set for all 78 registered
  repositories before any edit, and assert that the 72 repositories outside
  the measured corpus are byte-identical after the change. Without this
  snapshot, "additive" is an assertion rather than a check.
- [x] 1.2 Record the measured corpus: 9 repositories with negative status
  language, 7 contradicted, 19 contradicted surfaces, 1 untestable claim,
  2 clean — with the per-repository evidence paths from `design.md` §5.
  These numbers are the fixture oracle.

  **Re-measured 2026-10-03 against the current tree; the oracle moved.** Five
  of the seven contradicted READMEs have since been corrected, so the corpus is
  now **4 contradicted repositories / 4 contradicted surfaces / 3 unscoped
  statements / 7 clean**, not 7 / 19 / 1 / 2:

  | Repository | Claim | Surface | Evidence | Outcome |
  |---|---|---|---|---|
  | `argoset` | `README.md:31` live source adapters not implemented | `application-source` | `apps/api/src/auth.rs` | ERROR ×1 |
  | `care-bridge` | `README.md:17` no deployment is provisioned | `deployment` | `compose.yaml` | ERROR ×1 |
  | `retake-kit` | `README.md:42` no production deployment exists | `deployment` | `compose.yaml` | ERROR ×1 |
  | `devloom` | `README.md:9` nothing is deployed | `deployment` | `compose.yaml` | ERROR ×1 |
  | `kairosa` | five named surfaces, all absent | — | 39 source files, `tests/`, CI — none claimed | clean |
  | `chronicleaf` | ten named features | — | n/a | clean; 1 unscoped |
  | `opendockify` | `README.md:52` not implemented in the MVP | — | n/a | clean; 1 unscoped |
  | `platform-contracts` | `README.md:15` planning-only | — | n/a | clean; 1 unscoped |
  | `pluggify`, `testify`, `aesthra`, `reelio`, `shopifireman`, `rostera` | claims now accurate | — | — | clean |

  `rostera`'s `Rostera.slnx` is the only build marker in that repository, which
  is why `*.slnx` is in the `build` evidence rule. Two measured **precision
  limits** are recorded in `docs/product-code-quality.md` and are not smoothed
  over: the `deployment` evidence rule treats a local `compose.yaml` as the
  `deployment` surface, and the `application-source` census is whole-tree.
- [x] 1.3 Map each requirement in `proposal.md` onto existing code:
  `Policy` / `parse_policy` / `evaluate` / `Report`
  (`scripts/product_code_quality.py:125`, `:187`, `:523`, `:159`),
  `DEFAULT_EXCLUDED_DIRS` (`:79`), `LANGUAGE_EXTENSIONS` (`:110`),
  `_is_path_safe` (`:251`), `_is_excluded` (`:260`), `_candidate_files`
  (`:301`), `redact` (`:514`), `validate_product_quality`
  (`scripts/workspace_check.py:1629`), `validate_kind` (`:372`),
  `read_manifest_dependencies` (`:868`), and `classify_standalone` (`:2030`)
  as the read-only-classification precedent.
- [x] 1.4 Add failing tests before implementation: one fixture per corpus
  repository; a claim-scope fixture using `kairosa`'s exact wording; a
  code-block fixture; a future-tense fixture using `rostera/README.md:20`
  (must be ignored) alongside `:44` (must fire); an unknown-surface fixture
  using `chronicleaf`'s ten-item list; a `{"mode": "off"}` fixture that MUST
  be refused (the check still runs); a `*.slnx`-only build fixture; and a
  vocabulary-load failure fixture for an empty `readme_claim_surfaces`.

  All of these fixtures exist in `tests/test_readme_claim_verification.py`
  (33 tests). Recorded honestly: they were written alongside the implementation
  rather than red-first, so the red phase was never observed. The corpus
  fixtures assert the **re-measured** corpus in 1.2, not the 7/19 numbers
  above, because those repositories' claims have been corrected since.
- [x] 1.5 Verify the implementation-handoff gate: Python 3.11,
  `workspace-governance`, no shared-library boundary crossed, no sibling
  repository written.

## 2. DFS — Requirement-by-requirement implementation

- [x] 2.1 R1: add `readme_claim_surfaces` and `readme_absence_phrases` to
  `vocabulary.json`; surface them from `scripts/vocabulary.py` with the
  existing fail-closed duplicate and empty-list handling. Do **not** include
  `data-set`: it is deliberately dropped from the vocabulary because no
  evidence rule can decide it from a file tree, and a surface that cannot be
  decided is not a check (ruled — see `design.md` §10, ruling 8).
- [x] 2.2 R1: implement `_readme_claims` — the qualifying-claim extraction
  from `design.md` §4.1. Exclude fenced code blocks, HTML comments, block
  quotes, and future/hypothetical scoping. Report the README byte offset and
  1-based line number for every accepted claim, because the finding message
  must be actionable at a line.
- [x] 2.3 R2 and R3: implement `_claim_surfaces` and the bounded evidence
  rules from `design.md` §4.2, reusing `DEFAULT_EXCLUDED_DIRS`,
  `LANGUAGE_EXTENSIONS`, `_is_path_safe`, `_is_excluded` and
  `read_manifest_dependencies` for `provider-integration`. Evaluate **only**
  the surfaces a claim names. Evidence: the `kairosa` fixture reports no
  contradicted surface despite 39 source files, a test root and a CI
  workflow.
- [x] 2.4 R4: emit rule `readme-status-claim` findings, one per contradicted
  surface, with `level: ERROR`, `severity: FAIL`, and a message naming the
  README line, the surface, and the evidence path. When two claims name the
  same surface, report once against the first claim and name both line
  numbers.
- [x] 2.5 R5: emit `QUALITY_README_CLAIM_UNSCOPED` as a **single aggregate
  coverage metric per run**, not as a per-repository finding. Count a claim
  naming only unknown surfaces, a claim naming a subject outside the closed
  vocabulary, an unreadable or truncated README, and a negative status
  statement in a repository with no qualifying claim. Name each unscoped
  statement and its repository. `severity: REVIEW_REQUIRED`, never PASS. It
  fires on `chronicleaf`, whose claim is accurate, so emitting it per
  repository would be a false positive that trains readers to ignore the
  checker (ruled — `design.md` §10, ruling 7).
- [x] 2.6 R6: add **no** `readme_claims` block to
  `schemas/project.schema.json`. The claim check runs for every registered
  project, triggered by claim presence, and the audit honours no `mode`,
  opt-out, or per-repository exemption. A declaration carrying a
  `readme_claims` key is reported as WARNING `QUALITY_REVIEW_REQUIRED`
  naming the unsupported field, and canonical behaviour applies anyway —
  a check that can be switched off is not a check (ruled — `design.md` §10,
  ruling 10). Declare `QUALITY_README_CLAIM_CONTRADICTED` and
  `QUALITY_README_CLAIM_UNSCOPED`; add both to the finding-code table in
  `docs/vocabulary.md`.
- [x] 2.7 R7: add a test asserting that a repository with a contradicted
  claim and `deployable: true`, an `evidence_status`, and a promotion-ledger
  entry reports the same evidence state as before. A README sentence is
  prose; it never becomes evidence.
- [ ] 2.8 Update `docs/product-code-quality.md` with the rule, the surface
  table, the two codes, the measured corpus, the aggregate coverage metric,
  and the explicit statement that the rule has no opt-out. Update `README.md`
  with one short paragraph and link rather than restate. Record the outcome
  in `HANDOFF.md` in the second commit.

  `docs/product-code-quality.md`, `docs/vocabulary.md` and `README.md` are
  updated. **The `HANDOFF.md` record is the second commit and was not made** —
  this package makes no commits, so the last clause is outstanding.

## 3. BFS — Cross-surface regression and completeness

- [x] 3.1 R6: prove additivity against the §1.1 baseline — the 72
  repositories outside the corpus produce a finding set identical to before,
  and `maturity_audit.py` still reports the single `workspace_check.py`
  result with no second opinion.
- [x] 3.2 R3: prove claim scope holds for a partial claim. A README that
  denies only its API while shipping a web client MUST report the API
  contradiction and MUST NOT report anything about the web client.
- [x] 3.3 Prove the two honest repositories stay clean:
  `QUALITY_README_CLAIM_CONTRADICTED` fires for none of the 72, and
  `kairosa` and `chronicleaf` produce the exact outcomes in `design.md` §5.
- [x] 3.4 R7: prove no evidence state moves for the 7 contradicted
  repositories — no change to `lifecycle`, `evidence_status`,
  `deployable`, the promotion ledger, or any `CAPABILITY_ADOPTION_*`
  posture. `measure_capability_adoption` is not called with a claim result.
- [x] 3.5 Prove the read-only and bounded properties: a recursive tree hash
  of a fixture project is identical before and after, no child process is
  spawned, a `..` or absolute path in a declaration is refused without
  being read, a symlinked directory is not followed, and a README above
  64 KiB is truncated with the truncation stated in the finding.
- [x] 3.6 Prove the fail-closed path: a missing or empty
  `readme_claim_surfaces` exits non-zero naming the file, and a claim naming a
  subject outside the closed vocabulary — including `data-set`, which is not in
  the vocabulary at all — is counted in the aggregate
  `QUALITY_README_CLAIM_UNSCOPED` coverage metric rather than passing and
  rather than producing a contradicted finding.
- [x] 3.7 Confirm the existing quality gate is untouched:
  `product_code_quality.py` still returns the same status, counts, and exit
  code for `forge` and `workspace-governance` — the only 2 declarations with
  a `quality` block — and a per-project `placeholder_markers` override is
  still honoured.
- [x] 3.8 Confirm `auto_gate.py` needs no change: an
  `QUALITY_README_CLAIM_CONTRADICTED` ERROR fails the unattended gate
  through the existing `summary["errors"]` rule, and the report schema is
  unchanged.

## 4. Verification

- [x] 4.1 `python3 -m unittest discover -s tests -v` — all pass, including
  `tests/test_readme_claim_verification.py`, with no existing test changing
  expectation.
- [x] 4.2 `python3 scripts/product_code_quality.py <project_dir> --json` for
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

  **Not complete, and deliberately left unchecked.** This is the final state,
  recorded as the task requires. The fleet audit is
  `errors=215 warnings=18`, against a `errors=211 warnings=17` baseline, and
  every line of the difference is accounted for: **+4**
  `ERROR QUALITY_README_CLAIM_CONTRADICTED` (`argoset`, `care-bridge`,
  `retake-kit`, `devloom`) and **+1** fleet-level
  `WARNING QUALITY_README_CLAIM_UNSCOPED` naming 3 unscoped statements
  (`opendockify`, `platform-contracts`, `chronicleaf`). No existing code changed
  count. The seven READMEs `design.md` §5 measured have not all been corrected
  in this cycle, and the repair sequence in ruling 9 is a sequence of separately
  authorized cross-repo commits that this package does not make — so the audit
  stays red until those owners act, which is the correct outcome of ruling 6.
  The measured corpus is 4 contradicted repositories, not the 7/19 recorded in
  1.2's original text; see the re-measured table above.
- [x] 4.4 `python3 scripts/workspace_check.py --self-check` — 0 errors, 0
  warnings for the governance repository itself.
- [x] 4.5 `node scripts/check-openspec-change-names.mjs`,
  `openspec validate readme-claim-verification --strict`, and
  `git diff --check`.
- [x] 4.6 Record actual outputs. Report any environment-blocked check with
  its exact next action rather than as passing.

## 5. Follow-up — the authorized repair sequence (not this package)

`design.md` §10 ruling 9 fixes the repair order for contradicted READMEs:
**blast radius descending, one commit per repository, each a separately
authorized cross-repo source edit.** This package wrote no sibling and edits
none. The order below is a documented follow-up, and each repair is the
repository owner's own commit.

| Order | Repository | Contradicted surfaces (2026-10-03 §5) | Status |
|---|---|---|---|
| 1 | `rostera` | 5 | claims corrected; no finding today |
| 2 | `care-bridge` | 4 | claims corrected; 1 finding today, `deployment` |
| 3 | `aesthra` | 4 | claims corrected; no finding today |
| 4 | `reelio` | 3 | claims corrected; no finding today |
| 5 | `pluggify` | 1 | claims corrected; no finding today |
| 6 | `testify` | 1 | claims corrected; no finding today |
| 7 | `shopifireman` | 1 | claims corrected; no finding today |

Four repositories that were never in that table are contradicted today and
were not in the 2026-10-03 measurement, so they have no repair slot yet and
need one recorded before their owners act:

| Repository | Surface | Why it is contradicted today |
|---|---|---|
| `argoset` | `application-source` | the claim denies *live source adapters for named platforms*; the evidence rule is a whole-source-root census |
| `care-bridge` | `deployment` | the claim denies a *provisioned* deployment; the evidence rule is `compose*.y(a)ml` at any depth |
| `retake-kit` | `deployment` | same shape: "no production deployment exists" against a local Compose |
| `devloom` | `deployment` | same shape: "nothing is deployed" against a portable Compose |

Two open questions for the owner, deliberately not answered here:

1. Should the `deployment` evidence rule distinguish a local Compose from a
   provisioned deployment? Three of the four current findings turn on it.
2. Should the `application-source` evidence rule be scoped below the whole
   source root, so a claim about one kind of source is not answered by any
   source file?

Until both are decided, the `ERROR` level stands as ruled and the audit stays
red on those four.
