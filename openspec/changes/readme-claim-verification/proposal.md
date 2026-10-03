# Proposal: Make a README "not implemented" claim verifiable against the file tree

## Why

A README status line is the first thing an agent reads about a sibling
repository. **7 `AGENTS.md` files** across 6 repositories plus the project
template instruct exactly that: "Assess shared infrastructure before
duplication", "assess sibling `common`/`manager` projects". The assessment
has two inputs — the sibling's declared classification and the sibling's
README — and neither is currently checked against reality. Seven
repositories in this workspace state in prose that they contain no
implementation while their file tree contains one.

Measured 2026-10-03, bounded read-only, excluding `node_modules`, `dist`,
`build`, `target`, `bin`, `obj`, `vendor`, `coverage`, `.git`,
`__pycache__`, `.venv`, `.dart_tool`, `.next`, `out`, `.turbo`:

| Repository | README claim | What the tree holds | Verdict |
|---|---|---|---|
| `pluggify` | `README.md:9` "planning-only. No extension application has been implemented, packaged, published, archived, or released" | 112 `.ts` files, built `packages/shared/dist` | **contradicted** |
| `careBridge` | `README.md:17` "No application source, runtime, deployment, provider integration, or production evidence exists" | 32 `.cs`, `CareBridge.sln`, `src/CareBridge.Api/Program.cs`, `compose.yaml`, 7 pinned `Platform.*` packages | **contradicted** on 4 of the 5 surfaces it names |
| `testify` | `README.md:92` "contains specifications and documentation only" | 97 source files (86 `.cs`, 10 `.py`), `testify.sln`, `tests/` | **contradicted** |
| `aesthra` | `README.md:13` "has no application source, selected implementation stack, build, test, CI, or runtime verification" | 137 `.cs`, `Aesthra.sln`, `tests/`, `.github/workflows/governance.yml` | **contradicted** on 4 of 5 |
| `reelio` | `README.md:31` "contains no application source, tests, CI configuration, database migrations, or deployment evidence" | `src/api` (78 `.cs`) + `src/client` (9), `Reelio.Api/Program.cs`, `.github/workflows/ci.yml`, `Data/Migrations` | **contradicted** on 3 of 5 |
| `shopifireman` | `README.md:17` "contains planning artifacts only" | 115 source files, 770 KB, under `apps/` and `packages/` | **contradicted** |
| `rostera` | `README.md:44` "No source, build, test, deployment, provider, or runtime integration exists yet" | 354 `.cs` (1.5 MB) under `src/` and `tests/`, `Rostera.slnx`, `compose.yaml`, `Rostera.Api/Program.cs` + 2 controllers | **contradicted** on 5 of 6 |

The cost is not the seven wrong sentences. It is that each one is a
**false negative in the duplication assessment the workspace mandates**: an
agent told to assess a sibling before duplicating reads "no application
source exists" and correctly concludes there is nothing to reuse, then
writes its own. That is precisely the outcome
`capability-adoption-gate` measures across 34 idempotency, 28 rate-limiting
and 28 telemetry sites, arriving by a different route.

**The fix cannot be a keyword ban, and the corpus proves it.** Two
repositories in the same workspace carry negative status language and are
**not** wrong:

- `kairosa/README.md:11` — "Domain read models implemented in
  `src/Kairosa.CulturalData` … with 124 passing xUnit tests. … **No product
  runtime, data set, API, web client, mobile client, or production
  verification exists yet** — the library is an in-memory domain model."
  All six named surfaces are genuinely absent. The repository has a test
  suite and a CI workflow, and it never claims otherwise.
- `chronicleaf/README.md:19` — "What does not exist yet: GitHub
  integration, Evidence Bundles, screenshot capture, media storage, the
  credential vault, AI generation, Markdown drafts, review/approval, export
  and the Milestone Timeline." Ten named items, none of them a surface this
  checker can resolve, and it is a current, accurate status.

A check that reads "the README says nothing is implemented" and counts files
would fire on `kairosa`, the most honest status block in the workspace. A
check that reads the whole repository as one claim also fires on it. The
only rule that separates the seven from the two is **claim scope**: a claim
is verified only against the surfaces it names, and nothing else.

The natural home already exists. `scripts/product_code_quality.py` is a
bounded, read-only, fail-closed per-repository checker with
`DEFAULT_EXCLUDED_DIRS`, a per-language `LANGUAGE_EXTENSIONS` census, and a
`PASS | FAIL | REVIEW_REQUIRED` report that `workspace_check.py` already
translates into `QUALITY_*` findings. It has no rule for documentation
claims, and this change adds one.

