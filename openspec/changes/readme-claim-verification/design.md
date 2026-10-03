# Design: readme-claim-verification

## 1. Implementation boundary

**Repository:** `/home/paul/code/workspace-governance` — Python 3.11, standard
library only. **No sibling repository is written**, including the seven with
contradicted claims.

**Files to change:**

- `vocabulary.json` — add `readme_claim_surfaces` (the closed surface set)
  and `readme_absence_phrases` (the claim vocabulary). Both are non-empty,
  duplicate-free, and loaded through the existing fail-closed path.
- `scripts/vocabulary.py` — surface the two arrays.
- `scripts/product_code_quality.py` — add the `readme-status-claim` rule:
  claim detection (`_readme_claims`), surface resolution
  (`_claim_surfaces`), and bounded surface evidence (`_surface_evidence`),
  plus the report findings. Reuse `DEFAULT_EXCLUDED_DIRS`,
  `LANGUAGE_EXTENSIONS`, `_is_path_safe`, `_is_excluded` and `redact`.
- `scripts/workspace_check.py` — add `validate_readme_claims`, called from
  `validate_project` for every registered project; declare
  `QUALITY_README_CLAIM_CONTRADICTED` and `QUALITY_README_CLAIM_UNSCOPED`.
- `schemas/project.schema.json` — additive `readme_claims` block, not in
  `required`, with `additionalProperties: false`.
- `docs/product-code-quality.md` — the new rule, the surface table, the two
  codes, and the measured corpus.
- `README.md` — one short paragraph; link rather than restate.
- `tests/test_readme_claim_verification.py` (new).

**Must not change:** every sibling repository; `capabilities.json`,
`decisions.json`, `projects.json`, `deployment/promotions.json`,
`scripts/promote_project.py`, the `quality` block's existing fields and
their validation, the `standalone` and `release_evidence` blocks,
`scripts/forge_governance_adapter.py`, and every existing
`placeholder_markers` / `secret_field_substrings` entry.

## 2. Language and runtime

Python **3.11**, standard library only.

- `python3 -m unittest discover -s tests -v`
- `python3 scripts/product_code_quality.py <project_dir> --json`
- `python3 scripts/workspace_check.py --root .. --audit --json`
- `python3 scripts/workspace_check.py --self-check`
- `node scripts/check-openspec-change-names.mjs`
- `openspec validate readme-claim-verification --strict`
- `git diff --check`

## 3. Ownership and shared code

- **Owner:** `workspace-governance`. `product_code_quality.py` is the
  existing shared owner of bounded, per-repository, read-only checks; this
  change adds a rule to it rather than creating a second checker.
- **Exported contract:** `vocabulary.json`
  `readme_claim_surfaces` and `readme_absence_phrases`.
- **Consumers:** `product_code_quality.py` (rule),
  `workspace_check.py` (finding translation), `driftwatchdog` when the
  governance check is bound as a gate check (deferred to that repository),
  and the Forge adapter through the unchanged `findings[]` array.
- **Dependency direction:** products → governance. The checker reads a
  sibling's files and writes none.
- **Release boundary:** ships with this repository.

## 4. The claim model

### 4.1 Claim detection

A **qualifying claim** is a sentence in `README.md` that satisfies all four
conditions:

1. it asserts **absence in the present tense of the repository's current
   state** — matched from `readme_absence_phrases` (`no application source`,
   `no source`, `nothing is implemented`, `not implemented`,
   `planning-only`, `planning artifacts only`, `specifications and
   documentation only`, `documentation only`, `does not exist yet`,
   `no … exists`, `remains to be built`);
2. it is **not** inside a fenced code block, an HTML comment, or a block
   quote;
3. it is **not** scoped to a future or hypothetical state (`the first
   release will be`, `once the solution exists, we will`,
   `is intended to`, `are planning decisions`);
