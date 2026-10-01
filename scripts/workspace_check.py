#!/usr/bin/env python3
"""Fail-closed governance checks for the local project portfolio."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


PROJECT_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
CHANGE_ID = PROJECT_ID
LIFECYCLES = {"active", "planning", "reference", "inventory", "archived"}


# Decision register codes (see scripts/decisions.py and the
# `workspace-decision-register` canonical spec).
DECISIONS_REGISTER_MISSING = "DECISIONS_REGISTER_MISSING"
DECISIONS_REGISTER_ABSENT = "DECISIONS_REGISTER_ABSENT"
DECISIONS_REGISTER_INVALID = "DECISIONS_REGISTER_INVALID"
DECISIONS_REGISTRY_REFERENCE = "DECISIONS_REGISTRY_REFERENCE"

# The canonical kind/profile sets and the secret scan pattern live in
# vocabulary.json (see scripts/vocabulary.py). This module keeps no local
# duplicate list: SECRET_WORDS and PROFILES resolve lazily from the
# vocabulary so `from workspace_check import SECRET_WORDS` (used by the
# Forge governance adapter) keeps working.


def _default_governance_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _vocabulary_for(governance_root: Path | None) -> dict[str, Any]:
    import vocabulary

    root = Path(governance_root) if governance_root is not None else _default_governance_root()
    return vocabulary.load_vocabulary_for_governance_root(root)


def canonical_profiles_for(governance_root: Path | None = None) -> frozenset[str]:
    return _vocabulary_for(governance_root)["profiles"]


def canonical_kinds_for(governance_root: Path | None = None) -> frozenset[str]:
    return _vocabulary_for(governance_root)["kinds"]


def secret_words_for(governance_root: Path | None = None) -> "re.Pattern[str]":
    import vocabulary

    return vocabulary.secret_pattern(_vocabulary_for(governance_root)["secret_field_substrings"])


def __getattr__(name: str) -> Any:
    if name == "SECRET_WORDS":
        return secret_words_for()
    if name == "PROFILES":
        return set(canonical_profiles_for())
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

# Capability and release-evidence vocabulary (additive, opt-in per project).
CAPABILITY_OWNERS = {"platform", "product", "shared", "external"}
CAPABILITY_EVIDENCE_STATES = {"declared", "configured", "verified", "unverified", "blocked"}
RELEASE_EVIDENCE_STATES = {"declared", "configured", "verified", "unverified"}
RELEASE_EVIDENCE_FIELDS = (
    "revision",
    "version",
    "toolchain",
    "artifacts",
    "digests",
    "sbom",
    "provenance",
    "checks",
    "publication",
)
DEPLOYABLE_RELEASE_REQUIRED_FIELDS = ("revision", "artifacts", "digests", "provenance", "checks", "publication")


@dataclass
class Finding:
    level: str
    code: str
    message: str
    project: str | None = None


def finding(findings: list[Finding], level: str, code: str, message: str, project: str | None = None) -> None:
    findings.append(Finding(level, code, message, project))


PROJECT_MARKERS = (
    ".project.json",
    ".git",
    "README.md",
    "Cargo.toml",
    "package.json",
    "pyproject.toml",
    "pubspec.yaml",
    "go.mod",
    "pom.xml",
    "Dockerfile",
    "docker-compose.yml",
    "compose.yml",
    "Jenkinsfile",
)


def discover_projects(workspace_root: Path, registry: dict[str, Any]) -> list[dict[str, str]]:
    """Discover immediate child projects without persisting a machine path."""
    discovery = registry.get("discovery") or {}
    mode = discovery.get("mode", "explicit")
    if mode not in {"immediate-directories", "explicit-plus-immediate-directories"}:
        return []
    excluded = {str(item) for item in discovery.get("exclude", []) if isinstance(item, str)}
    projects: list[dict[str, str]] = []
    try:
        children = sorted(workspace_root.iterdir(), key=lambda item: item.name)
    except OSError:
        return projects
    for child in children:
        if child.name.startswith(".") or child.name in excluded or not child.is_dir() or child.is_symlink():
            continue
        if not any((child / marker).exists() for marker in PROJECT_MARKERS):
            continue
        projects.append({"id": child.name, "path": child.relative_to(workspace_root).as_posix()})
    return projects


def load_json(path: Path, findings: list[Finding], code: str) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        finding(findings, "ERROR", code, f"missing JSON file: {path}")
        return None
    except (OSError, json.JSONDecodeError) as exc:
        finding(findings, "ERROR", code, f"invalid JSON {path}: {exc}")
        return None
    if not isinstance(value, dict):
        finding(findings, "ERROR", code, f"JSON object required: {path}")
        return None
    return value


def load_decisions_register(
    governance_root: Path,
    registry: dict[str, Any],
    findings: list[Finding],
    *,
    self_check: bool,
) -> "list[object] | None":
    """Load `decisions.json` from the governance root and surface findings.

    The register is governance-owned and is required for the governance
    self-check (ERROR `DECISIONS_REGISTER_MISSING`). A portfolio audit on
    sibling repos tolerates the absence of the register (single WARNING
    `DECISIONS_REGISTER_ABSENT`); broken shapes and unknown registry
    references are always errors. Returns the parsed decisions on success,
    `None` on any failure path (the caller does not need the value).

    The `WORKSPACE_DECISIONS_PATH` env var overrides the default location
    so tests can stage a per-workspace register without touching the
    governance root file. Production callers never set it.
    """
    import decisions as decisions_module

    override = os.environ.get("WORKSPACE_DECISIONS_PATH")
    if override:
        register_path = Path(override)
    else:
        register_path = decisions_module.decisions_path(governance_root)
    if not register_path.is_file():
        if self_check:
            finding(findings, "ERROR", DECISIONS_REGISTER_MISSING,
                    f"decisions register missing at {register_path}")
        else:
            finding(findings, "WARNING", DECISIONS_REGISTER_ABSENT,
                    f"decisions register absent at {register_path}; "
                    "self-check mode requires it")
        return None
    try:
        loaded = decisions_module.load_decisions(register_path)
    except decisions_module.DecisionError as exc:
        finding(findings, "ERROR", DECISIONS_REGISTER_INVALID, str(exc))
        return None
    registry_ids = {
        entry.get("id")
        for entry in (registry.get("projects") or [])
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    }
    offenders = decisions_module.validate_against_registry(loaded, registry_ids)
    if offenders:
        finding(
            findings,
            "ERROR",
            DECISIONS_REGISTRY_REFERENCE,
            f"decisions register references unknown registry ids: {offenders}",
        )
        return None
    return loaded


def validate_registry(registry: dict[str, Any], workspace_root: Path, findings: list[Finding], check_paths: bool = True, *, canonical_profiles: set[str] | frozenset[str] | None = None, governance_root: Path | None = None) -> list[dict[str, Any]]:
    if registry.get("schema_version") != 1:
        finding(findings, "ERROR", "REGISTRY_SCHEMA", "registry schema_version must be 1")
    projects = registry.get("projects")
    if not isinstance(projects, list):
        finding(findings, "ERROR", "REGISTRY_PROJECTS", "registry projects must be an array")
        return []
    seen: set[str] = set()
    seen_paths: set[str] = set()
    for entry in projects:
        if not isinstance(entry, dict):
            finding(findings, "ERROR", "REGISTRY_ENTRY", "each registry project must be an object")
            continue
        project_id = entry.get("id")
        path_value = entry.get("path")
        if not isinstance(project_id, str) or not PROJECT_ID.fullmatch(project_id):
            finding(findings, "ERROR", "PROJECT_ID", f"invalid project id: {project_id!r}")
            continue
        if project_id in seen:
            finding(findings, "ERROR", "PROJECT_DUPLICATE", f"duplicate project id: {project_id}", project_id)
        seen.add(project_id)
        if not isinstance(path_value, str) or Path(path_value).is_absolute() or ".." in Path(path_value).parts:
            finding(findings, "ERROR", "PROJECT_PATH", f"project path must be repository-relative: {path_value!r}", project_id)
        else:
            if path_value in seen_paths:
                finding(findings, "ERROR", "PROJECT_PATH_DUPLICATE", f"duplicate project path: {path_value}", project_id)
            seen_paths.add(path_value)
            if check_paths:
                project_path = workspace_root / path_value
                if not project_path.is_dir():
                    finding(findings, "ERROR", "PROJECT_MISSING", f"registered project directory missing: {project_path}", project_id)
        profile = entry.get("profile")
        if not isinstance(profile, str) or not profile:
            finding(findings, "ERROR", "PROFILE_MISSING", "project profile is required", project_id)
        else:
            profiles = canonical_profiles if canonical_profiles is not None else canonical_profiles_for(governance_root)
            if profile not in profiles:
                finding(findings, "ERROR", "PROFILE_UNKNOWN", f"unknown profile: {profile}; canonical profiles: {sorted(profiles)}", project_id)
        lifecycle = entry.get("lifecycle")
        if lifecycle not in LIFECYCLES:
            finding(findings, "ERROR", "LIFECYCLE", f"invalid lifecycle: {lifecycle!r}", project_id)
    return projects


def profile_requirements(profile: str) -> tuple[list[str], bool, bool, bool]:
    if profile == "inventory":
        return [".project.json"], False, False, False
    if profile == "tooling":
        return ["README.md", ".project.json"], False, False, True
    if profile == "deployment":
        return ["README.md", ".project.json"], False, False, True
    if profile == "dotnet-template":
        return ["README.md", "AGENTS.md", ".project.json"], True, False, True
    if profile == "governance":
        return ["README.md", "ROADMAP.md", "HANDOFF.md", "AGENTS.md", ".ai-rules/workflow.md", ".ai-rules/completion.md", ".project.json"], True, False, True
    return ["README.md", "ROADMAP.md", "HANDOFF.md", "AGENTS.md", ".ai-rules/workflow.md", ".ai-rules/completion.md", ".project.json"], True, True, True


def load_profile_spec(governance_root: Path, profile: str) -> dict[str, Any] | None:
    """Load the profile JSON next to the governance checker, if present.

    Profiles are documentation by default. The checker only reads them to
    surface a soft warning when a project declares a capability its profile
    does not list as supported.
    """
    path = governance_root / "profiles" / f"{profile}.json"
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict):
        return None
    return value


def validate_profile_docs(governance_root: Path, findings: list[Finding], *, canonical_profiles: set[str] | frozenset[str] | None = None) -> None:
    """A `profiles/<name>.json` document naming a non-canonical profile is ERROR `PROFILE_DOC_UNKNOWN`."""
    profiles = canonical_profiles if canonical_profiles is not None else canonical_profiles_for(governance_root)
    profiles_dir = Path(governance_root) / "profiles"
    if not profiles_dir.is_dir():
        return
    for child in sorted(profiles_dir.glob("*.json")):
        try:
            value = json.loads(child.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            finding(findings, "ERROR", "PROFILE_DOC_UNKNOWN", f"cannot parse profile document {child.name}: {exc}")
            continue
        if not isinstance(value, dict):
            finding(findings, "ERROR", "PROFILE_DOC_UNKNOWN", f"profile document must contain a JSON object: {child.name}")
            continue
        documented = value.get("id", child.stem)
        if child.stem not in profiles or documented not in profiles:
            finding(findings, "ERROR", "PROFILE_DOC_UNKNOWN", f"profile document {child.name} names a non-canonical profile: {documented!r}; canonical profiles: {sorted(profiles)}")


def validate_kind(declaration: dict[str, Any], findings: list[Finding], project_id: str, *, canonical_kinds: set[str] | frozenset[str] | None = None, governance_root: Path | None = None) -> None:
    """A declaration whose `kind` is outside the canonical set is WARNING `KIND_UNKNOWN`.

    Kind is descriptive and never drives profile requirements.
    """
    kinds = canonical_kinds if canonical_kinds is not None else canonical_kinds_for(governance_root)
    kind = declaration.get("kind")
    if not isinstance(kind, str) or kind not in kinds:
        finding(findings, "WARNING", "KIND_UNKNOWN", f"unknown kind: {kind!r}; canonical kinds: {sorted(kinds)}", project_id)


def validate_capabilities(capabilities: Any, project_path: Path, findings: list[Finding], project_id: str, supported: set[str] | None = None) -> None:
    """Audit a project's optional capability declarations.

    Declarations describe intent, not implementation. Governance records the
    declared state and the presence/absence of native evidence; it never
    promotes a capability to verified on its own.

    When `supported` is provided, capabilities not listed there are surfaced
    as a WARNING so profile owners can keep the supported set intentional.
    """
    if not isinstance(capabilities, dict):
        finding(findings, "ERROR", "CAPABILITIES_SHAPE", "capabilities must be an object", project_id)
        return
    for name, entry in capabilities.items():
        if not isinstance(name, str) or not PROJECT_ID.fullmatch(name):
            finding(findings, "ERROR", "CAPABILITY_NAME", f"invalid capability name: {name!r}", project_id)
            continue
        if supported is not None and name not in supported:
            finding(findings, "WARNING", "CAPABILITY_UNSUPPORTED", f"capability {name!r} is not declared as supported by the project profile", project_id)
        if not isinstance(entry, dict):
            finding(findings, "ERROR", "CAPABILITY_SHAPE", f"capability {name!r} must be an object", project_id)
            continue
        owner = entry.get("owner")
        if not isinstance(owner, str) or not owner:
            finding(findings, "ERROR", "CAPABILITY_OWNER", f"capability {name!r} requires a non-empty owner", project_id)
        elif owner not in CAPABILITY_OWNERS and not PROJECT_ID.fullmatch(owner):
            finding(findings, "WARNING", "CAPABILITY_OWNER", f"capability {name!r} owner is not a known platform, product, or shared id: {owner!r}", project_id)
        state = entry.get("evidence_state")
        if state not in CAPABILITY_EVIDENCE_STATES:
            finding(findings, "ERROR", "CAPABILITY_STATE", f"capability {name!r} has invalid evidence_state: {state!r}", project_id)
            continue
        ref = entry.get("evidence_ref")
        if ref is not None and not isinstance(ref, str):
            finding(findings, "ERROR", "CAPABILITY_REF", f"capability {name!r} evidence_ref must be a string when present", project_id)
            ref = None
        if state in {"configured", "verified"}:
            if not isinstance(ref, str) or not ref:
                finding(findings, "WARNING", "CAPABILITY_PENDING", f"capability {name!r} is {state} but has no evidence_ref", project_id)
            elif (project_path / ref).is_file():
                continue
            else:
                level = "ERROR" if state == "verified" else "WARNING"
                code = "CAPABILITY_STALE" if state == "verified" else "CAPABILITY_PENDING"
                finding(findings, level, code, f"capability {name!r} evidence_ref missing: {ref}", project_id)
        elif state == "unverified":
            finding(findings, "WARNING", "CAPABILITY_PENDING", f"capability {name!r} is unverified; native evidence required", project_id)
        elif state == "blocked":
            finding(findings, "WARNING", "CAPABILITY_BLOCKED", f"capability {name!r} is declared blocked; verify the non-goal is recorded", project_id)


def validate_release_evidence(release_evidence: Any, project_path: Path, findings: list[Finding], project_id: str) -> None:
    """Audit a project's optional release evidence record.

    Release evidence is a producer-neutral record of source revision, version,
    toolchain, artifacts, digests, SBOM, provenance, checks, and publication.
    """
    if not isinstance(release_evidence, dict):
        finding(findings, "ERROR", "RELEASE_EVIDENCE_SHAPE", "release_evidence must be an object", project_id)
        return
    seen: set[str] = set()
    for field, entry in release_evidence.items():
        if not isinstance(field, str):
            finding(findings, "ERROR", "RELEASE_EVIDENCE_FIELD", f"release evidence field must be a string, got {type(field).__name__}", project_id)
            continue
        if field in seen:
            finding(findings, "WARNING", "RELEASE_EVIDENCE_DUPLICATE", f"release evidence field repeated: {field}", project_id)
        seen.add(field)
        if field not in RELEASE_EVIDENCE_FIELDS:
            finding(findings, "WARNING", "RELEASE_EVIDENCE_FIELD", f"unknown release evidence field: {field}", project_id)
        if not isinstance(entry, dict):
            finding(findings, "ERROR", "RELEASE_EVIDENCE_SHAPE", f"release evidence {field!r} must be an object", project_id)
            continue
        state = entry.get("state")
        if state not in RELEASE_EVIDENCE_STATES:
            finding(findings, "ERROR", "RELEASE_EVIDENCE_STATE", f"release evidence {field!r} has invalid state: {state!r}", project_id)
            continue
        ref = entry.get("evidence_ref")
        if ref is not None and not isinstance(ref, str):
            finding(findings, "ERROR", "RELEASE_EVIDENCE_REF", f"release evidence {field!r} evidence_ref must be a string when present", project_id)
            ref = None
        if state in {"configured", "verified"} and isinstance(ref, str) and ref and not (project_path / ref).is_file():
            level = "ERROR" if state == "verified" else "WARNING"
            code = "RELEASE_EVIDENCE_STALE" if state == "verified" else "RELEASE_EVIDENCE_PENDING"
            finding(findings, level, code, f"release evidence {field!r} evidence_ref missing: {ref}", project_id)


def validate_deployment_evidence(deployment: Any, declaration: dict[str, Any], project_path: Path, findings: list[Finding], project_id: str) -> None:
    """For projects that opt in to deployment, require complete release evidence.

    A deployable project must carry a release_evidence block whose required
    fields (revision, artifacts, digests, provenance, checks, publication) are
    either verified or configured with a present evidence_ref. Anything else
    is an ERROR that blocks the deployable gate; metadata alone is never
    sufficient to flip deployment.deployable to true.
    """
    if not isinstance(deployment, dict) or not deployment.get("deployable"):
        return
    declaration_release = declaration.get("release_evidence")
    if not isinstance(declaration_release, dict):
        finding(findings, "ERROR", "RELEASE_EVIDENCE_REQUIRED", "deployable project must declare release_evidence", project_id)
        return
    for field in DEPLOYABLE_RELEASE_REQUIRED_FIELDS:
        entry = declaration_release.get(field)
        if not isinstance(entry, dict):
            finding(findings, "ERROR", "RELEASE_EVIDENCE_INSUFFICIENT", f"deployable project must declare release_evidence.{field}", project_id)
            continue
        state = entry.get("state")
        if state == "verified":
            continue
        if state == "configured":
            ref = entry.get("evidence_ref")
            if isinstance(ref, str) and ref and (project_path / ref).is_file():
                continue
            finding(findings, "ERROR", "RELEASE_EVIDENCE_INSUFFICIENT", f"deployable project release_evidence.{field} configured but evidence_ref missing: {ref!r}", project_id)
            continue
        finding(findings, "ERROR", "RELEASE_EVIDENCE_INSUFFICIENT", f"deployable project release_evidence.{field} state is {state!r}; verified or configured+ref is required", project_id)


def load_promotion_ledger(governance_root: Path, findings: list[Finding]) -> dict[str, dict[str, Any]]:
    """Load the deployment-promo ledger if present, with tamper detection.

    Returns a map of project_id -> latest promote entry. Missing ledger
    returns an empty map (no error). Tampered entries produce a single
    `PROMOTIONS_LEDGER_TAMPERED` ERROR on the findings list; the function
    still returns the on-disk entries so the audit can keep reporting.
    """
    try:
        import promote_project  # local import to keep this module standalone
    except ImportError:
        return {}
    path = promote_project.ledger_path(governance_root)
    sidecar = promote_project.ledger_sidecar_path(governance_root)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries = payload.get("entries", [])
    except (OSError, json.JSONDecodeError) as exc:
        finding(findings, "ERROR", "PROMOTIONS_LEDGER_TAMPERED", f"cannot parse ledger: {exc}")
        return {}
    if sidecar.is_file():
        try:
            expected = sidecar.read_text(encoding="utf-8").strip()
            actual = promote_project.compute_ledger_hash(entries)
        except OSError:
            expected = ""
            actual = ""
        if expected and expected != actual:
            finding(findings, "ERROR", "PROMOTIONS_LEDGER_TAMPERED", f"ledger entries do not match recorded sidecar at {sidecar}")
    latest: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        project_id = entry.get("project_id")
        if not isinstance(project_id, str):
            continue
        if entry.get("kind") == "promote":
            latest[project_id] = entry
    return latest


def validate_deployment_promotion(deployment: Any, project_path: Path, project_id: str, governance_root: Path | None, findings: list[Finding]) -> None:
    """For projects with `deployable: true`, the audit must find a matching
    promotion ledger entry; a stale entry is a WARNING so the project still
    ships while the operator is asked to re-run promotion.
    """
    if not isinstance(deployment, dict) or not deployment.get("deployable"):
        return
    if governance_root is None:
        return
    ledger = load_promotion_ledger(governance_root, findings)
    entry = ledger.get(project_id)
    if entry is None:
        finding(findings, "ERROR", "DEPLOYMENT_PROMOTION", "deployable project has no matching entry in deployment/promotions.json", project_id)
        return
    recorded_revision = entry.get("revision")
    head_file = project_path / ".git" / "HEAD"
    if not head_file.is_file():
        return
    head = head_file.read_text(encoding="utf-8").strip()
    if head.startswith("ref:"):
        ref_name = head.split(":", 1)[1].strip()
        ref_path = project_path / ".git" / ref_name
        head = ref_path.read_text(encoding="utf-8").strip() if ref_path.is_file() else head
    if isinstance(recorded_revision, str) and head and recorded_revision != head and recorded_revision != "unknown":
        finding(findings, "WARNING", "DEPLOYMENT_PROMOTION_STALE", f"promoted revision {recorded_revision!r} differs from project HEAD {head!r}; re-promote at HEAD with scripts/promote_project.py {project_id} --evidence-ref <ref>", project_id)


def validate_product_quality(declaration: dict[str, Any], project_path: Path, findings: list[Finding], project_id: str) -> None:
    """Run the product-code quality checker on a project that opts in.

    The checker is imported in-process. The audit translates its findings into
    the existing Finding vocabulary: FAIL becomes ERROR, REVIEW_REQUIRED
    becomes WARNING, PASS produces no finding.
    """
    import product_code_quality  # local import to keep workspace_check importable without the checker
    import vocabulary as vocabulary_module  # local import for the same reason
    try:
        policy = product_code_quality.load_policy(declaration)
    except (product_code_quality.ConfigError, vocabulary_module.VocabularyError) as exc:
        finding(findings, "WARNING", "QUALITY_POLICY", f"product quality policy invalid: {exc}", project_id)
        return
    try:
        report = product_code_quality.evaluate(policy.with_root(project_path))
    except product_code_quality.ConfigError as exc:
        finding(findings, "WARNING", "QUALITY_POLICY", f"product quality check cannot run: {exc}", project_id)
        return
    for note in report.notes:
        if report.status == "REVIEW_REQUIRED":
            finding(findings, "WARNING", "QUALITY_REVIEW_REQUIRED", note, project_id)
        elif report.status == "FAIL":
            finding(findings, "ERROR", "QUALITY_FAILURE", note, project_id)
    for item in report.findings:
        level = "ERROR" if item.level == "ERROR" or report.status == "FAIL" else "WARNING"
        code = "QUALITY_TEST_CODE" if item.rule_id == "product-test-code" else "QUALITY_PLACEHOLDER"
        message = f"{item.file}:{item.line} {item.marker}".strip()
        finding(findings, level, code, message, project_id)


def validate_change_names(project_path: Path, findings: list[Finding], project_id: str) -> None:
    changes = project_path / "openspec" / "changes"
    if not changes.is_dir():
        return
    for child in sorted(changes.iterdir()):
        if child.name == "archive" or child.name.startswith("."):
            continue
        if child.is_dir() and not CHANGE_ID.fullmatch(child.name):
            finding(findings, "ERROR", "OPENSPEC_NAME", f"invalid active OpenSpec change name: {child.name}", project_id)


def validate_handoff_quality(project_path: Path, findings: list[Finding], project_id: str) -> None:
    """Surface a scaffold `HANDOFF.md` so boilerplate cannot pass as a handoff.

    Clause-level `.ai-rules` drift is reported by `scripts/rules_sync.py` as a
    triage report rather than here, because repositories legitimately document
    the shared rules in their own words and language.
    """
    import rules_drift  # local import to keep this module standalone
    if rules_drift.scaffold_handoff(project_path):
        finding(findings, "WARNING", "HANDOFF_SCAFFOLD", "HANDOFF.md still carries the initializer scaffold", project_id)


def validate_project(entry: dict[str, Any], workspace_root: Path, findings: list[Finding], strict: bool = True, governance_root: Path | None = None, *, check_publication: bool = True) -> None:
    project_id = str(entry.get("id"))
    project_path = workspace_root / str(entry.get("path"))
    declaration_path = project_path / ".project.json"
    if not declaration_path.exists():
        if strict:
            finding(findings, "ERROR", "DECLARATION_MISSING", "adopted project must contain .project.json", project_id)
        return
    declaration = load_json(declaration_path, findings, "PROJECT_DECLARATION")
    if declaration is None:
        return
    if declaration.get("schema_version") != 1:
        finding(findings, "ERROR", "DECLARATION_SCHEMA", "project declaration schema_version must be 1", project_id)
    if declaration.get("id") != project_id:
        finding(findings, "ERROR", "DECLARATION_ID", f"declaration id must be {project_id!r}", project_id)
    validate_kind(declaration, findings, project_id, governance_root=governance_root)
    profile = str(entry.get("profile"))
    required, requires_ci, requires_openspec, requires_verification = profile_requirements(profile)
    for relative in required:
        if not (project_path / relative).exists():
            finding(findings, "ERROR", "REQUIRED_FILE", f"missing required file: {relative}", project_id)
    verification = declaration.get("verification")
    if requires_verification and (not isinstance(verification, dict) or not str(verification.get("command", "")).strip()):
        finding(findings, "ERROR", "VERIFICATION_COMMAND", "a real verification command is required", project_id)
    if profile != "inventory":
        from repository_metadata import validate_discoverability, validate_publication

        if not (project_path / "LICENSE").is_file():
            finding(findings, "ERROR", "LICENSE_MISSING", "standard project must contain a root LICENSE", project_id)
        validate_discoverability(declaration, project_path, findings, project_id)
        if check_publication:
            validate_publication(declaration, findings, project_id)
    if requires_ci and not any((project_path / candidate).exists() for candidate in ("Jenkinsfile", ".gitlab-ci.yml")) and not (project_path / ".github" / "workflows").is_dir():
        finding(findings, "ERROR", "CI_MISSING", "a CI workflow is required by this profile", project_id)
    if requires_openspec and not (project_path / "openspec").is_dir():
        finding(findings, "ERROR", "OPENSPEC_MISSING", "OpenSpec directory is required by this profile", project_id)
    if requires_openspec:
        validate_change_names(project_path, findings, project_id)
    deployment = declaration.get("deployment")
    if not isinstance(deployment, dict) or not isinstance(deployment.get("deployable"), bool):
        finding(findings, "ERROR", "DEPLOYMENT_DECLARATION", "deployment.deployable must be boolean", project_id)
    else:
        compose = deployment.get("compose_file")
        if compose is not None and (not isinstance(compose, str) or not compose or Path(compose).is_absolute() or ".." in Path(compose).parts):
            finding(findings, "ERROR", "DEPLOYMENT_COMPOSE", "deployment.compose_file must be repository-relative when present", project_id)
        template_type = deployment.get("template_type")
        template_version = deployment.get("template_version")
        rendered_files = deployment.get("rendered_files")
        template_state = deployment.get("template_state")
        if template_type is not None and (not isinstance(template_type, str) or not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", template_type)):
            finding(findings, "ERROR", "DEPLOYMENT_TEMPLATE", "deployment.template_type must be a kebab-case identifier", project_id)
        if template_version is not None and (not isinstance(template_version, int) or isinstance(template_version, bool) or template_version < 1):
            finding(findings, "ERROR", "DEPLOYMENT_TEMPLATE", "deployment.template_version must be a positive integer", project_id)
        if rendered_files is not None:
            if not isinstance(rendered_files, list) or len(set(rendered_files)) != len(rendered_files) or any(not isinstance(item, str) or Path(item).is_absolute() or ".." in Path(item).parts for item in rendered_files):
                finding(findings, "ERROR", "DEPLOYMENT_TEMPLATE", "deployment.rendered_files must contain unique repository-relative paths", project_id)
        if template_state is not None and template_state not in {"configured", "verified", "blocked"}:
            finding(findings, "ERROR", "DEPLOYMENT_TEMPLATE", "deployment.template_state is invalid", project_id)
    if isinstance(deployment, dict) and deployment.get("deployable"):
        compose = deployment.get("compose_file")
        job = deployment.get("jenkins_job")
        if not isinstance(compose, str) or not compose:
            finding(findings, "ERROR", "DEPLOYMENT_COMPOSE", "deployable project must declare compose_file", project_id)
        elif not (project_path / compose).is_file():
            finding(findings, "ERROR", "DEPLOYMENT_COMPOSE", f"declared Compose file is missing: {compose}", project_id)
        if not isinstance(job, str) or not job:
            finding(findings, "ERROR", "DEPLOYMENT_JOB", "deployable project must declare jenkins_job", project_id)
    capabilities = declaration.get("capabilities")
    supported: set[str] | None = None
    if capabilities is not None and governance_root is not None:
        spec = load_profile_spec(governance_root, profile)
        if spec is not None:
            raw = spec.get("supported_capabilities")
            if isinstance(raw, list):
                supported = {item for item in raw if isinstance(item, str)}
    if capabilities is not None:
        validate_capabilities(capabilities, project_path, findings, project_id, supported=supported)
    release_evidence = declaration.get("release_evidence")
    if release_evidence is not None:
        validate_release_evidence(release_evidence, project_path, findings, project_id)
    if isinstance(deployment, dict) and deployment.get("deployable"):
        validate_deployment_evidence(deployment, declaration, project_path, findings, project_id)
        validate_deployment_promotion(deployment, project_path, project_id, governance_root, findings)
    if isinstance(declaration.get("quality"), dict):
        validate_product_quality(declaration, project_path, findings, project_id)
    if entry.get("adoption") == "adopted":
        validate_handoff_quality(project_path, findings, project_id)


def scan_for_secrets(value: Any, findings: list[Finding], location: str = "registry", *, secret_words: "re.Pattern[str] | None" = None, governance_root: Path | None = None) -> None:
    pattern = secret_words if secret_words is not None else secret_words_for(governance_root)
    if isinstance(value, dict):
        for key, child in value.items():
            if pattern.search(str(key)) and child not in (None, "", False):
                finding(findings, "ERROR", "SECRET_VALUE", f"secret-like field contains a value: {location}.{key}")
            scan_for_secrets(child, findings, f"{location}.{key}", secret_words=pattern)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            scan_for_secrets(child, findings, f"{location}[{index}]", secret_words=pattern)


def run(args: argparse.Namespace) -> tuple[list[Finding], dict[str, int]]:
    findings: list[Finding] = []
    governance_root = Path(__file__).resolve().parents[1]
    try:
        vocabulary = _vocabulary_for(governance_root)
    except Exception as exc:
        finding(findings, "ERROR", "VOCABULARY", str(exc))
        return findings, {"errors": len(findings), "warnings": 0}
    canonical_profiles = vocabulary["profiles"]
    canonical_kinds = vocabulary["kinds"]
    import vocabulary as vocabulary_module

    secret_words = vocabulary_module.secret_pattern(vocabulary["secret_field_substrings"])
    registry_path = Path(args.registry)
    if not registry_path.is_absolute():
        registry_path = governance_root / registry_path
    registry = load_json(registry_path, findings, "REGISTRY_FILE")
    if registry is None:
        return findings, {"errors": len(findings), "warnings": 0}
    configured_root = getattr(args, "root", None) or os.environ.get("WORKSPACE_ROOT") or registry.get("workspace_root")
    if args.self_check:
        workspace_root = governance_root
    elif configured_root:
        workspace_root = Path(configured_root).expanduser().resolve()
    else:
        workspace_root = Path.cwd().resolve()
    load_decisions_register(governance_root, registry, findings, self_check=bool(args.self_check))
    projects = validate_registry(registry, workspace_root, findings, check_paths=not args.self_check, canonical_profiles=canonical_profiles, governance_root=governance_root)
    validate_profile_docs(governance_root, findings, canonical_profiles=canonical_profiles)
    scan_for_secrets(registry, findings, secret_words=secret_words)
    effective_projects = list(projects)
    explicit_paths = {str(entry.get("path")) for entry in projects}
    discovery = registry.get("discovery") or {}
    if discovery.get("mode") in {"immediate-directories", "explicit-plus-immediate-directories"} and not args.self_check:
        policy = discovery.get("unregistered_policy", "report")
        for discovered in discover_projects(workspace_root, registry):
            if discovered["path"] in explicit_paths:
                continue
            level = "ERROR" if policy == "fail" else "WARNING"
            finding(findings, level, "DISCOVERED_UNREGISTERED", "project folder is discovered but not registered; local metadata is the source of truth", discovered["id"])
            declaration_path = workspace_root / discovered["path"] / ".project.json"
            if declaration_path.is_file():
                try:
                    declaration = json.loads(declaration_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    declaration = {}
                if isinstance(declaration, dict):
                    effective_projects.append({
                        "id": discovered["id"],
                        "path": discovered["path"],
                        "profile": declaration.get("profile", "inventory"),
                        "lifecycle": declaration.get("lifecycle", "inventory"),
                        "adoption": "pending",
                    })
    if args.self_check:
        selected = [{**entry, "path": "."} for entry in projects if entry.get("id") == "workspace-governance"]
        for entry in selected:
            validate_project(entry, workspace_root, findings, governance_root=governance_root, check_publication=False)
    else:
        selected = effective_projects
        if args.project:
            selected = [entry for entry in effective_projects if entry.get("id") == args.project or entry.get("path") == args.project]
            if not selected:
                finding(findings, "ERROR", "PROJECT_UNKNOWN", f"project not found in registry: {args.project}")
        for entry in selected:
            adopted = entry.get("adoption", "pending") == "adopted"
            discovered_only = entry.get("path") not in explicit_paths
            if args.audit or args.project or adopted:
                validate_project(entry, workspace_root, findings, strict=not discovered_only, governance_root=governance_root)
            else:
                finding(findings, "WARNING", "ADOPTION_PENDING", "project is registered but not yet adopted", str(entry.get("id")))
    summary = {"errors": sum(item.level == "ERROR" for item in findings), "warnings": sum(item.level == "WARNING" for item in findings)}
    return findings, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="workspace root; defaults to registry workspace_root")
    parser.add_argument("--registry", default="projects.json")
    parser.add_argument("--project", help="validate one registered project")
    parser.add_argument("--audit", action="store_true", help="validate every registered project and fail on adoption gaps")
    parser.add_argument("--self-check", action="store_true", help="validate the governance repository only")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument(
        "--decisions",
        action="store_true",
        help="print a summary of the toolchain decision register and exit (loader errors are non-zero)",
    )
    args = parser.parse_args(argv)
    if args.decisions:
        return _print_decisions_summary(args)
    findings, summary = run(args)
    if args.as_json:
        print(json.dumps({"summary": summary, "findings": [asdict(item) for item in findings]}, indent=2, sort_keys=True))
    else:
        for item in findings:
            prefix = f"[{item.project}] " if item.project else ""
            print(f"{item.level} {item.code}: {prefix}{item.message}")
        print(f"Summary: errors={summary['errors']} warnings={summary['warnings']}")
    if any(item.code == "VOCABULARY" for item in findings):
        return 2
    return 1 if summary["errors"] else 0


def _print_decisions_summary(args: argparse.Namespace) -> int:
    """Print the toolchain decision register summary and exit.

    Loader failures (missing file, malformed JSON, bad shape, unknown registry
    references) produce a non-zero exit and a short message on stderr. The
    register is owned by the governance root; this summary reads from there
    regardless of `--root` so the surface is stable for downstream tooling.
    """
    import decisions as decisions_module

    governance_root = _default_governance_root()
    register_path = decisions_module.decisions_path(governance_root)
    try:
        loaded = decisions_module.load_decisions(register_path)
    except decisions_module.DecisionError as exc:
        print(f"ERROR decisions register: {exc}", file=sys.stderr)
        return 1
    registry_path = governance_root / args.registry
    if not registry_path.is_file():
        print(
            f"ERROR decisions register: registry file not found at {registry_path}",
            file=sys.stderr,
        )
        return 1
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR decisions register: cannot read registry {registry_path}: {exc}", file=sys.stderr)
        return 1
    if not isinstance(registry, dict):
        print(f"ERROR decisions register: registry must be a JSON object: {registry_path}", file=sys.stderr)
        return 1
    registry_ids = {
        entry.get("id")
        for entry in (registry.get("projects") or [])
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    }
    offenders = decisions_module.validate_against_registry(loaded, registry_ids)
    if offenders:
        joined = ", ".join(sorted(offenders))
        print(
            f"ERROR decisions register: unknown registry references: {joined}",
            file=sys.stderr,
        )
        return 1
    summary = [
        {"id": entry.id, "title": entry.title, "status": entry.status, "date": entry.date}
        for entry in loaded
    ]
    if args.as_json:
        print(json.dumps({"decisions": summary, "total": len(summary)}, indent=2, sort_keys=True))
        return 0
    for entry in summary:
        print(f"{entry['id']}\t{entry['status']}\t{entry['date']}\t{entry['title']}")
    print(f"Total decisions: {len(summary)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
