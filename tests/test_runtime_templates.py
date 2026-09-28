import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from runtime_templates import (  # noqa: E402
    TemplateError,
    check_target,
    inspect_target,
    load_registry,
    render_target,
)


class RuntimeTemplateRegistryTests(unittest.TestCase):
    def test_registry_has_six_supported_types(self):
        registry = load_registry()
        self.assertEqual(
            set(registry),
            {
                "dotnet-web-postgres",
                "rust-web-postgres",
                "python-web-postgres",
                "node-web",
                "static-site",
                "worker-postgres",
            },
        )
        for entry in registry.values():
            self.assertEqual(entry["version"], 1)
            self.assertTrue(entry["files"])
            self.assertTrue(entry["required_variables"])


class RuntimeTemplateInspectionTests(unittest.TestCase):
    def test_dotnet_inspection_suggests_dotnet_template(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "App.csproj").write_text("<Project />\n", encoding="utf-8")
            result = inspect_target(root)
            self.assertEqual(result["suggestions"], ["dotnet-web-postgres"])
            self.assertIn("src/App.csproj", result["evidence"])

    def test_empty_target_requires_explicit_type(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(TemplateError) as context:
                inspect_target(Path(directory))
            self.assertEqual(context.exception.code, "TYPE_REQUIRED")


class RuntimeTemplateRenderingTests(unittest.TestCase):
    def declaration(self):
        return {
            "schema_version": 1,
            "id": "demo-app",
            "kind": "product",
            "profile": "product",
            "lifecycle": "active",
            "verification": {"command": "./scripts/verify.sh", "gate_runtime": "driftwatchdog", "evidence_status": "planned"},
            "deployment": {"deployable": False, "jenkins_job": None, "compose_file": None},
        }

    def variables(self, template_type):
        values = {"project_name": "demo-app"}
        if template_type != "worker-postgres":
            values.update({"port": "8080", "health_path": "/healthz"})
        if template_type in {"dotnet-web-postgres", "rust-web-postgres"}:
            values.update({"app_project": "src/App/App.csproj" if template_type.startswith("dotnet") else "app", "database_name": "demo"})
        elif template_type == "python-web-postgres":
            values.update({"entrypoint": "app.main:app", "database_name": "demo"})
        elif template_type == "node-web":
            values.update({"build_command": "npm run build", "start_command": "npm run start", "output_dir": "dist"})
        elif template_type == "static-site":
            values.update({"output_dir": "dist"})
        elif template_type == "worker-postgres":
            values.update({"worker_command": "python -m worker", "database_name": "demo"})
        return values

    def test_render_writes_relative_files_and_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".project.json").write_text(json.dumps(self.declaration()), encoding="utf-8")
            result = render_target(root, "static-site", self.variables("static-site"))
            self.assertEqual(result["state"], "configured")
            self.assertTrue((root / "Dockerfile").is_file())
            self.assertTrue((root / "compose.yaml").is_file())
            updated = json.loads((root / ".project.json").read_text(encoding="utf-8"))
            self.assertEqual(updated["deployment"]["compose_file"], "compose.yaml")
            self.assertFalse(updated["deployment"]["deployable"])
            self.assertEqual(updated["deployment"]["template_type"], "static-site")

    def test_existing_file_refuses_without_exact_replace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".project.json").write_text(json.dumps(self.declaration()), encoding="utf-8")
            (root / "compose.yaml").write_text("existing\n", encoding="utf-8")
            with self.assertRaises(TemplateError) as context:
                render_target(root, "static-site", self.variables("static-site"))
            self.assertEqual(context.exception.code, "TARGET_EXISTS")
            self.assertEqual((root / "compose.yaml").read_text(), "existing\n")

    def test_secret_variable_is_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(TemplateError) as context:
                render_target(Path(directory), "static-site", {"project_name": "demo", "port": "8080", "health_path": "/healthz", "token": "secret"})
            self.assertEqual(context.exception.code, "RENDER_REJECTED")
            self.assertFalse((Path(directory) / "Dockerfile").exists())

    def test_template_output_has_no_unresolved_placeholders(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".project.json").write_text(json.dumps(self.declaration()), encoding="utf-8")
            render_target(root, "node-web", self.variables("node-web"))
            self.assertEqual(check_target(root)["state"], "configured")
            for path in root.rglob("*"):
                if path.is_file() and path.name != ".project.json":
                    self.assertNotIn("{{", path.read_text(encoding="utf-8"))

    def test_every_template_renders_without_cross_family_files(self):
        for template_type in load_registry():
            with self.subTest(template_type=template_type), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / ".project.json").write_text(json.dumps(self.declaration()), encoding="utf-8")
                result = render_target(root, template_type, self.variables(template_type))
                self.assertEqual(result["template_type"], template_type)
                self.assertTrue((root / "Dockerfile").is_file())
                self.assertTrue((root / "compose.yaml").is_file())
                self.assertIn(check_target(root)["compose_validation"], {"verified", "TOOL_UNAVAILABLE"})


if __name__ == "__main__":
    unittest.main()
