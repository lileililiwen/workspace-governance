#!/usr/bin/env python3
"""Add the minimum governance declaration to an existing or new repository."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


PROJECT_ID = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
CONVERTIBLE_NAME = re.compile(r"^[A-Za-z0-9_-]+$")
GOVERNANCE_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = GOVERNANCE_ROOT / "templates" / "project"
TEXT_TEMPLATES = (
    "README.md",
    "ROADMAP.md",
    "AGENTS.md",
    "HANDOFF.md",
    ".ai-rules/workflow.md",
    ".ai-rules/completion.md",
    ".ai-gate/gate.yaml",
)


def derive_id(directory_name: str) -> str:
    """Return the canonical kebab-case project id for a directory name.

    ``hestiaLab`` -> ``hestia-lab``. Directory names that are not directly
    convertible (for example a dotted host name) still produce a candidate so
    the caller can decide whether to accept an explicit alias.
    """
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", directory_name)
    return re.sub(r"[^A-Za-z0-9]+", "-", spaced).strip("-").lower()


def resolve_project_id(directory_name: str, requested: str | None) -> tuple[str | None, str | None]:
    """Resolve the declaration id, returning (id, error).

    The directory name is the source of truth when it is convertible to a
    valid id: an explicit ``--id`` that differs is refused. A directory name
    that is not convertible (for example ``lileililiwen.github.io``) may use
    an explicitly recorded alias instead.
    """
    derived = derive_id(directory_name)
    convertible = bool(CONVERTIBLE_NAME.fullmatch(directory_name))
    if requested:
        if not PROJECT_ID.fullmatch(requested):
            return None, f"id must match {PROJECT_ID.pattern}: {requested!r}"
        if convertible and requested != derived:
            return None, f"--id {requested!r} conflicts with directory name; use {derived!r}"
        return requested, None
    if not PROJECT_ID.fullmatch(derived):
        return None, f"cannot derive a valid id from {directory_name!r}; pass --id explicitly"
    return derived, None


def load_templates() -> dict[str, str]:
    """Read the canonical templates from disk.

    `templates/project/` is the single source of truth; there is deliberately
    no embedded copy in this script, so changing a template changes the
    initializer's output.
    """
    templates: dict[str, str] = {}
    for relative in TEXT_TEMPLATES:
        path = TEMPLATE_DIR / relative
        if not path.is_file():
            raise FileNotFoundError(f"missing canonical template: {path}")
        templates[relative] = path.read_text(encoding="utf-8")
    return templates


def render(content: str, project_id: str, profile: str, verification_command: str) -> str:
    return (content
            .replace("__PROFILE__", profile)
            .replace("__CURRENT_SPEC__", "bootstrap-governance")
            .replace("__PROJECT_ID__", project_id)
            .replace("__VERIFICATION_COMMAND__", verification_command))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", type=Path)
    parser.add_argument("--id", default=None, help="explicit id; must match the derived id unless the directory name is not convertible")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--kind", default="product")
    parser.add_argument("--lifecycle", default="active")
    parser.add_argument("--verification-command", default="./scripts/verify.sh")
    parser.add_argument("--force", action="store_true", help="kept for automation compatibility; existing files are never overwritten")
    args = parser.parse_args()
    target = args.target.resolve()
    project_id, error = resolve_project_id(target.name, args.id)
    if project_id is None:
        print(f"init_project refused: {error}", file=sys.stderr)
        return 2
    try:
        templates = load_templates()
    except FileNotFoundError as exc:
        print(f"init_project refused: {exc}", file=sys.stderr)
        return 2
    target.mkdir(parents=True, exist_ok=True)
    created: list[str] = []
    declaration = target / ".project.json"
    if not declaration.exists():
        declaration.write_text(json.dumps({
            "schema_version": 1,
            "id": project_id,
            "kind": args.kind,
            "profile": args.profile,
            "lifecycle": args.lifecycle,
            "verification": {"command": args.verification_command, "gate_runtime": "driftwatchdog", "evidence_status": "planned"},
            "deployment": {"deployable": False, "jenkins_job": None, "compose_file": None},
        }, indent=2) + "\n", encoding="utf-8")
        created.append(".project.json")
    for relative, content in templates.items():
        path = target / relative
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render(content, project_id, args.profile, args.verification_command), encoding="utf-8")
        created.append(relative)
    print(f"Initialized {project_id} at {target}")
    print("Created: " + (", ".join(created) if created else "nothing; existing files preserved"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
