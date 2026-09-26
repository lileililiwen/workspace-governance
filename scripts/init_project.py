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


TEMPLATES = {
    "README.md": "# __PROJECT_ID__\n\nThis project is governed by Workspace Governance. Preserve the product-specific README content when extending this file.\n\nVerification command: `__VERIFICATION_COMMAND__`.\n",
    "ROADMAP.md": "# __PROJECT_ID__ Roadmap\n\nRecord dependency-ordered delivery phases, release targets, deferred scope, and evidence boundaries here.\n",
    "AGENTS.md": "# Project Agent Instructions\n\n- Read `HANDOFF.md` before work.\n- Use OpenSpec for non-trivial changes.\n- Use BFS → DFS → BFS for impact, implementation, and regression review.\n- Run the declared verification command before completion.\n- Build/test/skeleton success is not runtime or release evidence.\n- Each completed OpenSpec spec/change requires exactly two commits: first the implementation/tests/archive commit, then a HANDOFF.md-only pointer/evidence commit.\n\nDetailed rules: `.ai-rules/workflow.md` and `.ai-rules/completion.md`.\n",
    "HANDOFF.md": "# Project Handoff\n\ncurrent_spec: __CURRENT_SPEC__\n\n## Current state\n\nGovernance declaration created by Workspace Governance. Replace this section with current implementation and verification evidence.\n\n## Next action\n\nSelect the next OpenSpec change or record why the project is blocked.\n\nEach completed OpenSpec spec/change requires exactly two commits: first the implementation/tests/archive commit, then a HANDOFF.md-only pointer/evidence commit.\n",
    ".ai-rules/workflow.md": "# Project Workflow\n\nUse BFS → DFS → BFS. Map impact and evidence first, implement one coherent change, then re-audit callers, persistence, APIs, tests, security, and release boundaries.\n\nRun the shared governance checker and the project verification command before archive or completion. Run `node scripts/check-openspec-change-names.mjs` from the governance repository before OpenSpec status/instructions.\n\nEach completed OpenSpec spec/change requires exactly two commits: first the implementation/tests/archive commit, then a HANDOFF.md-only pointer/evidence commit. Stop after commit 2.\n",
    ".ai-rules/completion.md": "# Project Completion\n\nCompletion requires requirements and scenarios verified, migrated callers reviewed, required tests passing, the project verification command passing, the shared governance check passing, and the original impact surface rechecked. Build/test/skeleton success is not runtime or release evidence.\n\nEach completed OpenSpec spec/change requires exactly two commits: first the implementation/tests/archive commit, then a HANDOFF.md-only pointer/evidence commit. Stop after commit 2.\n",
    ".ai-gate/gate.yaml": "version: 1\nruntime: driftwatchdog\nprofile: __PROFILE__\nrule_pack: workspace-governance@1\nchecks:\n  repository: true\n  build: true\n  tests: true\n  security: true\n  product_quality: false\nblocking:\n  - FAIL\n  - REVIEW_REQUIRED\nnotes:\n  - Set `product_quality: true` only after adding a `quality` block to `.project.json`; see docs/product-code-quality.md.\n  - The local OpenSpec name preflight remains mandatory.\n",
}


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
    for relative, content in TEMPLATES.items():
        path = target / relative
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.replace("__PROFILE__", args.profile).replace("__CURRENT_SPEC__", "bootstrap-governance").replace("__PROJECT_ID__", project_id).replace("__VERIFICATION_COMMAND__", args.verification_command), encoding="utf-8")
        created.append(relative)
    print(f"Initialized {project_id} at {target}")
    print("Created: " + (", ".join(created) if created else "nothing; existing files preserved"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
