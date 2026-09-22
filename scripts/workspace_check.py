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
PROFILES = {"governance", "product", "dotnet-library", "dotnet-template", "deployment", "inventory"}
LIFECYCLES = {"active", "planning", "reference", "inventory", "archived"}
SECRET_WORDS = re.compile(r"(password|secret|token|api[_-]?key|private[_-]?key|credential)", re.I)


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


def validate_registry(registry: dict[str, Any], workspace_root: Path, findings: list[Finding], check_paths: bool = True) -> list[dict[str, Any]]:
    if registry.get("schema_version") != 1:
        finding(findings, "ERROR", "REGISTRY_SCHEMA", "registry schema_version must be 1")
    projects = registry.get("projects")
    if not isinstance(projects, list):
        finding(findings, "ERROR", "REGISTRY_PROJECTS", "registry projects must be an array")
        return []
    seen: set[str] = set()
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
        elif check_paths:
            project_path = workspace_root / path_value
            if not project_path.is_dir():
                finding(findings, "ERROR", "PROJECT_MISSING", f"registered project directory missing: {project_path}", project_id)
        profile = entry.get("profile")
        if not isinstance(profile, str) or not profile:
            finding(findings, "ERROR", "PROFILE_MISSING", "project profile is required", project_id)
        elif profile not in PROFILES and not profile.endswith("-product") and profile not in {"platform", "tooling", "python-runtime", "rust-platform", "typescript-monorepo"}:
            finding(findings, "ERROR", "PROFILE_UNKNOWN", f"unknown profile: {profile}", project_id)
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


def validate_change_names(project_path: Path, findings: list[Finding], project_id: str) -> None:
    changes = project_path / "openspec" / "changes"
    if not changes.is_dir():
        return
    for child in sorted(changes.iterdir()):
        if child.name == "archive" or child.name.startswith("."):
            continue
        if child.is_dir() and not CHANGE_ID.fullmatch(child.name):
            finding(findings, "ERROR", "OPENSPEC_NAME", f"invalid active OpenSpec change name: {child.name}", project_id)


def validate_project(entry: dict[str, Any], workspace_root: Path, findings: list[Finding], strict: bool = True) -> None:
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
    profile = str(entry.get("profile"))
    required, requires_ci, requires_openspec, requires_verification = profile_requirements(profile)
    for relative in required:
        if not (project_path / relative).exists():
            finding(findings, "ERROR", "REQUIRED_FILE", f"missing required file: {relative}", project_id)
    verification = declaration.get("verification")
    if requires_verification and (not isinstance(verification, dict) or not str(verification.get("command", "")).strip()):
        finding(findings, "ERROR", "VERIFICATION_COMMAND", "a real verification command is required", project_id)
    if requires_ci and not any((project_path / candidate).exists() for candidate in ("Jenkinsfile", ".gitlab-ci.yml")) and not (project_path / ".github" / "workflows").is_dir():
        finding(findings, "ERROR", "CI_MISSING", "a CI workflow is required by this profile", project_id)
    if requires_openspec and not (project_path / "openspec").is_dir():
        finding(findings, "ERROR", "OPENSPEC_MISSING", "OpenSpec directory is required by this profile", project_id)
    if requires_openspec:
        validate_change_names(project_path, findings, project_id)
    deployment = declaration.get("deployment")
    if not isinstance(deployment, dict) or not isinstance(deployment.get("deployable"), bool):
        finding(findings, "ERROR", "DEPLOYMENT_DECLARATION", "deployment.deployable must be boolean", project_id)
    elif deployment.get("deployable"):
        compose = deployment.get("compose_file")
        job = deployment.get("jenkins_job")
        if not isinstance(compose, str) or not compose:
            finding(findings, "ERROR", "DEPLOYMENT_COMPOSE", "deployable project must declare compose_file", project_id)
        elif not (project_path / compose).is_file():
            finding(findings, "ERROR", "DEPLOYMENT_COMPOSE", f"declared Compose file is missing: {compose}", project_id)
        if not isinstance(job, str) or not job:
            finding(findings, "ERROR", "DEPLOYMENT_JOB", "deployable project must declare jenkins_job", project_id)


def scan_for_secrets(value: Any, findings: list[Finding], location: str = "registry") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if SECRET_WORDS.search(str(key)) and child not in (None, "", False):
                finding(findings, "ERROR", "SECRET_VALUE", f"secret-like field contains a value: {location}.{key}")
            scan_for_secrets(child, findings, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            scan_for_secrets(child, findings, f"{location}[{index}]")


def run(args: argparse.Namespace) -> tuple[list[Finding], dict[str, int]]:
    findings: list[Finding] = []
    governance_root = Path(__file__).resolve().parents[1]
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
    projects = validate_registry(registry, workspace_root, findings, check_paths=not args.self_check)
    scan_for_secrets(registry, findings)
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
            validate_project(entry, workspace_root, findings)
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
                validate_project(entry, workspace_root, findings, strict=not discovered_only)
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
    args = parser.parse_args(argv)
    findings, summary = run(args)
    if args.as_json:
        print(json.dumps({"summary": summary, "findings": [asdict(item) for item in findings]}, indent=2, sort_keys=True))
    else:
        for item in findings:
            prefix = f"[{item.project}] " if item.project else ""
            print(f"{item.level} {item.code}: {prefix}{item.message}")
        print(f"Summary: errors={summary['errors']} warnings={summary['warnings']}")
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