4. it **names at least one surface** from `readme_claim_surfaces`, using
   `readme_absence_phrases`'s surface synonyms (§4.2).

Condition 4 is what separates a checkable claim from prose. A qualifying
claim resolves to a **set of surfaces**, and that set is the entire scope of
the verification. A claim that names six surfaces is tested on those six and
on nothing else. A claim that names none is not a claim about the
repository's implementation state and produces no contradicted finding.

### 4.2 Surfaces and their evidence

| Surface | Claim synonyms | Bounded evidence (read-only) |
|---|---|---|
| `application-source` | application source, extension application, source, implementation | ≥1 file with an extension in `LANGUAGE_EXTENSIONS` under a source root (`src`, `lib`, `app`, `apps`, `packages`, `tools`, `cmd`, `internal`, `server`, `client`) or the repository root, excluding `DEFAULT_EXCLUDED_DIRS` |
| `repository-content` | planning artifacts only, specifications and documentation only, documentation only, nothing is implemented | the same census as `application-source`, but not limited to a source root — a document-only tree has no source root at all |
| `build` | build | ≥1 `*.sln`, `*.slnx`, `*.csproj`, `Cargo.toml`, `package.json`, `pyproject.toml`, `go.mod`, `pubspec.yaml`, or `CMakeLists.txt` |
| `test` | tests, test suite, test project | a `tests`, `test`, `__tests__` or `spec` root, a `*.Tests/*.csproj`, a `tests` target in a solution, or a file matching a language's test pattern |
| `ci` | CI, CI configuration, CI workflow, pipeline | `.github/workflows/`, `Jenkinsfile`, `.gitlab-ci.yml`, `azure-pipelines.yml`, `.circleci/` |
| `runtime` | runtime, product runtime, runtime integration, running application | a runnable entry point (`Program.cs`, `main.py`, `index.ts`, `main.go`, `cmd/`, `bin/`, an `ENTRYPOINT`/`CMD` in a `Dockerfile`) |
| `api` | API, HTTP API, endpoints | a `*Controller.cs`, `routes/`, `api/`, `openapi*.y(a)ml`, `swagger*.y(a)ml`, or a framework entry point that serves HTTP |
| `web-client` | web client, web UI, frontend, SPA | a `client`, `web`, `frontend`, `wwwroot` or `ui` root, or a `package.json` declaring a UI framework |
| `mobile-client` | mobile client, mobile app, Flutter client | `pubspec.yaml` with a Flutter SDK constraint, `*.xcodeproj`/`*.xcworkspace`, an `android`+`ios` pair, or `*.dart` outside `packages` |
| `migrations` | database migrations, migrations | a `migrations`, `Migrations`, `alembic` or `db/migrate` root, or `*.sql` inside one |
| `deployment` | deployment, deployment evidence | a `compose*.y(a)ml` at any depth, a `deployment/` root with a compose or template, or a `deployment.compose_file` in the declaration that resolves |
| `provider-integration` | provider integration, provider, sibling platform integration | a `capabilities[].consumes[]` record, or a pinned `Platform.*` / sibling package in `Directory.Packages.props`, `*.csproj`, `package.json`, `Cargo.toml` or `pyproject.toml` — reusing `read_manifest_dependencies` |
| `production-evidence` | production evidence, production verification, release evidence, published, released | a `release_evidence` block in the declaration, or a matching promotion-ledger entry |
| `data-set` | data set, dataset, seed data | **not decidable from a file tree** — always `QUALITY_README_CLAIM_UNSCOPED` unless the repository declares a data surface (open decision 3) |

`*.slnx` is in the `build` row because `rostera` ships `Rostera.slnx`; a rule
that recognised only `*.sln` would have missed one of the five surfaces that
contradicts that repository's claim.

### 4.3 The rule's control flow

