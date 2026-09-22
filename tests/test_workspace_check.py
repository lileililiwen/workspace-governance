import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from workspace_check import discover_projects, run


BASE_DECLARATION = {
    "schema_version": 1,
    "id": "demo-project",
    "kind": "product",
    "profile": "inventory",
    "lifecycle": "inventory",
    "verification": {"command": "true", "gate_runtime": "driftwatchdog", "evidence_status": "planned"},
    "deployment": {"deployable": False, "jenkins_job": None, "compose_file": None},
}


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class WorkspaceCheckTests(unittest.TestCase):
    def make_workspace(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        project = root / "demo-project"
        project.mkdir()
        write_json(project / ".project.json", BASE_DECLARATION)
        registry = {"schema_version": 1, "workspace_root": None, "discovery": {"mode": "explicit", "unregistered_policy": "fail"}, "projects": [{"id": "demo-project", "path": "demo-project", "profile": "inventory", "lifecycle": "inventory", "adoption": "adopted"}]}
        registry_path = root / "projects.json"
        write_json(registry_path, registry)
        return temp, root, registry_path

    def test_valid_inventory_project_passes(self):
        temp, root, registry = self.make_workspace()
        self.addCleanup(temp.cleanup)
        findings, summary = run(SimpleNamespace(registry=str(registry), root=str(root), project=None, audit=False, self_check=False, as_json=False))
        self.assertEqual(summary["errors"], 0, findings)

    def test_missing_declaration_fails_audit(self):
        temp, root, registry = self.make_workspace()
        self.addCleanup(temp.cleanup)
        (root / "demo-project" / ".project.json").unlink()
        findings, summary = run(SimpleNamespace(registry=str(registry), root=str(root), project=None, audit=True, self_check=False, as_json=False))
        self.assertGreater(summary["errors"], 0)
        self.assertTrue(any(item.code == "DECLARATION_MISSING" for item in findings))

    def test_secret_value_is_rejected(self):
        temp, root, registry = self.make_workspace()
        self.addCleanup(temp.cleanup)
        data = json.loads(registry.read_text())
        data["api_token"] = "do-not-store"
        write_json(registry, data)
        findings, summary = run(SimpleNamespace(registry=str(registry), root=str(root), project=None, audit=False, self_check=False, as_json=False))
        self.assertGreater(summary["errors"], 0)
        self.assertTrue(any(item.code == "SECRET_VALUE" for item in findings))

    def test_invalid_active_openspec_name_is_rejected(self):
        temp, root, registry = self.make_workspace()
        self.addCleanup(temp.cleanup)
        project = root / "demo-project"
        declaration = json.loads((project / ".project.json").read_text())
        declaration["profile"] = "product"
        write_json(project / ".project.json", declaration)
        registry_data = json.loads(registry.read_text())
        registry_data["projects"][0]["profile"] = "product"
        write_json(registry, registry_data)
        (project / "README.md").write_text("# Demo\n")
        (project / "ROADMAP.md").write_text("# Roadmap\n")
        (project / "HANDOFF.md").write_text("current_spec: valid-change\n")
        (project / "AGENTS.md").write_text("# Agents\n")
        (project / ".ai-rules").mkdir()
        (project / ".ai-rules/workflow.md").write_text("BFS DFS BFS\n")
        (project / ".ai-rules/completion.md").write_text("completion\n")
        (project / "openspec/changes/2026-bad").mkdir(parents=True)
        (project / ".github/workflows").mkdir(parents=True)
        findings, summary = run(SimpleNamespace(registry=str(registry), root=str(root), project=None, audit=False, self_check=False, as_json=False))
        self.assertGreater(summary["errors"], 0)
        self.assertTrue(any(item.code == "OPENSPEC_NAME" for item in findings))

    def test_new_project_folder_is_discovered_without_registry_edit(self):
        temp, root, registry = self.make_workspace()
        self.addCleanup(temp.cleanup)
        candidate = root / "new-project"
        candidate.mkdir()
        (candidate / "README.md").write_text("# New project\n", encoding="utf-8")
        write_json(candidate / ".project.json", {**BASE_DECLARATION, "id": "new-project"})
        data = json.loads(registry.read_text())
        data["discovery"] = {"mode": "immediate-directories", "unregistered_policy": "report"}
        write_json(registry, data)

        findings, summary = run(SimpleNamespace(registry=str(registry), root=str(root), project=None, audit=True, self_check=False, as_json=False))

        self.assertEqual(summary["errors"], 0, findings)
        self.assertTrue(any(item.code == "DISCOVERED_UNREGISTERED" and item.project == "new-project" for item in findings))

    def test_discovery_uses_relative_folder_names(self):
        temp, root, registry = self.make_workspace()
        self.addCleanup(temp.cleanup)
        (root / "new-project").mkdir()
        (root / "new-project" / "README.md").write_text("# New project\n", encoding="utf-8")
        discovered = discover_projects(root, {"discovery": {"mode": "immediate-directories"}})
        self.assertEqual(discovered[0]["path"], "demo-project")
        self.assertEqual(discovered[1]["path"], "new-project")


if __name__ == "__main__":
    unittest.main()
