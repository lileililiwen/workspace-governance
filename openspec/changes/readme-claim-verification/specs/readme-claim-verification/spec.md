## ADDED Requirements

### Requirement: A present-tense absence claim in a README is detectable

Workspace Governance SHALL detect a README statement that asserts the
absence of implementation in the present tense of the repository's current
state, and SHALL resolve that statement to the set of surfaces it names.
A statement inside a fenced code block, an HTML comment, or a block quote
SHALL NOT be a claim, and a statement scoped to a future, hypothetical, or
unbuilt state SHALL NOT be a claim. A statement that names no surface from
the canonical surface vocabulary SHALL NOT be treated as a claim about the
repository's implementation state.

#### Scenario: A present-tense claim is detected

- **WHEN** a README contains the sentence "No application source, runtime,
  deployment, provider integration, or production evidence exists"
- **THEN** the checker resolves one claim naming five surfaces and records
  the README line number

#### Scenario: A future-tense statement is not a claim

- **WHEN** a README contains "The first release is planning-only in this
  repository" alongside "No source, build, test, deployment, provider, or
  runtime integration exists yet"
- **THEN** the first statement is not a claim and produces no finding, and
  the second statement is a claim naming six surfaces

#### Scenario: A statement inside a code block is not a claim

- **WHEN** the only occurrence of an absence phrase is inside a fenced code
  block, an HTML comment, or a block quote
- **THEN** the checker reports no claim for that repository

#### Scenario: A statement naming no known surface is not a claim

- **WHEN** a README lists ten things that "does not exist yet" and none of
  the ten is a canonical surface
- **THEN** the checker records no claim about the repository's
  implementation state

### Requirement: A claim is verified against the file tree, scoped to the surfaces it names

A claim SHALL be verified only against the surfaces it names, and a surface
SHALL be treated as present only when bounded, read-only evidence exists
for it inside the repository. The checker SHALL NOT evaluate a surface the
claim does not name, and SHALL NOT derive a contradiction from a
repository-wide file count. A positive claim, a claim about implemented
behaviour, and a claim about a future release SHALL NOT be verified. No
project command SHALL be executed, no package manager SHALL be invoked, and
no network request SHALL be made.

#### Scenario: A named surface is absent

- **WHEN** a claim names the `mobile-client` surface and the repository has
  no `pubspec.yaml`, no Apple project, and no `android` and `ios` pair
- **THEN** the claim is verified for that surface and no finding is reported
  for it

#### Scenario: Only the named surfaces are tested

- **WHEN** a claim denies only the `api` surface and the repository also
  ships a web client
- **THEN** the checker reports the `api` contradiction if the API surface is
  present, and reports nothing about the web client

#### Scenario: A scoped claim is verified against a populated repository

- **WHEN** a README states "No product runtime, data set, API, web client,
  mobile client, or production verification exists yet" and the repository
  contains a domain library, a test suite, and a CI workflow
- **THEN** the six named surfaces are evaluated, and no contradicted surface
  is reported

#### Scenario: A positive claim is not verified

- **WHEN** a README states that five of fifty-three packages are implemented,
  verified, and archived
- **THEN** the checker reports no claim and no finding for that statement

#### Scenario: The walk is bounded and read-only

- **WHEN** the checker evaluates any surface
- **THEN** it reads only the repository's own files, excludes generated,
  vendored, and dependency directories, follows no symlink, writes nothing,
  and spawns no child process

### Requirement: A claim contradicted by the tree is a finding

A claim naming a surface that bounded evidence shows to be present SHALL be
reported as ERROR `QUALITY_README_CLAIM_CONTRADICTED`, with one finding per
contradicted surface naming the README line, the surface, and the evidence
path that contradicts it. When two claims name the same surface, the surface
SHALL be reported once against the first claim that names it. A
documentation claim SHALL NOT change any project's lifecycle, evidence
status, deployable flag, promotion state, or capability adoption posture,
and SHALL NOT promote a capability to verified.

#### Scenario: An absence claim is contradicted

- **WHEN** a README states that no application source exists and the
  repository contains 112 TypeScript files under a source root
- **THEN** the audit reports ERROR `QUALITY_README_CLAIM_CONTRADICTED` naming
  the README line, the `application-source` surface, and the evidence path

#### Scenario: Each contradicted surface is reported separately

- **WHEN** a README denies six surfaces and the tree evidences five of them
- **THEN** the audit reports five findings, one per contradicted surface,
  each naming the same README line and a different evidence path

#### Scenario: One surface is reported once

- **WHEN** two separate claims in one README both deny the `ci` surface and
  the tree contains a CI workflow
- **THEN** one finding is reported for `ci`, naming both README line numbers

#### Scenario: Evidence state is unaffected

- **WHEN** a repository has a contradicted README claim and declares
  `deployable: true` with a matching promotion-ledger entry
- **THEN** its lifecycle, evidence status, deployable flag, promotion entry,
  and capability adoption posture are exactly what they were before the
  check ran

### Requirement: A claim that cannot be resolved is reported, never passed