```
read README.md
  -> extract qualifying claims (§4.1)
  -> for each claim, resolve its named surfaces (§4.2)
  -> for each named surface, evaluate bounded evidence
       present  -> QUALITY_README_CLAIM_CONTRADICTED  (ERROR,   one per surface)
       absent   -> no finding for that surface
       unknown  -> QUALITY_README_CLAIM_UNSCOPED      (WARNING, once per claim)
  -> if no qualifying claim and a non-qualifying negative status statement exists
       -> QUALITY_README_CLAIM_UNSCOPED                (WARNING, once per project)
```

One finding per contradicted surface, not per claim, because the remediation
differs per surface: `rostera` needs its claim corrected for source, build,
test, deployment and runtime, and a single "README is wrong" finding would
hide that. Each message names the README line number, the surface, and the
evidence path that contradicts it.

`readme_claims: {"mode": "off"}` short-circuits the whole rule for that
repository. `{"mode": "check", "surfaces": ["…"]}` extends the closed
vocabulary with repository-specific surfaces. A declaration with no
`readme_claims` block is checked, because the claim is the trigger.

## 5. The measured corpus

Nine repositories in the workspace carry negative status language. This is
the regression fixture, with the outcome this rule produces. It was measured
on 2026-10-03; the numbers are a bounded extension census, not a build.

| Repository | Claim line | Surfaces named | Evidence found | Expected outcome |
|---|---|---|---|---|
| `pluggify` | 9 | `application-source` | 112 `.ts`, `packages/shared/dist` | **ERROR** ×1 |
| `careBridge` | 17 | `application-source`, `runtime`, `deployment`, `provider-integration`, `production-evidence` | 32 `.cs` + `CareBridge.sln`; `src/CareBridge.Api/Program.cs`; `compose.yaml`; 7 pinned `Platform.*`; no `release_evidence` | **ERROR** ×4 |
| `testify` | 92 | `repository-content` | 97 source files (86 `.cs`, 10 `.py`), `testify.sln`, `tests/` | **ERROR** ×1 |
| `aesthra` | 13 | `application-source`, `build`, `test`, `ci`, `runtime` | 137 `.cs`; `Aesthra.sln`; `tests/`; `.github/workflows/governance.yml`; no entry point | **ERROR** ×4 |
| `reelio` | 31 | `application-source`, `test`, `ci`, `migrations`, `deployment` | `src/api` 78 `.cs` + `src/client` 9; `Reelio.Api/Program.cs`; `.github/workflows/ci.yml`; `Data/Migrations`; no tests root, no compose | **ERROR** ×3 |
| `shopifireman` | 17 | `repository-content` | 115 source files, 770 KB, under `apps/` and `packages/` | **ERROR** ×1 |
| `rostera` | 44 | `source`, `build`, `test`, `deployment`, `provider`, `runtime` | 354 `.cs` (1.5 MB); `Rostera.slnx`; `tests/`; `compose.yaml`; `Rostera.Api/Program.cs` + 2 controllers; no `Platform.*` pin | **ERROR** ×5 |
| `kairosa` | 11 | `runtime`, `data-set`, `api`, `web-client`, `mobile-client`, `production-evidence` | **none of the six present** — no entry point, no controller, no client, no data, no `release_evidence`. It has `tests/` and a CI workflow and claims neither | **no finding** |
| `chronicleaf` | 19 | none in the closed vocabulary (`GitHub integration`, `Evidence Bundles`, `screenshot capture`, `media storage`, `credential vault`, `AI generation`, `Markdown drafts`, `review/approval`, `export`, `Milestone Timeline`) | n/a | **WARNING** ×1 `QUALITY_README_CLAIM_UNSCOPED` |

Totals: **7 repositories contradicted, 19 contradicted surfaces, 1
untestable negative claim, 2 clean.** The remaining 72 registered
repositories must produce exactly the findings they produced before.

### 5.1 Two corpus facts that contradict the commissioning brief

Recorded here because the rule must be correct regardless of which
expectation is right, and because an implementer will hit both immediately.

