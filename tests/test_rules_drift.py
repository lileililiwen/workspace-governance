import json
import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import init_project
import rules_drift


WORK_ON_MAIN = "Work directly on `main` by default; do not create a branch or worktree unless the user asks for one or designates one."
WORK_ON_MAIN_EXCEPTION = "unless the user asks for one or designates one"

WORKFLOW = f"BFS → DFS → BFS. Each change requires two commits. Run `node scripts/check-openspec-change-names.mjs` first. {WORK_ON_MAIN}"
COMPLETION = "Completion requires the checks. Each change requires two commits. Build success is not release evidence."


class RulesDriftTests(unittest.TestCase):
    def make_project(self, workflow=WORKFLOW, completion=COMPLETION, handoff=""):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        project = root / "demo"
        (project / ".ai-rules").mkdir(parents=True)
        (project / ".ai-rules" / "workflow.md").write_text(workflow + "\n", encoding="utf-8")
        (project / ".ai-rules" / "completion.md").write_text(completion + "\n", encoding="utf-8")
        if handoff:
            (project / "HANDOFF.md").write_text(handoff, encoding="utf-8")
        registry = {"schema_version": 1, "projects": [{"id": "demo", "path": "demo", "profile": "product", "lifecycle": "active", "adoption": "adopted"}]}
        registry_path = root / "projects.json"
        registry_path.write_text(json.dumps(registry), encoding="utf-8")
        return root, registry_path, project

    def test_complete_rules_have_no_drift(self):
        _, _, project = self.make_project()
        self.assertEqual(rules_drift.drift(project), [])

    def test_missing_clause_is_reported(self):
        _, _, project = self.make_project(workflow="BFS only")
        labels = [item["label"] for item in rules_drift.drift(project)]
        self.assertIn("two-commit rule", labels)

    def test_opt_out_marker_suppresses_drift(self):
        _, _, project = self.make_project(workflow="BFS only " + rules_drift.OPT_OUT)
        self.assertEqual(rules_drift.drift(project), [])

    def test_unreadable_file_is_reported(self):
        _, _, project = self.make_project()
        (project / ".ai-rules" / "workflow.md").write_bytes(b"\xff\xfe\x00bad")
        codes = [item["code"] for item in rules_drift.drift(project)]
        self.assertIn("RULES_UNREADABLE", codes)

    def test_report_is_non_destructive(self):
        root, registry_path, project = self.make_project(workflow="BFS only")
        before = {name: (project / ".ai-rules" / name).read_bytes() for name in ("workflow.md", "completion.md")}
        rules_drift.check(root, registry_path)
        after = {name: (project / ".ai-rules" / name).read_bytes() for name in before}
        self.assertEqual(before, after)

    def test_work_on_main_clause_reported_when_absent(self):
        _, _, project = self.make_project(
            workflow="BFS → DFS → BFS. Each change requires two commits. Run `node scripts/check-openspec-change-names.mjs` first."
        )
        labels = [item["label"] for item in rules_drift.drift(project)]
        self.assertIn("work-on-main rule", labels)

    def test_work_on_main_clause_present_is_not_reported(self):
        _, _, project = self.make_project()
        labels = [item["label"] for item in rules_drift.drift(project)]
        self.assertNotIn("work-on-main rule", labels)

    def test_opt_out_marker_suppresses_the_work_on_main_clause(self):
        _, _, project = self.make_project(workflow="BFS only " + rules_drift.OPT_OUT)
        path = project / ".ai-rules" / "workflow.md"
        before = path.read_bytes()
        self.assertEqual(rules_drift.drift(project), [])
        self.assertEqual(before, path.read_bytes())

    def test_scaffold_handoff_detected(self):
        _, _, project = self.make_project(handoff="Replace this section with current implementation and verification evidence\n")
        self.assertTrue(rules_drift.scaffold_handoff(project))

    def test_real_handoff_not_flagged(self):
        _, _, project = self.make_project(handoff="# Handoff\n\ncurrent_spec: none\n\nRecords the shipped change and its evidence.\n")
        self.assertFalse(rules_drift.scaffold_handoff(project))

    def test_non_adopted_project_is_skipped(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        project = root / "demo"
        (project / ".ai-rules").mkdir(parents=True)
        (project / ".ai-rules" / "workflow.md").write_text("nothing useful\n", encoding="utf-8")
        registry = {"schema_version": 1, "projects": [{"id": "demo", "path": "demo", "profile": "product", "lifecycle": "active"}]}
        registry_path = root / "projects.json"
        registry_path.write_text(json.dumps(registry), encoding="utf-8")
        self.assertEqual(rules_drift.check(root, registry_path), [])


class TemplateSourceTests(unittest.TestCase):
    def test_templates_are_read_from_disk(self):
        templates = init_project.load_templates()
        self.assertIn(".ai-rules/workflow.md", templates)
        self.assertIn("check-openspec-change-names", templates[".ai-rules/workflow.md"])
        for relative in ("README.md", "ROADMAP.md", "AGENTS.md", "HANDOFF.md", ".ai-rules/completion.md", ".ai-gate/gate.yaml"):
            self.assertIn(relative, templates)

    def test_templates_carry_the_work_on_main_rule(self):
        templates = init_project.load_templates()
        for relative in (".ai-rules/workflow.md", "AGENTS.md"):
            with self.subTest(relative=relative):
                text = templates[relative]
                self.assertIn(WORK_ON_MAIN, text)
                self.assertIn(WORK_ON_MAIN_EXCEPTION, text)

    def test_no_embedded_template_copy(self):
        self.assertFalse(hasattr(init_project, "TEMPLATES"))


if __name__ == "__main__":
    unittest.main()
