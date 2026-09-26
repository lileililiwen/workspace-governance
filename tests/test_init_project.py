import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from init_project import derive_id, resolve_project_id


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


if __name__ == "__main__":
    unittest.main()
