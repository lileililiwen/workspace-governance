# Product-Code Quality Gate

The product-code quality gate is a portable, deterministic repository
checker owned by Workspace Governance. It detects two failure modes that
the existing structural audit cannot:

- **Test code in product scope.** Code that ships in the product
  source root but is really a test. For Rust the check is lexical:
  `#[test]` or `mod tests` outside a `#[cfg(test)]` guard is rejected.
  Python, TypeScript, C#, and Go use the recognised file/import patterns
  of each language.
- **Placeholder debt in product scope.** Maintainer-visible markers
  such as `TODO`, `FIXME`, `XXX`, `HACK`, `placeholder`, `stub`,
  `unimplemented!`, and `todo!` are counted across product files. The
  count is compared against a configured threshold; the default for
  newly adopted product roots is **zero**.

The gate is fail-closed: a missing or invalid `quality` block, an
unsupported language, an exclusion that escapes the project root, or an
unreadable product file is `REVIEW_REQUIRED`, never a guessed pass.

## How a project opts in

Add a `quality` block to the project's `.project.json`:

```json
{
  "quality": {
    "product_roots": ["src"],
    "languages": ["rust"],
    "exclude": ["src/generated", "src/fixtures"],
    "placeholder_threshold": 0
  }
}
```

| Field                  | Required | Meaning                                                                                                  |
|------------------------|----------|----------------------------------------------------------------------------------------------------------|
| `product_roots`        | yes      | Repository-relative directories that count as product source. Each must exist and be a directory.        |
| `languages`            | yes      | One or more of `rust`, `python`, `typescript`, `javascript`, `csharp`, `go`, `generic`.                  |
| `exclude`              | no       | Repository-relative paths under any product root to exclude. Must not escape the project root.            |
| `placeholder_threshold`| no       | Integer count of tolerated markers across product files. Default `0`.                                    |
| `placeholder_markers`  | no       | Override the default marker vocabulary. Words are matched case-insensitively with word boundaries.        |

## Running the checker directly

The checker is a normal command; Driftwatchdog binds it as a Gate check.

```bash
python3 scripts/product_code_quality.py <project_dir>            # human output
python3 scripts/product_code_quality.py <project_dir> --json     # versioned JSON report
python3 scripts/product_code_quality.py <project_dir> --policy <path>
```

Exit codes:

| Code | Meaning                                                                                          |
|------|--------------------------------------------------------------------------------------------------|
| `0`  | PASS — no blocking finding, no review-required gap.                                              |
| `1`  | FAIL — test code in product scope, or the placeholder count exceeds the configured threshold.    |
| `2`  | REVIEW_REQUIRED — missing or invalid policy, unreadable product file, or any other manual-review gap. |

## The JSON contract

```json
{
  "schema_version": 1,
  "status": "PASS | FAIL | REVIEW_REQUIRED",
  "project": "project-name",
  "summary": {
    "test_code": 0,
    "placeholder": 0,
    "errors": 0,
    "warnings": 0,
    "files_scanned": 0,
    "files_unreadable": 0,
    "excluded_paths": 0
  },
  "findings": [
    {
      "rule_id": "product-test-code | placeholder-marker",
      "level": "ERROR | WARNING",
      "severity": "FAIL",
      "file": "src/lib.rs",
      "line": 4,
      "marker": "#[test]",
      "remediation": "..."
    }
  ],
  "notes": ["..."]
}
```

## Audit integration

When a project declaration has a `quality` block, the workspace audit
(`workspace_check.py`) imports the checker in-process and translates
the report into its existing Finding vocabulary:

- `FAIL` → `ERROR` (codes `QUALITY_TEST_CODE`, `QUALITY_PLACEHOLDER`,
  `QUALITY_FAILURE`)
- `REVIEW_REQUIRED` → `WARNING` (codes `QUALITY_REVIEW_REQUIRED`,
  `QUALITY_POLICY`)
- `PASS` → no finding

Projects that omit the `quality` block continue to pass unchanged; the
rule is opt-in.

## Default exclusions

The checker ignores the following directory segments everywhere inside
a product root, so projects do not need to repeat them:

`tests`, `test`, `__tests__`, `spec`, `specs`, `node_modules`, `vendor`,
`target`, `build`, `dist`, `out`, `.git`, `fixtures`, `fixture`,
`example`, `examples`, `generated`, `.github`, `.gitlab`.

The default list is restricted to universally non-product paths
(test, fixture, generated, vendor, build). Projects that store code in
`scripts/`, `docs/`, `deployment/`, `schemas/`, or `templates/` opt in
to scanning them by listing them in `product_roots` and any non-product
subtree in `exclude`.

## Language rules

- **Rust** — `#[test]` or `mod tests` outside a `#[cfg(test)]` guard.
  `#[cfg(any(test, ...))]` and `#[cfg(all(test, ...))]` do not authorise
  test scope. Repository `tests/` is always outside product scope.
- **Python** — `import unittest`/`from unittest`/`import pytest`/`from
  pytest` imports, or `def test_*` definitions in non-`test_*.py` files.
- **TypeScript / JavaScript** — `describe(`, `it(`, or `test(` calls in
  non-`.test.*` / non-`.spec.*` files. Files matching the test glob are
  excluded by path policy.
- **C#** — `[Test]`, `[TestMethod]`, `[Fact]`, `[Theory]` attributes.
- **Go** — `*_test.go` files (excluded by path policy).
- **Generic** — file-name heuristic: `test_*`, `*_test`, `*.test.*`,
  `*.spec.*` filenames anywhere in product scope.

## Ownership

| Surface                                  | Owner                                                |
|------------------------------------------|------------------------------------------------------|
| Checker, vocabulary, exit codes, contract| Workspace Governance (this repository).              |
| Quality policy and exclusions            | Each product repository via `.project.json` quality. |
| `product_roots`, `languages`, threshold  | Project owner, declared locally.                     |
| Gate execution                           | Driftwatchdog, via the existing Gate binding.        |
| Audit translation to `Finding`           | Workspace Governance audit (`workspace_check.py`).   |

## Non-goals

- No automatic code repair, test generation, or AI judgment.
- No claim that a passing lexical check proves behaviour, integration,
  release, or runtime quality.
- No universal ban on tests in a repository; test roots remain first-class.
- No hard-coded assumption that every project uses Rust, Python, .NET,
  or JavaScript; the `generic` profile covers everything else.
- No replacement for Driftwatchdog's Gate executor; the checker is one
  of the checks Driftwatchdog binds.