## What Changes

- Add a **readme-status-claim rule** to `product_code_quality.py`: detect a
  present-tense absence claim in `README.md`, resolve each claim to the
  closed set of surfaces it names, and test each named surface against
  bounded, read-only file-tree evidence.
- Add a **closed surface vocabulary** shared with `vocabulary.json`:
  `application-source`, `build`, `test`, `ci`, `runtime`, `api`,
  `web-client`, `mobile-client`, `migrations`, `deployment`,
  `provider-integration`, `production-evidence`, `data-set`, plus the
  `repository-content` pseudo-surface that covers "planning artifacts
  only" and "specifications and documentation only".
- **A claim is verified only against the surfaces it names.** A claim that
  says nothing is implemented MUST NOT be evaluated against the whole
  repository, and a claim about a subset MUST NOT be evaluated against the
  rest. This is the rule that keeps `kairosa` and `chronicleaf` clean, and
  it is stated as a requirement rather than left to the implementation.
- **A claim that cannot be resolved is never a pass.** A negative status
  statement that names no surface from the closed vocabulary is WARNING
  `QUALITY_README_CLAIM_UNSCOPED` — a claim the checker cannot test is
  reported as untested, never as true.
- **A claim contradicted by the tree is a finding**: ERROR
  `QUALITY_README_CLAIM_CONTRADICTED`, one per contradicted surface, naming
  the README line, the surface, and the evidence path that contradicts it.
- **Additive and claim-triggered, not opt-in gated.** The rule fires only
  when a qualifying claim exists, so the other 72 registered repositories
  produce exactly the findings they produced before. Only 2 of 81
  declarations carry a `quality` block, so gating the rule behind that block
  would leave 79 repositories unchecked; the check is therefore invoked for
  every registered project from `validate_project`, and the claim itself is
  the trigger.
- **An explicit per-repository off switch and surface extension** via an
  additive `readme_claims` block: `{"mode": "off"}` suppresses the rule for
  a repository, and `{"mode": "check", "surfaces": [...]}` adds
  repository-specific surfaces. Neither is required, and a declaration
  without the block is unchanged.
- **This change detects; it does not repair.** Correcting a README is a
  source edit to a sibling repository, which `AGENTS.md` forbids without
  scope authorization. The finding names the line and the contradiction; the
  owner of each repository decides the wording.

## Package Boundary and Split Assessment

This package ends at **a detected contradiction with a named evidence
path**. It does not edit a README, and it does not decide which of the two
sides of the contradiction is wrong — a stale claim and an undeclared
implementation are different problems with different owners, and the
checker can only see that they disagree.

| Package | Single outcome | Owner / language | Boundary and contract | Depends on | Independent oracle |
|---|---|---|---|---|---|
| `readme-claim-verification` (this) | A "not implemented" README claim is checked against the file tree, and a contradiction is a finding | `workspace-governance`, Python 3.11 stdlib | `product_code_quality.py` rule `readme-status-claim`; `vocabulary.json` surface set; `QUALITY_README_*` findings | existing quality-checker harness; no sibling edit | the 9-repository measured corpus resolves to 7 contradicted / 2 clean; the 72-repo remainder is byte-identical |
| `identity-and-taxonomy-axis-split` (companion) | Immutable `id` plus two classification axes | `workspace-governance`, Python 3.11 stdlib | `vocabulary.json` `roles`/`stacks`; `TAXONOMY_*` findings | none from this change | independent; it never reads a README |
| `cross-repo-adoption-grant` (not this) | The lawful permission to repoint a consumer onto a provider | `workspace-governance`, Python 3.11 stdlib | `adoption_grant` declaration, `adoption/adoptions.json` | registry + provider identity | independent |

The two packages are not merged even though both edit
`vocabulary.json` and both run in the same audit, for one concrete reason:
their blast radii are opposite. Reclassifying a repository is a
governance-owned edit this owner may make unilaterally; rewriting a
sibling's README is a source edit to another repository's files. A single
package containing both would let a 9-file vocabulary change carry a
7-repository source edit, and the source edit would be the part that stalls.

## Sibling and Shared Architecture Reconnaissance

