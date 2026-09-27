import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from init_project import apply_local_metadata, derive_id, resolve_project_id
from repository_metadata import build_discoverability


class DeriveIdTests(unittest.TestCase):
    def test_camel_case_becomes_kebab(self):
        self.assertEqual(derive_id("hestiaLab"), "hestia-lab")
        self.assertEqual(derive_id("campusMesh"), "campus-mesh")
        self.assertEqual(derive_id("careBridge"), "care-bridge")
        self.assertEqual(derive_id("openTeacherKit"), "open-teacher-kit")

    def test_plain_name_is_unchanged(self):
        self.assertEqual(derive_id("dharmatlas"), "dharmatlas")
        self.assertEqual(derive_id("trailCrew"), "trail-crew")


class ResolveProjectIdTests(unittest.TestCase):
    def test_derives_when_omitted(self):
        self.assertEqual(resolve_project_id("openTeacherKit", None), ("open-teacher-kit", None))

    def test_matching_explicit_id_accepted(self):
        self.assertEqual(resolve_project_id("hestiaLab", "hestia-lab"), ("hestia-lab", None))

    def test_conflicting_explicit_id_refused(self):
        resolved, error = resolve_project_id("hestiaLab", "something-else")
        self.assertIsNone(resolved)
        self.assertIn("conflicts", error)

    def test_dotted_directory_alias_allowed(self):
        self.assertEqual(resolve_project_id("lileililiwen.github.io", "lileililiwen-site"), ("lileililiwen-site", None))

    def test_invalid_explicit_id_refused(self):
        resolved, error = resolve_project_id("demo", "Bad_Id")
        self.assertIsNone(resolved)
        self.assertIn("must match", error)


class MetadataRepairTests(unittest.TestCase):
    def test_missing_semantic_fields_are_rejected(self):
        with self.assertRaises(ValueError):
            build_discoverability(description="", keywords=[], topics=[], audience=[], use_cases=[], search_phrases=[], homepage="", license_spdx="MIT", visibility="public")

    def test_explicit_metadata_is_normalized(self):
        metadata = build_discoverability(
            description="Repository governance tool",
            keywords=["repository", "governance"],
            topics=["Repository Governance"],
            audience=["developers"],
            use_cases=["audit projects"],
            search_phrases=["repository governance"],
            homepage="https://example.com",
            license_spdx="MIT",
            visibility="public",
        )
        self.assertEqual(metadata["topics"], ["repository-governance"])

    def test_apply_repair_adds_metadata_and_license(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / ".project.json").write_text(json.dumps({"id": "demo"}), encoding="utf-8")
            metadata = build_discoverability(
                description="Repository governance tool",
                keywords=["repository"],
                topics=["repository-governance"],
                audience=["developers"],
                use_cases=["audit projects"],
                search_phrases=["repository governance"],
                homepage="https://example.com",
                license_spdx="MIT",
                visibility="public",
            )
            changed = apply_local_metadata(target, metadata, "MIT")
            self.assertEqual(changed, [".project.json", "LICENSE"])
            self.assertEqual(json.loads((target / ".project.json").read_text())["discoverability"], metadata)
            self.assertIn("MIT License", (target / "LICENSE").read_text())


if __name__ == "__main__":
    unittest.main()