A negative status statement that names no canonical surface, a claim naming
a surface for which no decidable evidence rule exists, an unreadable or
truncated README, and a repository whose only negative status statements
fail the claim conditions SHALL be reported as WARNING
`QUALITY_README_CLAIM_UNSCOPED` naming the statement or the surface. An
unresolved claim SHALL NOT be reported as verified, and SHALL NOT be
reported as contradicted. A repository with no `README.md` SHALL produce no
claim finding.

#### Scenario: A claim names an undecidable surface

- **WHEN** a claim names the `data-set` surface and no evidence rule exists
  for it
- **THEN** the audit reports WARNING `QUALITY_README_CLAIM_UNSCOPED` naming
  the surface, and no contradicted finding for that surface

#### Scenario: A negative list names no canonical surface

- **WHEN** a README lists ten absent features and none is a canonical
  surface
- **THEN** the audit reports WARNING `QUALITY_README_CLAIM_UNSCOPED` once for
  the project and no contradicted finding

#### Scenario: The README cannot be read

- **WHEN** a `README.md` exists but is not valid UTF-8
- **THEN** the audit reports WARNING `QUALITY_README_CLAIM_UNSCOPED` naming
  the file, and does not report the claim as verified

#### Scenario: The README is truncated by the read bound

- **WHEN** a `README.md` exceeds the bounded read size and an absence
  statement appears beyond the bound
- **THEN** the finding states that the file was truncated at the bound and no
  claim beyond it is reported as verified

#### Scenario: No README at all

- **WHEN** a repository has no `README.md`
- **THEN** the audit reports no claim finding for that repository

### Requirement: The claim check is additive and claim-triggered

The claim check SHALL run for every registered project and SHALL be
triggered by the presence of a qualifying claim, not by an opt-in
declaration. A repository whose README contains no qualifying claim SHALL
produce exactly the findings it produced before this capability existed. A
declaration MAY carry an additive `readme_claims` block whose `mode` is
`off`, which suppresses the rule for that repository, or `check`, which adds
repository-specific surfaces; the block SHALL NOT be required, and an
invalid `mode` or a non-string `surfaces` entry SHALL be reported as
WARNING `QUALITY_REVIEW_REQUIRED` without disabling the rule or enabling an
unknown surface.

#### Scenario: A repository with no claim is silent

- **WHEN** a repository's README contains no qualifying claim
- **THEN** the audit produces no `QUALITY_README_CLAIM_*` finding for it and
  its remaining findings are identical to the pre-change baseline

#### Scenario: The baseline is unchanged across the fleet

- **WHEN** the check runs over every registered repository and the
  repositories that contain no qualifying claim are counted
- **THEN** each of those repositories produces a finding set identical to the
  one it produced before this capability existed

#### Scenario: Opting out

- **WHEN** a declaration carries `readme_claims` with `mode` set to `off`
- **THEN** no claim finding is produced for that repository and the file tree
  is not walked

#### Scenario: Extending the surface set per repository

- **WHEN** a declaration carries `readme_claims` with `mode` set to `check`
  and a `surfaces` entry naming a repository-specific surface
- **THEN** that surface is evaluated for that repository only, and the
  canonical surface vocabulary is unchanged

#### Scenario: An invalid claim configuration

- **WHEN** a declaration carries `readme_claims` with `mode` set to `audit`
  or with a non-string `surfaces` entry
- **THEN** the audit reports WARNING `QUALITY_REVIEW_REQUIRED` naming the
  invalid field, and falls back to the canonical behaviour

## MODIFIED Requirements

### Requirement: Emit bounded machine-readable findings

The checker MUST emit one versioned JSON document containing status, summary,
relative paths, line numbers, rule IDs, bounded diagnostics, and exit-code
compatible remediation without exposing configured secrets. The `readme-
status-claim` rule MUST participate in that same document, MUST report
findings by README line number and by contradicting evidence path, and MUST
pass every message through the existing redaction helper. Its statuses MUST
use the existing `PASS`, `FAIL` and `REVIEW_REQUIRED` vocabulary: a
contradicted claim is `FAIL`, an unresolvable claim is `REVIEW_REQUIRED`, and
a verified or absent claim produces no finding.

#### Scenario: JSON failure report

- **WHEN** a product boundary or threshold violation is found with `--json`
- **THEN** stdout contains one parseable report and the process exits 1

#### Scenario: JSON claim report

- **WHEN** a README claim is contradicted and the checker runs with `--json`
- **THEN** stdout contains one parseable report whose findings carry rule id
  `readme-status-claim`, the README line number, the contradicted surface,
  the evidence path, and no unredacted secret-shaped value

#### Scenario: Unreadable product file

- **WHEN** a declared product file cannot be read safely
- **THEN** the report is `REVIEW_REQUIRED` and the process exits 2

#### Scenario: An unresolvable claim is review-required, not a pass

- **WHEN** a claim names only surfaces with no decidable evidence rule
- **THEN** the report is `REVIEW_REQUIRED` and the process exits 2, and the
  report does not record the claim as verified
