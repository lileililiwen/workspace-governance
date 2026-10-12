# product-code-quality-boundary Specification

## Purpose

The portfolio currently declares generic build, test, and security concerns, but it has no shared, executable control that detects test or integration code leaking into product source or placeholder-heavy product code. A project can therefore report a structurally complete Gate while shipping code that is unfinished or placed in the wrong boundary. AI-generated changes make this failure mode common enough to require a deterministic repository check.
## Requirements
### Requirement: Declare product source boundaries

Workspace Governance MUST require an applicable product-quality check to name
at least one product source root, a supported language profile, and explicit
exclusions for generated, vendor, fixture, or other non-product paths.

#### Scenario: Valid product policy

- **WHEN** a project declares an existing source root, supported language, and
  non-escaping exclusions
- **THEN** the checker scans the declared product scope

#### Scenario: Missing product policy

- **WHEN** a project enables the check without product roots or with an
  unsupported language
- **THEN** the result is `REVIEW_REQUIRED` with configuration remediation

### Requirement: Reject test code in product scope

The quality checker SHALL report a test call found in product scope as
`product-test-code` at ERROR, and SHALL NOT report a call that is not a test.

For TypeScript and JavaScript, the checker SHALL match `describe`, `it` and
`test` only when the call is made on a **bare identifier** — the framework
global. A call on any expression is a method on that expression, and a method
named `test` is a method: a regular expression literal, a compiled `RegExp`, or
a `String` method are all product code. A comment line SHALL NOT be matched at
all, because a comment cannot call anything.

#### Scenario: Rust cfg test module

- **WHEN** a Rust product file contains a test module under `#[cfg(test)]`
- **THEN** the test module is allowed and produces no boundary finding

#### Scenario: Rust integration code in source

- **WHEN** a Rust product file contains an integration-test module or test-only
  imports outside `#[cfg(test)]`
- **THEN** the checker reports `product-test-code` as `FAIL`

#### Scenario: Non-Rust test module

- **WHEN** a Python, TypeScript, C#, or supported product file contains a
  recognized test-only module/file pattern
- **THEN** the checker reports `product-test-code` as `FAIL`

#### Scenario: A framework global in product scope

- **WHEN** a `.ts` file in product scope contains `describe('x', () => {})`,
      `it('y', () => {})` or `test('z', () => {})` on a bare identifier
- **THEN** the checker reports one `product-test-code` finding at ERROR

#### Scenario: A regular expression is not a test

- **WHEN** a line contains `/pattern/.test(value)` or `PATTERN.test(value)`
- **THEN** the checker reports nothing

#### Scenario: A String method is not a test

- **WHEN** a line contains `"text".test(value)`
- **THEN** the checker reports nothing

#### Scenario: An optional-chained member call is not a test

- **WHEN** a line contains `re?.test(body)`
- **THEN** the checker reports nothing

#### Scenario: Prose about a test file is not a test

- **WHEN** a comment line names a `*.test.ts` file
- **THEN** the checker reports nothing

#### Scenario: A longer identifier is not a test

- **WHEN** a line contains `contest(1)` or `const latest = compute()`
- **THEN** the checker reports nothing, because the identifier is not `test`

#### Scenario: The rule is still live

- **WHEN** the qualifier anchor were removed to silence the cases above
- **THEN** the bare-call scenarios above would be reported as clean, and a test
      asserting they are still reported would fail

### Requirement: Enforce placeholder threshold

The checker MUST count configured placeholder markers only within product
scope and MUST return `FAIL` when the count exceeds the declared threshold.

#### Scenario: Threshold met

- **WHEN** the product marker count is at or below the configured threshold
- **THEN** the placeholder check passes and reports the count

#### Scenario: Threshold exceeded

- **WHEN** the product marker count is above the configured threshold
- **THEN** the checker reports `placeholder-threshold` as `FAIL` with per-file
  counts and remediation

#### Scenario: Excluded fixture marker

- **WHEN** a marker appears only in an explicitly excluded fixture or generated
  path
- **THEN** it does not count toward the product threshold

### Requirement: Emit bounded machine-readable findings

The checker MUST emit one versioned JSON document containing status, summary,
relative paths, line numbers, rule IDs, bounded diagnostics, and exit-code
compatible remediation without exposing configured secrets.

#### Scenario: JSON failure report

- **WHEN** a product boundary or threshold violation is found with `--json`
- **THEN** stdout contains one parseable report and the process exits 1

#### Scenario: Unreadable product file

- **WHEN** a declared product file cannot be read safely
- **THEN** the report is `REVIEW_REQUIRED` and the process exits 2

