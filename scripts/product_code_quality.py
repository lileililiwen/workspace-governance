#!/usr/bin/env python3
"""Portable product-code quality checker owned by Workspace Governance.

Detects test code in product source roots and counts placeholder markers.
Designed to be invoked both in-process (by the audit) and as a standalone
command (by Driftwatchdog Gate bindings and CI).

Exit codes
----------
0  no blocking finding, no review-required gap
1  quality failure: test code in product scope, or threshold exceeded
2  configuration error: missing or invalid policy, unreadable product file,
   or any other condition that must be reviewed manually

The checker is fail-closed: a missing product_roots block, an unsupported
language, an exclusion that escapes the project root, or an unreadable
product file is REVIEW_REQUIRED, never a guessed pass.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
LANGUAGES = ("rust", "python", "typescript", "javascript", "csharp", "go", "generic")

DEFAULT_PLACEHOLDER_MARKERS = (
    "todo",
    "fixme",
    "xxx",
    "hack",
    "placeholder",
    "stub",
    "unimplemented!",
    "todo!",
)

# Default test-scope and out-of-product directories. These are matched
# against path segments, not full paths, so they apply inside any root.
# The list is restricted to universally non-product paths (test, fixture,
# generated, vendor, build) so projects can opt-in to scanning their own
# `scripts`, `docs`, or `deployment` trees by naming them in product_roots.
DEFAULT_EXCLUDED_DIRS = frozenset({
    "tests",
    "test",
    "__tests__",
    "spec",
    "specs",
    "node_modules",
    "vendor",
    "target",
    "build",
    "dist",
    "out",
    ".git",
    "fixtures",
    "fixture",
    "example",
    "examples",
    "generated",
    ".github",
    ".gitlab",
})

# Per-language file-name patterns that always count as out of product scope.
LANGUAGE_EXCLUDED_GLOBS: dict[str, tuple[str, ...]] = {
    "python": ("test_*.py", "*_test.py"),
    "javascript": ("*.test.js", "*.spec.js", "*.test.jsx", "*.spec.jsx"),
    "typescript": ("*.test.ts", "*.spec.ts", "*.test.tsx", "*.spec.tsx"),
    "go": ("*_test.go"),
}

# Per-language filename extension filter. Generic uses the full set.
LANGUAGE_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "rust": (".rs",),
    "python": (".py",),
    "typescript": (".ts", ".tsx"),
    "javascript": (".js", ".jsx", ".mjs", ".cjs"),
    "csharp": (".cs",),
    "go": (".go",),
    "generic": (),  # generic matches any text file
}

# Secret-like vocabulary that must never appear in a finding message.
SECRET_WORDS = re.compile(r"(password|secret|token|api[_-]?key|private[_-]?key|credential)", re.I)


@dataclass
class Policy:
    product_roots: tuple[str, ...]
    languages: tuple[str, ...]
    exclude: tuple[str, ...] = ()
    placeholder_threshold: int = 0
    placeholder_markers: tuple[str, ...] = DEFAULT_PLACEHOLDER_MARKERS
    root_dir: Path | None = None

    def with_root(self, root: Path) -> "Policy":
        return Policy(
            product_roots=self.product_roots,
            languages=self.languages,
            exclude=self.exclude,
            placeholder_threshold=self.placeholder_threshold,
            placeholder_markers=self.placeholder_markers,
            root_dir=root,
        )


@dataclass
class Finding:
    rule_id: str
    level: str  # ERROR | WARNING | INFO
    severity: str  # human-facing: FAIL | REVIEW_REQUIRED | PASS
    file: str
    line: int
    marker: str
    remediation: str

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Report:
    schema_version: int
    status: str  # PASS | FAIL | REVIEW_REQUIRED
    project: str
    summary: dict[str, int] = field(default_factory=lambda: {"test_code": 0, "placeholder": 0, "errors": 0, "warnings": 0, "files_scanned": 0, "files_unreadable": 0, "excluded_paths": 0})
    findings: list[Finding] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "project": self.project,
            "summary": self.summary,
            "findings": [f.to_json() for f in self.findings],
            "notes": list(self.notes),
        }


class ConfigError(ValueError):
    """Raised when policy is missing, invalid, or cannot be applied."""


# ---------------------------------------------------------------------------
# Policy parsing
# ---------------------------------------------------------------------------


def parse_policy(raw: dict[str, Any]) -> Policy:
    if not isinstance(raw, dict):
        raise ConfigError("quality must be an object")
    product_roots = raw.get("product_roots")
    if not isinstance(product_roots, list) or not product_roots:
        raise ConfigError("quality.product_roots must be a non-empty list of strings")
    roots: list[str] = []
    for entry in product_roots:
        if not isinstance(entry, str) or not entry:
            raise ConfigError("each product_roots entry must be a non-empty string")
        if entry.startswith("/") or ".." in Path(entry).parts:
            raise ConfigError(f"product_roots entry must be project-relative: {entry!r}")
        roots.append(entry)
    languages_raw = raw.get("languages")
    if not isinstance(languages_raw, list) or not languages_raw:
        raise ConfigError("quality.languages must be a non-empty list")
    languages: list[str] = []
    for entry in languages_raw:
        if not isinstance(entry, str) or entry not in LANGUAGES:
            raise ConfigError(f"unsupported language: {entry!r}; supported: {sorted(LANGUAGES)}")
        languages.append(entry)
    if len(set(languages)) != len(languages):
        raise ConfigError("quality.languages entries must be unique")
    exclude_raw = raw.get("exclude", [])
    if not isinstance(exclude_raw, list):
        raise ConfigError("quality.exclude must be a list of strings")
    exclude: list[str] = []
    for entry in exclude_raw:
        if not isinstance(entry, str) or not entry:
            raise ConfigError("each quality.exclude entry must be a non-empty string")
        if entry.startswith("/") or ".." in Path(entry).parts:
            raise ConfigError(f"quality.exclude entry must be project-relative: {entry!r}")
        exclude.append(entry)
    threshold = raw.get("placeholder_threshold", 0)
    if not isinstance(threshold, int) or isinstance(threshold, bool) or threshold < 0:
        raise ConfigError("quality.placeholder_threshold must be a non-negative integer")
    markers_raw = raw.get("placeholder_markers", list(DEFAULT_PLACEHOLDER_MARKERS))
    if not isinstance(markers_raw, list) or not markers_raw:
        raise ConfigError("quality.placeholder_markers must be a non-empty list")
    markers: list[str] = []
    for entry in markers_raw:
        if not isinstance(entry, str) or not entry:
            raise ConfigError("each quality.placeholder_markers entry must be a non-empty string")
        markers.append(entry)
    return Policy(
        product_roots=tuple(roots),
        languages=tuple(languages),
        exclude=tuple(exclude),
        placeholder_threshold=threshold,
        placeholder_markers=tuple(markers),
    )


def load_policy(declaration: dict[str, Any]) -> Policy:
    if "quality" not in declaration:
        raise ConfigError("project declaration is missing the 'quality' block")
    return parse_policy(declaration["quality"])


# ---------------------------------------------------------------------------
# Path classification
# ---------------------------------------------------------------------------


def _is_path_safe(rel: Path) -> bool:
    if rel.is_absolute():
        return False
    parts = rel.parts
    if not parts or parts[0] == "..":
        return False
    return True


def _is_excluded(rel: Path, exclude: Iterable[str], language: str) -> bool:
    parts = rel.parts
    for part in parts:
        if part in DEFAULT_EXCLUDED_DIRS:
            return True
    rel_posix = rel.as_posix()
    for raw in exclude:
        candidate = Path(raw)
        try:
            if rel == candidate or rel.is_relative_to(candidate):
                return True
        except ValueError:
            pass
        if candidate.as_posix() in rel_posix:
            return True
    for pattern in LANGUAGE_EXCLUDED_GLOBS.get(language, ()):
        if rel.match(pattern):
            return True
    return False


def _resolve_root(root_dir: Path, raw: str) -> Path:
    if not _is_path_safe(Path(raw)):
        raise ConfigError(f"product_roots entry must be project-relative: {raw!r}")
    candidate = (root_dir / raw).resolve(strict=False)
    base = root_dir.resolve()
    if not str(candidate).startswith(str(base)):
        raise ConfigError(f"product_roots entry escapes project root: {raw!r}")
    return candidate


def _resolve_exclude(root_dir: Path, raw: str) -> Path:
    if not _is_path_safe(Path(raw)):
        raise ConfigError(f"exclude entry must be project-relative: {raw!r}")
    candidate = (root_dir / raw).resolve(strict=False)
    base = root_dir.resolve()
    if not str(candidate).startswith(str(base)):
        raise ConfigError(f"exclude entry escapes project root: {raw!r}")
    return candidate


def _candidate_files(root: Path, language: str) -> Iterable[Path]:
    extensions = LANGUAGE_EXTENSIONS.get(language, ())
    if not extensions:
        # generic: every regular file
        for path in sorted(root.rglob("*")):
            try:
                if path.is_file() and not path.is_symlink():
                    yield path
            except OSError:
                continue
        return
    for ext in extensions:
        for path in sorted(root.rglob(f"*{ext}")):
            try:
                if path.is_file() and not path.is_symlink():
                    yield path
            except OSError:
                continue


# ---------------------------------------------------------------------------
# Test-code detection
# ---------------------------------------------------------------------------


def _scan_rust_test_code(path: Path, lines: list[str]) -> list[Finding]:
    """Detect `#[test]` or `mod tests` outside a `#[cfg(test)]` scope.

    The check is lexical: a single pass tracks brace depth and a stack of
    `#[cfg(test)]` guards. Any `#[test]` attribute or `mod tests` line that
    is not currently under a `#[cfg(test)]` guard is a finding.
    """
    findings: list[Finding] = []
    cfg_depths: list[int] = []  # depth at which a cfg(test) started
    brace_depth = 0
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("#[cfg(test)]"):
            cfg_depths.append(brace_depth)
            continue
        if "#[cfg(any(test" in stripped or "#[cfg(all(test" in stripped:
            # Ambiguous cfg: do not authorize as test scope.
            if re.search(r"#\s*\[\s*test\s*\]", stripped) and not cfg_depths:
                findings.append(Finding(
                    rule_id="product-test-code",
                    level="ERROR",
                    severity="FAIL",
                    file=path.name,
                    line=index,
                    marker=stripped,
                    remediation="move test code into a `#[cfg(test)]` module or into the project tests/ root",
                ))
        if re.search(r"#\s*\[\s*test\s*\]", stripped) and not cfg_depths:
            findings.append(Finding(
                rule_id="product-test-code",
                level="ERROR",
                severity="FAIL",
                file=path.name,
                line=index,
                marker=stripped,
                remediation="move test code into a `#[cfg(test)]` module or into the project tests/ root",
            ))
        if re.match(r"mod\s+tests\b", stripped) and not cfg_depths:
            findings.append(Finding(
                rule_id="product-test-code",
                level="ERROR",
                severity="FAIL",
                file=path.name,
                line=index,
                marker=stripped,
                remediation="place `mod tests` under a `#[cfg(test)]` attribute or move it to the project tests/ root",
            ))
        brace_depth += stripped.count("{") - stripped.count("}")
        while cfg_depths and brace_depth <= cfg_depths[-1]:
            cfg_depths.pop()
    return findings


def _scan_python_test_code(path: Path, lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("import unittest") or stripped.startswith("from unittest"):
            findings.append(Finding(
                rule_id="product-test-code",
                level="ERROR",
                severity="FAIL",
                file=path.name,
                line=index,
                marker=stripped,
                remediation="move unittest imports into a test_* file under the project tests/ root",
            ))
        if re.search(r"\bimport\s+pytest\b", stripped) or re.search(r"\bfrom\s+pytest\b", stripped):
            findings.append(Finding(
                rule_id="product-test-code",
                level="ERROR",
                severity="FAIL",
                file=path.name,
                line=index,
                marker=stripped,
                remediation="move pytest imports into a test_* file under the project tests/ root",
            ))
        if re.match(r"def\s+test_\w+", stripped) and not path.name.startswith("test_") and not path.name.endswith("_test.py"):
            findings.append(Finding(
                rule_id="product-test-code",
                level="ERROR",
                severity="FAIL",
                file=path.name,
                line=index,
                marker=stripped,
                remediation="rename the file to test_*.py or move the function into a test file under tests/",
            ))
    return findings


def _scan_typescript_test_code(path: Path, lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if re.search(r"\b(describe|it|test)\s*\(", stripped) and "import" not in stripped:
            findings.append(Finding(
                rule_id="product-test-code",
                level="ERROR",
                severity="FAIL",
                file=path.name,
                line=index,
                marker=stripped,
                remediation="move describe/it/test calls into a *.test.ts or *.spec.ts file under the project tests/ root",
            ))
    return findings


def _scan_csharp_test_code(path: Path, lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        for attr in ("[Test]", "[TestMethod]", "[Fact]", "[Theory]"):
            if attr in stripped:
                findings.append(Finding(
                    rule_id="product-test-code",
                    level="ERROR",
                    severity="FAIL",
                    file=path.name,
                    line=index,
                    marker=stripped,
                    remediation="move the test method into a separate test project",
                ))
                break
    return findings


def _scan_generic_test_code(path: Path, lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    lower_name = path.name.lower()
    if "test" in lower_name and (lower_name.startswith("test_") or lower_name.endswith("_test") or ".test." in lower_name or ".spec." in lower_name):
        findings.append(Finding(
            rule_id="product-test-code",
            level="ERROR",
            severity="FAIL",
            file=path.name,
            line=1,
            marker=path.name,
            remediation="rename or move the file out of the product root",
        ))
    return findings


LANGUAGE_TEST_SCANNERS = {
    "rust": _scan_rust_test_code,
    "python": _scan_python_test_code,
    "typescript": _scan_typescript_test_code,
    "javascript": _scan_typescript_test_code,
    "csharp": _scan_csharp_test_code,
    "go": _scan_generic_test_code,
    "generic": _scan_generic_test_code,
}


# ---------------------------------------------------------------------------
# Placeholder scanning
# ---------------------------------------------------------------------------


def _marker_pattern(markers: Iterable[str]) -> re.Pattern[str]:
    escaped = [re.escape(m) for m in markers]
    return re.compile(r"\b(" + "|".join(escaped) + r")\b", re.IGNORECASE)


def scan_placeholders(path: Path, lines: list[str], markers: Iterable[str]) -> list[Finding]:
    pattern = _marker_pattern(markers)
    findings: list[Finding] = []
    for index, line in enumerate(lines, start=1):
        for match in pattern.finditer(line):
            token = match.group(0)
            if SECRET_WORDS.search(token):
                continue
            findings.append(Finding(
                rule_id="placeholder-marker",
                level="ERROR" if token.lower() in {"hack", "unimplemented!", "todo!"} else "WARNING",
                severity="FAIL",
                file=path.name,
                line=index,
                marker=token,
                remediation="replace the marker with the missing implementation or remove it once resolved",
            ))
    return findings


# ---------------------------------------------------------------------------
# Secret redaction
# ---------------------------------------------------------------------------


def redact(text: str) -> str:
    return SECRET_WORDS.sub("[REDACTED]", text)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


def evaluate(policy: Policy) -> Report:
    if policy.root_dir is None:
        raise ConfigError("policy is missing root_dir; call policy.with_root(...)")
    root_dir = policy.root_dir
    report = Report(schema_version=SCHEMA_VERSION, status="PASS", project=root_dir.name)

    # Resolve roots and exclusions once.
    try:
        resolved_roots = [_resolve_root(root_dir, raw) for raw in policy.product_roots]
    except ConfigError as exc:
        report.status = "REVIEW_REQUIRED"
        report.notes.append(f"configuration: {exc}")
        return report
    try:
        resolved_excludes = [_resolve_exclude(root_dir, raw) for raw in policy.exclude]
    except ConfigError as exc:
        report.status = "REVIEW_REQUIRED"
        report.notes.append(f"configuration: {exc}")
        return report

    for raw in policy.product_roots:
        candidate = root_dir / raw
        if not candidate.is_dir():
            report.status = "REVIEW_REQUIRED"
            report.notes.append(f"product_roots entry is not a directory: {raw}")
            return report

    files_scanned = 0
    files_unreadable = 0
    test_findings: list[Finding] = []
    placeholder_findings: list[Finding] = []

    for language in policy.languages:
        for root in resolved_roots:
            try:
                candidates = list(_candidate_files(root, language))
            except OSError as exc:
                report.status = "REVIEW_REQUIRED"
                report.notes.append(f"cannot enumerate {root}: {exc}")
                return report
            for path in candidates:
                try:
                    rel = path.relative_to(root_dir)
                except ValueError:
                    continue
                if _is_excluded(rel, list(policy.exclude), language):
                    report.summary["excluded_paths"] += 1
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError) as exc:
                    files_unreadable += 1
                    report.status = "REVIEW_REQUIRED"
                    report.notes.append(f"unreadable product file: {rel} ({exc})")
                    return report
                lines = text.splitlines()
                files_scanned += 1
                scanner = LANGUAGE_TEST_SCANNERS.get(language)
                if scanner is not None:
                    for finding in scanner(path, lines):
                        finding.file = rel.as_posix()
                        finding.marker = redact(finding.marker)
                        finding.remediation = redact(finding.remediation)
                        test_findings.append(finding)
                for finding in scan_placeholders(path, lines, policy.placeholder_markers):
                    finding.file = rel.as_posix()
                    finding.marker = redact(finding.marker)
                    finding.remediation = redact(finding.remediation)
                    placeholder_findings.append(finding)

    report.summary["files_scanned"] = files_scanned
    report.summary["files_unreadable"] = files_unreadable
    report.summary["test_code"] = len(test_findings)
    report.summary["placeholder"] = len(placeholder_findings)

    # Placeholder threshold: only counting WARNING+ERROR (i.e. all markers).
    if report.summary["placeholder"] > policy.placeholder_threshold:
        for finding in placeholder_findings:
            report.findings.append(finding)
        report.summary["errors"] += sum(1 for f in placeholder_findings if f.level == "ERROR")
        report.summary["warnings"] += sum(1 for f in placeholder_findings if f.level == "WARNING")
        report.status = "FAIL"
        report.notes.append(
            f"placeholder marker count {report.summary['placeholder']} exceeds threshold {policy.placeholder_threshold}"
        )
    else:
        # Below threshold: still surface warnings, but do not fail.
        for finding in placeholder_findings:
            if finding.level == "WARNING":
                report.findings.append(finding)
        report.summary["warnings"] += sum(1 for f in placeholder_findings if f.level == "WARNING")
        report.notes.append(
            f"placeholder marker count {report.summary['placeholder']} at or below threshold {policy.placeholder_threshold}"
        )

    if test_findings:
        for finding in test_findings:
            report.findings.append(finding)
        report.summary["errors"] += len(test_findings)
        report.status = "FAIL"
        report.notes.append(f"{len(test_findings)} test-code findings in product scope")

    if report.status == "PASS":
        report.notes.append("product-code quality check passed")

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _load_declaration(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"cannot read declaration: {path} ({exc})")
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"declaration is not valid JSON: {exc}")
    if not isinstance(value, dict):
        raise ConfigError("declaration must be a JSON object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="project directory containing .project.json")
    parser.add_argument("--declaration", type=Path, default=None, help="explicit declaration file (defaults to <project>/.project.json)")
    parser.add_argument("--policy", type=Path, default=None, help="explicit policy JSON file (overrides declaration.quality)")
    parser.add_argument("--json", action="store_true", help="emit a versioned JSON report on stdout")
    args = parser.parse_args(argv)

    project_dir = args.project.resolve()
    if not project_dir.is_dir():
        print(f"project directory not found: {project_dir}", file=sys.stderr)
        return 2
    try:
        if args.policy is not None:
            policy_raw = json.loads(args.policy.read_text(encoding="utf-8"))
            if not isinstance(policy_raw, dict):
                raise ConfigError("policy file must contain a JSON object")
            policy = parse_policy(policy_raw)
        else:
            declaration_path = args.declaration if args.declaration else project_dir / ".project.json"
            declaration = _load_declaration(declaration_path)
            policy = load_policy(declaration)
    except ConfigError as exc:
        report = Report(
            schema_version=SCHEMA_VERSION,
            status="REVIEW_REQUIRED",
            project=project_dir.name,
        )
        report.notes.append(f"configuration: {exc}")
        if args.json:
            print(json.dumps(report.to_json(), indent=2, sort_keys=True))
        else:
            print(f"REVIEW_REQUIRED: {exc}")
        return 2

    policy = policy.with_root(project_dir)
    report = evaluate(policy)
    if args.json:
        print(json.dumps(report.to_json(), indent=2, sort_keys=True))
    else:
        for note in report.notes:
            print(f"{report.status}: {note}")
        for finding in report.findings:
            print(f"  {finding.level} {finding.rule_id} {finding.file}:{finding.line} {finding.marker}")
    if report.status == "FAIL":
        return 1
    if report.status == "REVIEW_REQUIRED":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