1. **`chronicleaf` does not make a false claim.** Its `## Status` section
   states that five of 53 packages "are implemented, verified and archived",
   lists what the running system does today, and lists ten things that "does
   not exist yet". It is the most accurate status block in the workspace,
   and it is one of the four unregistered repositories. The rule must not
   fire `QUALITY_README_CLAIM_CONTRADICTED` on it.
2. **`reelio`, `shopifireman` and `rostera` are not honest stubs.** They were
   expected to be the must-not-fire set. They are not: `reelio` holds 87
   source files (1.17 MB) in `src/api` and `src/client` while its status line
   says it "contains no application source"; `shopifireman` holds 115 source
   files (770 KB) under `apps/` and `packages/` while it says it "contains
   planning artifacts only"; `rostera` holds 354 `.cs` files under `src/` and
   `tests/` while it says "No source, build, test, deployment … exists yet".
   All three claims are as stale as the seven. The genuinely honest
   must-not-fire cases are `kairosa` and `chronicleaf`, and both are honest
   for different reasons — `kairosa` because its claim is *scoped* to six
   surfaces that are genuinely absent, `chronicleaf` because it makes no
   checkable absence claim at all.

`kairosa` is the case that decides the design. Its repository contains 22
`.cs` files and 124 passing xUnit tests, and its status line is accurate,
because the line scopes its absence to *product runtime, data set, API, web
client, mobile client and production verification* — six surfaces, all
absent. A rule that evaluated "the README says something is not implemented"
against a repository-wide file count would fire on it and would be wrong.
Claim scope is therefore a requirement, not an implementation detail.

## 6. Contract and compatibility

- `vocabulary.json` gains `readme_claim_surfaces` and
  `readme_absence_phrases`. Both are non-empty and duplicate-free;
  `schema_version` stays `1` and no existing array changes.
- New codes, extending the existing `QUALITY_*` family used by
  `validate_product_quality`. Neither collides with a code already in use
  (`QUALITY_POLICY`, `QUALITY_TEST_CODE`, `QUALITY_PLACEHOLDER`,
  `QUALITY_FAILURE`, `QUALITY_REVIEW_REQUIRED`):

| Code | Level | Fires when |
|---|---|---|
| `QUALITY_README_CLAIM_CONTRADICTED` | ERROR | a surface named by a qualifying README claim is present in the file tree; one per surface, naming line, surface, and evidence path |
| `QUALITY_README_CLAIM_UNSCOPED` | WARNING | a negative status statement names no surface the checker can resolve, or names a surface with no decidable evidence rule; never a pass |

- The rule id inside the checker is `readme-status-claim`, following the
  existing `product-test-code` and `placeholder-threshold` convention.
- `PASS`, `FAIL` and `REVIEW_REQUIRED` keep their meanings; exit codes 0/1/2
  are unchanged; the report schema is unchanged. `FAIL` promotes to ERROR
  and `REVIEW_REQUIRED` to WARNING through the same translation the existing
  rules use.
- The declaration schema gains an **additive, optional** `readme_claims`
  block: `{"mode": "off"}` or `{"mode": "check", "surfaces": [...]}`, with
  `additionalProperties: false`. It is not added to `required`, so all 81
  existing declarations remain valid.
- A README is prose. This change MUST NOT alter any `lifecycle`,
  `evidence_status`, `deployable` flag, promotion-ledger entry, capability
  adoption posture, or `verification.evidence_status`. The documented
  invariant is preserved verbatim: `workspace_check.py` does not promote a
  capability to verified on its own, and a sentence in a README does not
  either.
- The existing `quality` block is untouched. A repository with no `quality`
  block is still checked, because the claim is the trigger — only 2 of 81
  declarations carry a `quality` block, so gating on it would leave 79
  repositories unexamined.

## 7. Failure and boundary policy