| Candidate | Evidence path/symbol | Reusable code/config/architecture | Compatibility gap | Owner and release boundary | Decision |
|---|---|---|---|---|---|
| `product_code_quality.py` | `Policy`, `evaluate`, `Report`, `DEFAULT_EXCLUDED_DIRS`, `LANGUAGE_EXTENSIONS`, `_candidate_files` | the bounded, read-only, fail-closed per-repo harness; already censuses file extensions and never executes a project | No rule inspects documentation; `parse_policy` requires a `quality` block that only 2 of 81 declarations carry | workspace-governance | **extend shared owner** — new rule, existing harness, no new process |
| `validate_product_quality` | `scripts/workspace_check.py:1629` | the in-process bridge; FAIL→ERROR, REVIEW_REQUIRED→WARNING, PASS→no finding | Only runs when `declaration["quality"]` is a dict, so it cannot host a claim-triggered rule | workspace-governance | **sibling of, not replacement for**: add `validate_readme_claims`, invoked unconditionally like `validate_kind` |
| `validate_kind` | `scripts/workspace_check.py:372` | precedent for auditing a descriptive declaration field for every project, not only opted-in ones | — | workspace-governance | **adopt the invocation pattern** for the unconditional call |
| `vocabulary.json` | `placeholder_markers`, `secret_field_substrings` | one machine-readable word list, loaded fail-closed by both scripts | Has no claim phrase or surface list | workspace-governance | **extend additively** (`readme_claim_surfaces`, `readme_absence_phrases`) |
| `discoverability` metadata | `scripts/repository_metadata.py`, `publication` evidence | README-derived metadata already exists for a different purpose: audience, claims, SEO | Reads README for *presence* of metadata; never cross-checks a status claim against the tree | workspace-governance | **reference, do not extend** — a different question about the same file |
| `standalone` classification | `classify_standalone` | precedent for a read-only tree classification that never overrides a declaration and never executes a project | Classifies capability to operate alone, not documentation truth | workspace-governance | **adopt the posture**: advisory, bounded, never a pass by omission |
| `AGENTS.md` duplication rule | 7 files, 6 repos + template | the instruction that makes the README consequential | The instruction has no defined evidence source for "does a sibling already do this" | each product | **document the finding in `docs/product-code-quality.md`**; no sibling edit in this change |
| `driftwatchdog` gate runtime | gate `checks:` binding | consumes governance findings as evidence | Owns command execution, not claim semantics | driftwatchdog | **defer** — the rule is a governance check, not a gate check |
| `forge_governance_adapter` | observation `findings[]` | passes new codes through unchanged | — | workspace-governance | **no change**; new codes appear only in the existing findings list |

No sibling repository owns documentation-truth verification, so no
extraction is authorized. `workspace-governance` owns it, and the
`product_code_quality.py` harness is the existing shared owner it extends.

## BFS Impact Map

- **Actors:** the governance auditor (read-only), a repository owner
  (decides whether the README or the tree is the thing that is wrong), an
  agent performing the mandated duplication assessment (consumer of the
  finding).
- **State:** a README claim moves `unexamined → verified-consistent` when
  every surface it names is absent, or `unexamined → contradicted` when at
  least one named surface is present. A negative status statement that
  names no known surface moves `unexamined → untestable` and stays there
  until the wording or the vocabulary changes.
- **Contracts:** `vocabulary.json` gains `readme_claim_surfaces` and
  `readme_absence_phrases`; the declaration schema gains an additive
  `readme_claims` block; `product_code_quality.py` gains rule
  `readme-status-claim`; `workspace_check.py` gains
  `QUALITY_README_CLAIM_CONTRADICTED` and
  `QUALITY_README_CLAIM_UNSCOPED`.
- **Local files:** `README.md` is **read only**. No sibling repository is
  written. The governance repository's own `README.md`,
  `docs/product-code-quality.md` and `HANDOFF.md` are the only files this
  change edits outside `scripts/`, `schemas/` and `vocabulary.json`.
- **Integrations:** the existing `findings[]` array in the Forge
  observation, the existing `QUALITY_*` translation, and the existing
  `maturity_audit.py` single-result invariant.
- **Failure and boundary:** a missing or unreadable `README.md` produces no
  claim and therefore no finding — absence of documentation is not a false
  claim, and the profile requirement `REQUIRED_FILE` already owns that case.
  A README over a bounded size, a claim inside a fenced code block, a claim
  in the future tense, and a claim naming an unknown surface are all
  non-qualifying and produce no contradicted finding. A claim naming a
  known surface that the checker cannot evaluate with file-tree evidence
  alone — `data-set` is the one such surface today — is
  `QUALITY_README_CLAIM_UNSCOPED`, never a silent pass.