| Case | Result |
|---|---|
| `README.md` absent | no claim, no finding. `REQUIRED_FILE` owns the missing-file case for profiles that require it |
| `README.md` unreadable or not valid UTF-8 | `QUALITY_README_CLAIM_UNSCOPED` WARNING naming the file; never a pass, never an ERROR the owner cannot act on |
| `README.md` above the bounded read size (64 KiB) | the first 64 KiB is read and the finding message states that the file was truncated; a claim in the tail produces no finding, and that absence is reported as `QUALITY_README_CLAIM_UNSCOPED` |
| claim inside a fenced code block, HTML comment, or block quote | not a claim; no finding |
| claim in the future tense or scoped to a release that does not exist yet | not a claim; no finding. This is what keeps `rostera/README.md:20` out and lets `:44` carry the finding |
| claim names a surface with no evidence rule (`data-set`) | `QUALITY_README_CLAIM_UNSCOPED` WARNING naming the surface; the claim is reported as untested, not as true |
| claim names only unknown surfaces (`chronicleaf`) | `QUALITY_README_CLAIM_UNSCOPED` WARNING once for the project |
| claim names a surface that is absent | no finding for that surface; the claim is verified as far as it goes |
| two claims in one README disagree with each other | both are evaluated; each contradicted surface is reported once, against the first claim that names it, and the message names both line numbers |
| `readme_claims: {"mode": "off"}` | the rule does not run for that repository and no claim finding is produced |
| `readme_claims: {"mode": "check", "surfaces": ["x"]}` | `x` is added to the closed vocabulary for that repository only; the global vocabulary is unchanged |
| a `surfaces` entry is not a string, or `mode` is not `off`/`check` | `QUALITY_REVIEW_REQUIRED` WARNING naming the invalid field, following the existing `QUALITY_POLICY` pattern for an invalid policy |
| a path escape (`..`) or absolute path in any configuration | refused by the existing `_is_path_safe`; never normalized |
| a symlinked directory in the walk | not followed, matching `discover_projects` |
| `vocabulary.json` missing, unparseable, or with an empty surface list | hard non-zero exit naming the file; an empty surface list would make every claim vacuously true |

## 8. Verification oracle

- `python3 -m unittest discover -s tests -v` — all pass, including the nine
  corpus fixtures in `tests/test_readme_claim_verification.py`, and no
  existing test changes expectation.
- **Corpus assertion:** the nine-repository fixture set produces exactly
  7 contradicted projects, 19 contradicted surfaces, 1
  `QUALITY_README_CLAIM_UNSCOPED`, and 2 clean projects, matching §5.
- **Must-not-fire assertion:** `kairosa` and `chronicleaf` produce no
  `QUALITY_README_CLAIM_CONTRADICTED`, and the `kairosa` fixture passes even
  though its repository contains source files and a test suite.
- **Additivity assertion:** the other 72 registered repositories produce a
  finding set identical to the pre-change baseline.
- **Read-only proof:** a recursive tree hash of a fixture project is
  identical before and after, and no child process is spawned.
- `python3 scripts/product_code_quality.py <project_dir> --json` — one
  parseable report, correct exit code, and `redact` applied to every message.
- `python3 scripts/workspace_check.py --root .. --audit --json` — 0 errors
  after the seven repositories have corrected their claims; the
  pre-correction output showing 7 contradicted projects is recorded, not
  hidden.
- `python3 scripts/workspace_check.py --self-check` — 0 errors, 0 warnings
  for the governance repository itself.
- `node scripts/check-openspec-change-names.mjs`,
  `openspec validate readme-claim-verification --strict`, `git diff --check`.
- Record actual outputs. Any environment-blocked check is reported with its
  exact next action, never as passing.

## 9. Decision ledger

**Assumptions:** a README is prose and is never edited by this repository; a
claim is verified only against the surfaces it names; a claim that cannot be
evaluated is reported as untested rather than assumed true; the tree is
stronger evidence than prose for "does source exist", and weaker for
everything else.

**Resolved alternatives:**

- (a) A new checker vs a rule in `product_code_quality.py` → chose
  **a rule in the existing checker**. It already has the bounded walk, the
  excluded-directory set, the extension census, the fail-closed report
  vocabulary, and the in-process bridge. A second checker would duplicate all
  of it.
- (b) Gate the rule behind the `quality` block → chose **not to gate it**.
  Only 2 of 81 declarations carry that block; gating would leave 79
  repositories unchecked and the rule effectively dead. The claim is the
  trigger, and the invocation follows the unconditional `validate_kind`
  precedent.
- (c) Repository-wide file count vs claim-scoped surface evidence → chose
  **claim-scoped**. Measured: `kairosa` has 39 source files, a test suite
  and a CI workflow and its status line is accurate, because it scopes its
  absence to six absent surfaces. A repository-wide rule fires on the most
  honest status block in the workspace.
- (d) Auto-rewrite the README → chose **detect only**. Rewriting a sibling's
  prose is a cross-repository source edit that `AGENTS.md` forbids without
  authorization, and the checker cannot know which side of the contradiction
  is wrong.
- (e) Drop an unverifiable claim silently vs report it → chose
  **report it** as `QUALITY_README_CLAIM_UNSCOPED`. Silence makes an
  untestable claim indistinguishable from a verified one, which is the
  failure mode this change exists to remove.
- (f) One finding per claim vs per contradicted surface → chose **per
  surface**. `rostera` contradicts five surfaces with five different
  remediations; one finding would hide four of them.
- (g) Merge with `identity-and-taxonomy-axis-split` → chose **separate**;
  see the package boundary table.

**Deferred:** a `data-set` evidence rule (open decision 3); binding the rule
as a `driftwatchdog` gate check (owned by that repository); reporting the
contradiction count per repository in `maturity_audit.py` (display only, and
only after the seven are repaired); and any automated suggestion of
replacement README wording.

**Blockers:** none. Open decisions 1–3 are policy choices that change levels
and vocabulary membership, not the rule's shape, and each is reversible
without touching the detection logic. Open decisions 4 and 5 are
sequencing and reporting choices for the owner, outside this package.

## Traceability

| Requirement | Proposal outcome | Design decision | Implementation boundary | Scenarios | Tasks | Oracle |
|---|---|---|---|---|---|---|
| R1 A status claim is detectable | qualifying-claim definition | §4.1 | `product_code_quality.py` | present tense / future tense / code block | 2.1, 2.2 | claim fixtures |
| R2 A claim is verified against the file tree | surface evidence rules | §4.2, §4.3 | `product_code_quality.py` | surface present / absent / unknown | 2.3 | corpus: 19 contradicted surfaces |
| R3 Claim scope is respected | only named surfaces are tested | §4.1, §5.1 | `product_code_quality.py` | `kairosa` clean / subset claim | 2.3, 3.2 | `kairosa` fixture has no contradicted finding |
| R4 A contradiction is a finding | `QUALITY_README_CLAIM_CONTRADICTED` | §6, §7 | `validate_readme_claims` | per-surface finding / first line wins | 2.4, 2.5 | 7 contradicted projects |
| R5 An unverifiable claim is not a pass | `QUALITY_README_CLAIM_UNSCOPED` | §4.3, §7 | `validate_readme_claims` | unknown surface / unreadable / truncated | 2.5 | 1 warning in the corpus |
| R6 The rule is additive and claim-triggered | 72-silent baseline | §4.3, §6 | `validate_project`, `readme_claims` block | no claim / `mode: off` / invalid config | 2.6, 3.1 | identical findings for 72 repositories |
| R7 Documentation claims never change evidence | prose is not evidence | §6 | none — invariant | contradicted claim with `deployable: true` | 3.4 | no evidence-state change |