- **Compatibility:** a repository with no qualifying claim produces exactly
  the findings it produced before this change. The 72 registered
  repositories outside the measured corpus are the regression set.
  `PASS`, `FAIL` and `REVIEW_REQUIRED` keep their meanings; exit codes 0/1/2
  are unchanged.
- **Security:** bounded reads of one file (`README.md`) plus a bounded
  directory walk using the checker's existing `DEFAULT_EXCLUDED_DIRS`. No
  project command, no package manager, no network, no symlink following, no
  write to any project. Finding messages carry a path and a line number, and
  are passed through the existing `redact` helper.
- **Verification:** fixtures for each of the 9 corpus repositories; a
  claim-scope fixture proving `kairosa`-shaped wording produces no finding;
  an unknown-surface fixture proving REVIEW_REQUIRED, not a pass; a
  code-block and future-tense fixture; a `{"mode": "off"}` fixture; and a
  read-only proof (recursive tree hash identical before and after).
- **Dependencies:** Python 3.11 standard library only.

## Capabilities

- **New:** `readme-claim-verification`.
- **Modified:** `product-code-quality-boundary` — the checker's scope
  extends from product source to the repository's own status claim. Its
  existing requirements (declare product source boundaries, reject test code
  in product scope, enforce the placeholder threshold, emit bounded
  machine-readable findings) are preserved unchanged; the fail-closed
  posture and the `PASS | FAIL | REVIEW_REQUIRED` vocabulary are reused
  rather than redefined.
- **Unchanged:** `portfolio-vocabulary`. The new vocabulary arrays are
  additive and no existing array is narrowed.

## Non-goals

- No edit to any sibling repository's `README.md`, source, or CI. This
  change detects a contradiction and names it; the repository owner decides
  which side is wrong.
- No automatic rewriting, deletion, or "suggested replacement" text for a
  README claim.
- No requirement that a README carry a status section, and no new required
  field in any schema. A repository with no claim is valid and silent.
- No judgement about a repository's `lifecycle`, `evidence_status`,
  `deployable` flag, promotion state, or capability adoption. A README is
  prose, and this repository's invariant holds: `workspace_check.py` does
  not promote a capability to verified on its own, and neither does a
  sentence in a README.
- No inference from a positive claim. "Five of 53 packages are implemented"
  is not checked; only present-tense absence claims are in scope.
- No merging of the claim phrase and surface lists into the schema; they
  live in `vocabulary.json` beside the other shared word lists, so one file
  owns the vocabulary.
- No new finding code for a missing or unreadable README.

## Open decisions deliberately left to the owner

1. **ERROR or WARNING for a contradicted claim.** This proposal chooses
   ERROR, because the claim is a factual assertion that the workspace's own
   duplication-assessment rule consumes, and because a warning that nobody
   has to clear is how seven stale claims accumulated. The alternative is
   WARNING with a ramp; that is a one-line change but it leaves the same
   seven sentences in place.
2. **Whether `QUALITY_README_CLAIM_UNSCOPED` should exist at all.** With
   the closed vocabulary as designed, it fires once in the current corpus —
   on `chronicleaf`, whose ten-item negative list is accurate but names no
   surface the checker can resolve. The alternative is to stay silent, which
   means an unverifiable claim is indistinguishable from a verified one.
3. **Whether `data-set` belongs in the surface vocabulary.** It is the one
   surface that cannot be decided from a file tree with confidence: a
   repository can have `fixtures/` and no data set, or a `data/` directory
   of stubs. This proposal includes it and reports it as untestable rather
   than guessing. The alternative is to drop it from the vocabulary, which
   would make `kairosa`'s claim silently half-checked.
4. **Who fixes the seven, and in which order.** The finding is per
   repository, but remediation is a sibling source edit requiring
   authorization. This proposal explicitly does not sequence the repairs; the
   owner may prefer to fix `careBridge` and `rostera` first because each
   contradicts 4–5 surfaces, or to fix all seven in one sweep.
5. **Whether the 72-silent baseline should become an explicit registry of
   claim-free repositories.** A declaration could opt in to the rule with
   `readme_claims: {"mode": "check"}` so that a *future* claim is checked
   too. The current design already checks future claims everywhere, so this
   is a reporting choice rather than a behaviour change.
