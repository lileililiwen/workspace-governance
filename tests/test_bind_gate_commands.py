"""Tests for `scripts/bind_gate_commands.py`.

The properties that matter, and the ones this file pins:

* the shape comes from the files on disk; `.project.json` `stack` is never an
  input, because it disagrees with the disk for a large minority of the fleet;
* a `*.slnx` is a solution on the same footing as a `*.sln`, which a
  `*.sln`-only search cannot see at all;
* **a command is never invented.** An unknown shape, a `package.json` without
  the script the concern needs, a pure-Python `build`, and two equally
  plausible entry points are all *unresolved*, with the reason. A wrong
  command is worse than an honest gap, so the refusals are pinned harder than
  the successes;
* a concern the manifest did not select is never bound;
* an operator's own command is reported as a conflict and never overwritten;
* a dry run writes nothing, and `--apply` is the only thing that writes;
* the debt record names every unresolved concern, and carries no timestamp.

No test uses `rm`: this host's `rm` is a recoverable-delete shim that prints to
stdout and can fail. Cleanup uses `shutil.rmtree(..., ignore_errors=True)`.
"""

import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from bind_gate_commands import (  # noqa: E402
    ALREADY_BOUND,
    BOUND,
    CONFLICT,
    DEBT_FILE,
    DIRTY,
    GENERATED_MARKER,
    NO_MANIFEST,
    PARTIAL,
    REFUSED,
    RESOLVED,
    SOLUTION_SUFFIXES,
    UNRESOLVED,
    bind_repo,
    build_debt,
    derive,
    detect_shape,
    format_detail,
    main,
    read_manifest,
    render_manifest,
    roll_up,
    run,
    unquote_scalar,
    write_debt_record,
)

# The manifest a fixture starts from. `checks:` is the only thing a test
# varies about policy; everything else is fixed so a binding diff is readable.
MANIFEST = """version: 1
runtime: driftwatchdog
profile: product
checks:
{checks}blocking:
  - FAIL
"""

BUILD_AND_TESTS = "  build: true\n  tests: true\n"
TESTS_ONLY = "  tests: true\n"

# A manifest with an existing `commands:` block, so the insertion path is
# exercised against a document that already has one.
WITH_COMMANDS = """version: 1
runtime: driftwatchdog
profile: product
checks:
  build: true
  tests: true
commands:
  build: cargo build --all-targets
blocking:
  - FAIL
"""

# The exact reason the tool gives for a pure-Python `build`. Quoted rather
# than re-derived, so a change in the wording is a visible test diff.
PURE_PYTHON_BUILD = (
    "a pure-Python package has no build step; a packaging build is an owner "
    "decision, not a derivation"
)

UNITTEST_RUNNER = "python3 -m unittest discover -s tests -v"

A_SOLUTION = "Microsoft Visual Studio Solution File, Format Version 12.00\n"
A_SLNX = '<Solution>\n</Solution>\n'
A_CSPROJ = '<Project Sdk="Microsoft.NET.Sdk">\n</Project>\n'


class RepoCase(unittest.TestCase):
    """A throwaway repository with a manifest and whatever files a test needs."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = self.tmp / "demo"
        (self.repo / ".ai-gate").mkdir(parents=True)
        # A repository starts with a manifest declaring `build` and `tests`. A
        # test about a different selection calls `write_manifest` over the top.
        self.write_manifest()

    # --- fixture construction ------------------------------------

    def write_manifest(self, checks: str = BUILD_AND_TESTS, text: str | None = None):
        target = self.repo / ".ai-gate" / "gate.yaml"
        target.write_text(
            text if text is not None else MANIFEST.format(checks=checks),
            encoding="utf-8",
        )
        return target

    def write(self, relative: str, body: str = ""):
        target = self.repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        return target

    def unlink_manifest(self):
        (self.repo / ".ai-gate" / "gate.yaml").unlink(missing_ok=True)

    def manifest_text(self) -> str:
        return (self.repo / ".ai-gate" / "gate.yaml").read_text(encoding="utf-8")

    # --- running the tool -----------------------------------------

    def bind(self, apply: bool = False):
        return bind_repo(self.repo, apply=apply, check_clean=False)

    @staticmethod
    def concern(outcome, concern_id: str):
        """The one outcome for `concern_id`, or a hard failure if it is absent."""
        found = [c for c in outcome.concerns if c.concern == concern_id]
        if len(found) != 1:
            raise AssertionError(
                f"expected exactly one {concern_id!r} outcome, got {len(found)}: "
                f"{[c.concern for c in outcome.concerns]}"
            )
        return found[0]

    def bound_command(self, concern_id: str, apply: bool = False) -> str:
        got = self.concern(self.bind(apply=apply), concern_id)
        return got.command

    def derived(self, concern_id: str):
        return derive(concern_id, detect_shape(self.repo), self.repo)


class GitRepoCase(RepoCase):
    """A committed repository, for the paths that consult `git status`."""

    def commit(self):
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        subprocess.run(["git", "add", "-A"], cwd=self.repo, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base"],
            cwd=self.repo,
            check=True,
        )


# --- detection: the disk decides, the label does not ----------


class DetectionTests(RepoCase):
    def test_a_sln_is_a_solution(self):
        self.write("App.sln", A_SOLUTION)
        self.write("App/App.csproj", A_CSPROJ)
        shape = detect_shape(self.repo)
        self.assertEqual(shape.solutions, ["App.sln"])
        self.assertEqual(shape.label(), "dotnet")

    def test_a_slnx_is_a_solution(self):
        # The regression this exists for: 19 repositories in this fleet carry
        # no `*.sln` at all, and a `*.sln`-only search finds nothing in them.
        self.write("Foo.slnx", A_SLNX)
        shape = detect_shape(self.repo)
        self.assertEqual(shape.solutions, ["Foo.slnx"])
        self.assertEqual(shape.label(), "dotnet")

    def test_both_solution_suffixes_are_recognised(self):
        self.assertEqual(SOLUTION_SUFFIXES, (".sln", ".slnx"))

    def test_a_nested_slnx_is_found_at_depth(self):
        self.write("backend/Linglitch.slnx", A_SLNX)
        self.assertEqual(detect_shape(self.repo).solutions, ["backend/Linglitch.slnx"])

    def test_the_declared_stack_is_never_read(self):
        # `loreMix`: the label says typescript and the disk is a .NET solution.
        # A label-driven binder would emit `npm run build` for this repository.
        self.write(
            ".project.json", json.dumps({"schema_version": 1, "stack": "typescript"})
        )
        self.write("LoreMix.slnx", A_SLNX)
        self.write("web/package.json", json.dumps({"scripts": {"build": "vite"}}))
        shape = detect_shape(self.repo)
        self.assertEqual(shape.label(), "dotnet")
        self.assertEqual(
            derive("build", shape, self.repo)[0], "dotnet build LoreMix.slnx"
        )

    def test_a_wrong_label_does_not_produce_a_node_command(self):
        self.write(
            ".project.json", json.dumps({"schema_version": 1, "stack": "dotnet"})
        )
        self.write("package.json", json.dumps({"scripts": {"build": "tsc"}}))
        self.assertEqual(detect_shape(self.repo).label(), "node")

    def test_the_workspace_flag_follows_the_cargo_manifest(self):
        self.write("Cargo.toml", "[workspace]\nmembers = [\"a\"]\n")
        shape = detect_shape(self.repo)
        self.assertEqual(shape.crates, ["Cargo.toml"])
        self.assertEqual(shape.workspaces, ["Cargo.toml"])

    def test_a_cargo_manifest_without_workspace_is_not_a_workspace(self):
        self.write("Cargo.toml", '[package]\nname = "a"\n')
        shape = detect_shape(self.repo)
        self.assertEqual(shape.crates, ["Cargo.toml"])
        self.assertEqual(shape.workspaces, [])

    def test_a_vendored_conftest_is_not_evidence(self):
        # `alethefy`'s only `conftest.py` is inside a site-packages tree; reading
        # it would make a dependency's file look like this repository's pytest
        # configuration.
        self.write(".venv/lib/python3/site-packages/numpy/conftest.py", "def test_x():\n    pass\n")
        self.write("pyproject.toml", "[project]\nname = 'p'\n")
        self.assertEqual(detect_shape(self.repo).pytest_configs, [])

    def test_a_vendored_node_module_is_not_a_candidate(self):
        self.write("node_modules/dep/package.json", json.dumps({"scripts": {"test": "t"}}))
        self.assertEqual(detect_shape(self.repo).node_manifests, [])

    def test_an_indented_testcase_method_is_not_a_bare_test_function(self):
        # The false positive this file's sibling hit: an indented
        # `def test_x(self)` is a `unittest.TestCase` method, not a bare
        # function, so a repository written with unittest is not read as a
        # pytest repository.
        self.write(
            "tests/test_x.py",
            "import unittest\n\n\nclass T(unittest.TestCase):\n    def test_a(self):\n        pass\n",
        )
        shape = detect_shape(self.repo)
        self.assertEqual(shape.python_dirs, ["tests"])
        self.assertEqual(derive("tests", shape, self.repo)[0], UNITTEST_RUNNER)

    def test_an_empty_test_file_says_nothing_about_the_runner(self):
        self.write("tests/test_cli.py", "\n")
        shape = detect_shape(self.repo)
        command, _evidence, reason = derive("tests", shape, self.repo)
        self.assertEqual(command, "")
        self.assertIn("defines a test", reason)


# --- derivation: the exact command string ----------------------


class DerivationTests(RepoCase):
    def test_a_sln_yields_a_dotnet_build_naming_the_solution(self):
        self.write("App.sln", A_SOLUTION)
        self.write("App/App.csproj", A_CSPROJ)
        self.assertEqual(self.bound_command("build"), "dotnet build App.sln")

    def test_a_slnx_yields_a_dotnet_command(self):
        # The regression lock for the `.slnx` error: with no `*.sln` present,
        # the binder must still produce a .NET command rather than nothing.
        self.write("Foo.slnx", A_SLNX)
        self.assertEqual(self.bound_command("build"), "dotnet build Foo.slnx")
        self.assertEqual(self.bound_command("tests"), "dotnet test Foo.slnx")

    def test_a_workspace_cargo_manifest_yields_the_workspace_flag(self):
        self.write("Cargo.toml", "[workspace]\nmembers = [\"a\"]\n")
        self.assertEqual(self.bound_command("build"), "cargo build --workspace")
        self.assertEqual(self.bound_command("tests"), "cargo test --workspace")

    def test_a_bare_cargo_manifest_yields_a_plain_build(self):
        self.write("Cargo.toml", '[package]\nname = "a"\n')
        self.assertEqual(self.bound_command("build"), "cargo build")
        self.assertEqual(self.bound_command("tests"), "cargo test")

    def test_rust_security_is_the_dependency_audit(self):
        self.write_manifest("  security: true\n")
        self.write("Cargo.toml", '[package]\nname = "a"\n')
        got = self.concern(self.bind(), "security")
        self.assertEqual(got.command, "cargo audit")
        self.assertIn("dependency audit", got.evidence)

    def test_a_nested_node_manifest_carries_its_working_directory(self):
        # The Gate runs every command from the repository root, so a nested
        # manifest is unreachable without the `cd`.
        self.write("web/package.json", json.dumps({"scripts": {"test": "vitest"}}))
        self.assertEqual(self.bound_command("tests"), "cd web && npm test")

    def test_a_root_node_manifest_needs_no_working_directory(self):
        self.write("package.json", json.dumps({"scripts": {"test": "jest"}}))
        self.assertEqual(self.bound_command("tests"), "npm test")

    def test_a_package_json_without_the_script_yields_no_command(self):
        self.write("package.json", json.dumps({"scripts": {"build": "tsc"}}))
        got = self.concern(self.bind(), "tests")
        self.assertEqual(got.status, UNRESOLVED)
        self.assertEqual(got.command, "")
        self.assertIn("no package.json in this repository declares a 'test' script", got.reason)

    def test_a_bare_test_function_repository_binds_pytest(self):
        self.write("pyproject.toml", "[project]\nname = 'p'\n")
        self.write("tests/test_x.py", "def test_one():\n    assert True\n")
        self.assertEqual(self.bound_command("tests"), "pytest")

    def test_a_mixed_runner_repository_binds_pytest(self):
        # `unittest discovery` finds no TestCase in a bare-function file and
        # reports success having run nothing, so the repository that needs
        # pytest anywhere gets pytest.
        self.write("pyproject.toml", "[project]\nname = 'p'\n")
        self.write(
            "tests/test_a.py",
            "import unittest\nclass T(unittest.TestCase):\n    def test_a(self):\n        pass\n",
        )
        self.write("tests/test_b.py", "def test_b():\n    assert True\n")
        self.assertEqual(self.bound_command("tests"), "pytest")

    def test_a_unittest_only_repository_binds_unittest_discovery(self):
        self.write("pyproject.toml", "[project]\nname = 'p'\n")
        self.write(
            "tests/test_a.py",
            "import unittest\nclass T(unittest.TestCase):\n    def test_a(self):\n        pass\n",
        )
        self.assertEqual(self.bound_command("tests"), UNITTEST_RUNNER)

    def test_python_security_needs_a_declared_tool(self):
        # There is no stdlib Python dependency audit, so a command is bound
        # only when the repository names the tool itself.
        self.write_manifest("  security: true\n")
        self.write("pyproject.toml", "[project]\ndependencies = ['pip-audit']\n")
        self.assertEqual(self.bound_command("security"), "pip-audit")

    def test_python_security_without_a_declared_tool_is_unresolved(self):
        self.write_manifest("  security: true\n")
        self.write("pyproject.toml", "[project]\nname = 'p'\n")
        got = self.concern(self.bind(), "security")
        self.assertEqual(got.status, UNRESOLVED)
        self.assertIn("not in the standard library", got.reason)

    def test_a_single_csproj_may_stand_in_for_a_solution(self):
        self.write("A.csproj", A_CSPROJ)
        self.assertEqual(self.bound_command("build"), "dotnet build A.csproj")

    def test_a_flutter_package_binds_its_test_runner(self):
        self.write("pubspec.yaml", "name: p\n")
        self.assertEqual(self.bound_command("tests"), "flutter test")

    def test_a_repository_concern_is_a_repository_wide_property(self):
        self.write_manifest("  repository: true\n")
        self.write("A.sln", A_SOLUTION)
        self.assertEqual(self.bound_command("repository"), "git diff --check")

    def test_a_named_script_is_run_when_the_repository_wrote_it(self):
        self.write("scripts/check-openspec-change-names.mjs", "console.log(1)\n")
        self.write_manifest("  openspec_names: true\n")
        self.assertEqual(
            self.bound_command("openspec_names"),
            "node scripts/check-openspec-change-names.mjs",
        )

    def test_a_named_script_is_not_invented_when_it_is_absent(self):
        self.write("A.sln", A_SOLUTION)
        self.write_manifest("  openspec_names: true\n")
        got = self.concern(self.bind(), "openspec_names")
        self.assertEqual(got.status, UNRESOLVED)
        self.assertIn("no scripts/check-openspec-change-names.mjs", got.reason)

    def test_an_unknown_concern_looks_for_its_own_check_script(self):
        self.write("scripts/check-foo.sh", "#!/bin/sh\n")
        self.write_manifest("  foo: true\n")
        self.assertEqual(self.bound_command("foo"), "scripts/check-foo.sh")


# --- refusal: the negative controls ---------------------------


class RefusalTests(RepoCase):
    """A binder that fabricates a command is worse than no binder.

    These are the most important tests in the file: each one must stay red if
    the tool ever starts guessing.
    """

    def pure_python_repo(self):
        self.write_manifest(BUILD_AND_TESTS)
        self.write("pyproject.toml", "[project]\nname = 'p'\n")
        self.write(
            "tests/test_x.py",
            "import unittest\nclass T(unittest.TestCase):\n    def test_a(self):\n        pass\n",
        )
        return self.bind()

    def test_a_pure_python_build_is_unresolved(self):
        got = self.concern(self.pure_python_repo(), "build")
        self.assertEqual(got.status, UNRESOLVED)
        self.assertEqual(got.command, "")
        self.assertEqual(got.reason, PURE_PYTHON_BUILD)

    def test_a_pure_python_repository_never_acquires_a_build_command(self):
        # The negative control proper: whatever the tool does, no build command
        # may appear for a pure-Python package.
        outcome = self.pure_python_repo()
        for got in outcome.concerns:
            self.assertNotIn(" -m build", got.command, got.concern)
            self.assertNotIn("setup.py", got.command, got.concern)
            self.assertNotIn("pyproject", got.command, got.concern)
        build = self.concern(outcome, "build")
        self.assertEqual(build.command, "", "a build command was invented")
        # The only command in the whole repository is the one the files show.
        bound = [c.command for c in outcome.concerns if c.command]
        self.assertEqual(bound, [UNITTEST_RUNNER])

    def test_a_pure_python_dry_run_writes_nothing(self):
        self.pure_python_repo()
        self.assertNotIn("commands:", self.manifest_text())

    def test_a_flutter_build_is_unresolved_without_a_target(self):
        self.write("pubspec.yaml", "name: p\n")
        got = self.concern(self.bind(), "build")
        self.assertEqual(got.status, UNRESOLVED)
        self.assertIn("needs a target platform", got.reason)

    def test_an_unrecognised_shape_yields_no_command(self):
        self.write("README.md", "# hi\n")
        for concern_id in ("build", "tests"):
            got = self.concern(self.bind(), concern_id)
            self.assertEqual(got.status, UNRESOLVED, concern_id)
            self.assertEqual(got.command, "", concern_id)

    def test_several_csproj_and_no_solution_is_not_resolved_by_guessing(self):
        self.write("A/A.csproj", A_CSPROJ)
        self.write("B/B.csproj", A_CSPROJ)
        outcome = self.bind()
        for concern_id in ("build", "tests"):
            got = self.concern(outcome, concern_id)
            self.assertEqual(got.status, UNRESOLVED, concern_id)
            self.assertIn(".csproj files and no solution", got.reason)

    def test_two_root_solutions_are_not_resolved_by_picking_one(self):
        self.write("A.sln", A_SOLUTION)
        self.write("B.sln", A_SOLUTION)
        got = self.concern(self.bind(), "build")
        self.assertEqual(got.status, UNRESOLVED)
        self.assertIn("no single entry point", got.reason)

    def test_a_dotnet_repository_has_no_single_lint_command(self):
        self.write_manifest("  lint: true\n")
        self.write("A.sln", A_SOLUTION)
        got = self.concern(self.bind(), "lint")
        self.assertEqual(got.status, UNRESOLVED)
        self.assertIn("no single .NET linter", got.reason)

    def test_a_manifest_with_no_checks_block_is_refused(self):
        self.write("A.sln", A_SOLUTION)
        self.write_manifest(
            text="version: 1\nruntime: driftwatchdog\nblocking:\n  - FAIL\n"
        )
        outcome = self.bind()
        self.assertEqual(outcome.status, REFUSED)
        self.assertIn("no `checks:` block", outcome.detail)
        self.assertEqual(outcome.concerns, [])

    def test_a_missing_manifest_is_reported_not_invented(self):
        self.unlink_manifest()
        outcome = self.bind()
        self.assertEqual(outcome.status, NO_MANIFEST)
        self.assertFalse((self.repo / ".ai-gate" / "gate.yaml").exists())

    def test_a_derived_command_is_never_derived_from_prose(self):
        # A command written in a manifest's `notes:` is not recovered from it.
        self.write_manifest(
            text=MANIFEST.format(checks="  build: true\n")
            + "notes: |\n  use `cargo build --release` for this one\n"
        )
        self.write("Cargo.toml", '[package]\nname = "a"\n')
        self.assertEqual(self.bound_command("build"), "cargo build")


# --- ambiguity: reported, not resolved ------------------------


class AmbiguityTests(RepoCase):
    def test_two_equally_plausible_entry_points_are_reported_not_chosen(self):
        # `retakeKit`'s shape: a root solution and a root `package.json` with a
        # `test` script. Both can answer `tests`; choosing one would assert a
        # shape the repository does not have.
        self.write("App.sln", A_SOLUTION)
        self.write("App/App.csproj", A_CSPROJ)
        self.write("package.json", json.dumps({"scripts": {"test": "jest"}}))
        got = self.concern(self.bind(), "tests")
        self.assertEqual(got.status, UNRESOLVED)
        self.assertEqual(got.command, "")
        self.assertEqual(
            got.reason,
            "2 equally plausible entry points: dotnet test App.sln "
            "(root solution App.sln); npm test (package.json declares scripts.test)",
        )

    def test_the_ambiguity_reason_names_both_candidates(self):
        self.write("App.sln", A_SOLUTION)
        self.write("App/App.csproj", A_CSPROJ)
        self.write("package.json", json.dumps({"scripts": {"test": "jest"}}))
        got = self.concern(self.bind(), "tests")
        self.assertIn("dotnet test App.sln", got.reason)
        self.assertIn("npm test", got.reason)

    def test_an_ambiguous_repository_binds_neither_concern(self):
        self.write_manifest(TESTS_ONLY)
        self.write("App.sln", A_SOLUTION)
        self.write("App/App.csproj", A_CSPROJ)
        self.write("package.json", json.dumps({"scripts": {"test": "jest"}}))
        outcome = self.bind()
        self.assertEqual(
            [c.command for c in outcome.concerns if c.status == BOUND], []
        )
        self.assertNotIn("commands:", outcome.after)

    def test_a_root_candidate_beats_a_nested_one(self):
        # `linglitch`'s shape: the solution is at the root and the Node manifest
        # is under `frontend/`, so the root entry point wins on its own.
        self.write("App.sln", A_SOLUTION)
        self.write("App/App.csproj", A_CSPROJ)
        self.write("web/package.json", json.dumps({"scripts": {"test": "vitest"}}))
        self.assertEqual(self.bound_command("tests"), "dotnet test App.sln")

    def test_a_manifest_that_cannot_answer_is_dropped_before_ambiguity(self):
        # `alltools-platform`'s shape: the root `package.json` has no `test`
        # script, so it is not a candidate at all and the Rust workspace is not
        # reported as ambiguous.
        self.write("package.json", json.dumps({"scripts": {"build": "tsc"}}))
        self.write("Cargo.toml", "[workspace]\nmembers = [\"a\"]\n")
        self.assertEqual(self.bound_command("tests"), "cargo test --workspace")

    def test_a_nested_solution_still_names_its_own_path(self):
        self.write("backend/Linglitch.slnx", A_SLNX)
        got = self.concern(self.bind(), "build")
        self.assertEqual(got.command, "dotnet build backend/Linglitch.slnx")
        self.assertEqual(got.evidence, "the only solution, backend/Linglitch.slnx")


# --- the write contract ---------------------------------------


class WriteContractTests(RepoCase):
    def test_a_dry_run_writes_nothing(self):
        self.write_manifest()
        self.write("A.sln", A_SOLUTION)
        before = (self.repo / ".ai-gate" / "gate.yaml").read_bytes()
        outcome = self.bind(apply=False)
        self.assertEqual(self.concern(outcome, "build").status, BOUND)
        self.assertFalse(outcome.wrote)
        self.assertEqual((self.repo / ".ai-gate" / "gate.yaml").read_bytes(), before)

    def test_apply_writes_the_derived_command(self):
        self.write_manifest()
        self.write("A.sln", A_SOLUTION)
        outcome = self.bind(apply=True)
        self.assertTrue(outcome.wrote)
        self.assertIn("  build: 'dotnet build A.sln'\n", self.manifest_text())

    def test_apply_preserves_the_everything_else_in_the_manifest(self):
        self.write_manifest(text=WITH_COMMANDS)
        self.write("A.sln", A_SOLUTION)
        self.bind(apply=True)
        text = self.manifest_text()
        self.assertIn("  build: cargo build --all-targets\n", text)
        self.assertIn("  tests: 'dotnet test A.sln'\n", text)

    def test_a_second_run_derives_nothing_to_render(self):
        # Idempotence is a property of the run, not of `render_manifest`: the
        # second run classifies the already-bound concern as ALREADY_BOUND, so
        # there is no binding left to insert and the file is not rewritten.
        self.write_manifest()
        self.write("A.sln", A_SOLUTION)
        first = self.bind(apply=True)
        self.assertEqual(self.concern(first, "build").status, BOUND)
        before = self.manifest_text()
        second = self.bind(apply=False)
        self.assertEqual(self.concern(second, "build").status, ALREADY_BOUND)
        self.assertFalse(second.wrote)
        self.assertEqual(second.after, second.before)
        self.assertEqual(self.manifest_text(), before)

    def test_the_generated_comment_is_written_once(self):
        self.write_manifest()
        self.write("A.sln", A_SOLUTION)
        self.bind(apply=True)
        self.assertEqual(self.manifest_text().count(GENERATED_MARKER), 1)
        # And a further apply does not accumulate a second copy.
        self.bind(apply=True)
        self.assertEqual(self.manifest_text().count(GENERATED_MARKER), 1)

    def test_bindings_land_in_the_manifests_own_checks_order(self):
        # The concerns are handed to the renderer in the order `checks:` lists
        # them, so the result reads in the repository's own order.
        self.write_manifest("  tests: true\n  build: true\n")
        self.write("A.sln", A_SOLUTION)
        self.bind(apply=True)
        text = self.manifest_text()
        self.assertLess(
            text.index("  tests: 'dotnet test A.sln'"),
            text.index("  build: 'dotnet build A.sln'"),
        )

    def test_a_persons_own_command_is_left_in_place(self):
        # A person wrote a different command: it is reported, never clobbered.
        # The sibling concern that was *not* declared is still bound, so the
        # check is on the hand-written line itself, not on the whole file.
        self.write_manifest(
            text=MANIFEST.format(checks=BUILD_AND_TESTS).replace(
                "blocking:",
                "commands:\n  build: 'cargo build --release --all-features'\nblocking:",
            )
        )
        self.write("Cargo.toml", '[package]\nname = "a"\n')
        before = self.manifest_text()
        outcome = self.bind(apply=True)
        got = self.concern(outcome, "build")
        self.assertEqual(got.status, CONFLICT)
        self.assertIn("left untouched", got.reason)
        after = self.manifest_text()
        # The hand-written line is byte-identical, and the derived command for
        # the same concern appears nowhere.
        self.assertEqual(
            [line for line in after.splitlines() if line.startswith("  build:")],
            [line for line in before.splitlines() if line.startswith("  build:")],
        )
        self.assertNotIn("  build: 'cargo build'\n", after)
        # The sibling concern that was not hand-written is still bound.
        self.assertIn("  tests: 'cargo test'\n", after)

    def test_a_conflict_is_counted_as_left_in_place_and_not_as_debt(self):
        # A conflicting concern has a command the gate will run, so it is not an
        # unbound check. Counting it as debt would report wired checks as gaps.
        # `discover_repos` only finds a repository that has a `.git`, so the
        # fixture is `git init`ed before the fleet-level roll-up is asserted.
        self.write_manifest(
            text=MANIFEST.format(checks=BUILD_AND_TESTS).replace(
                "blocking:",
                "commands:\n  build: 'cargo build --release --all-features'\nblocking:",
            )
        )
        self.write("Cargo.toml", '[package]\nname = "a"\n')
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        report = run(self.tmp, apply=False, check_clean=False)
        self.assertEqual(len(report.conflicts()), 1)
        self.assertEqual(report.debt_total(), 0)
        self.assertEqual(report.count(RESOLVED), 1)

    def test_an_identical_existing_command_is_already_bound_not_a_conflict(self):
        for style in ("'dotnet build A.sln'", '"dotnet build A.sln"', "dotnet build A.sln"):
            with self.subTest(style=style):
                self.write_manifest(
                    text=MANIFEST.format(checks="  build: true\n").replace(
                        "blocking:", f"commands:\n  build: {style}\nblocking:"
                    )
                )
                self.write("A.sln", A_SOLUTION)
                got = self.concern(self.bind(), "build")
                self.assertEqual(got.status, ALREADY_BOUND)
                self.assertEqual(got.command, "dotnet build A.sln")

    def test_the_comparison_against_an_existing_command_is_semantic(self):
        self.assertEqual(unquote_scalar("'cargo build'"), "cargo build")
        self.assertEqual(unquote_scalar('"git diff --check"'), "git diff --check")
        self.assertEqual(unquote_scalar("cargo build  # the fast one"), "cargo build")
        self.assertEqual(unquote_scalar("'rg -e ''password'''"), "rg -e 'password'")

    def test_only_the_concerns_the_manifest_declared_are_bound(self):
        # The repository selects `tests` and nothing else, so it must not gain a
        # `security` command it never asked for.
        self.write_manifest(TESTS_ONLY)
        self.write("package.json", json.dumps({"scripts": {"test": "jest"}}))
        outcome = self.bind(apply=True)
        self.assertEqual([c.concern for c in outcome.concerns], ["tests"])
        text = self.manifest_text()
        self.assertIn("  tests: 'npm test'\n", text)
        self.assertNotIn("security", text)

    def test_a_false_check_stays_false_and_is_not_bound(self):
        self.write_manifest("  build: false\n  tests: true\n")
        self.write("package.json", json.dumps({"scripts": {"test": "jest"}}))
        outcome = self.bind(apply=True)
        self.assertEqual([c.concern for c in outcome.concerns], ["tests"])
        self.assertIn("  build: false\n", self.manifest_text())
        self.assertNotIn("build:", self.manifest_text().split("commands:")[1])

    def test_no_checks_value_is_changed(self):
        self.write_manifest("  build: true\n  tests: true\n  security: false\n")
        self.write("A.sln", A_SOLUTION)
        self.bind(apply=True)
        self.assertIn("  security: false\n", self.manifest_text())
        self.assertIn("  build: true\n", self.manifest_text())

        self.assertIn("  build: true\n", self.manifest_text())


class GitWriteContractTests(GitRepoCase):
    """The write paths that stop at `git status` before touching a file."""

    def test_a_dirty_manifest_is_skipped_not_written(self):
        self.write("A.sln", A_SOLUTION)
        self.commit()
        # The owner's uncommitted edit: modify the manifest without staging it.
        with (self.repo / ".ai-gate" / "gate.yaml").open("a", encoding="utf-8") as handle:
            handle.write("# owner WIP\n")
        before = self.manifest_text()
        outcome = bind_repo(self.repo, apply=True, check_clean=True)
        self.assertEqual(outcome.status, DIRTY)
        self.assertFalse(outcome.wrote)
        self.assertEqual(self.manifest_text(), before)

    def test_a_clean_repository_is_written(self):
        self.write("A.sln", A_SOLUTION)
        self.commit()
        outcome = bind_repo(self.repo, apply=True, check_clean=True)
        self.assertTrue(outcome.wrote)
        self.assertIn("dotnet build A.sln", self.manifest_text())

    def test_an_untracked_manifest_is_treated_as_dirty(self):
        self.write("A.sln", A_SOLUTION)
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        outcome = bind_repo(self.repo, apply=True, check_clean=True)
        self.assertEqual(outcome.status, DIRTY)


class WorkspaceWriteTests(GitRepoCase):
    """The write contract across a whole fixture workspace, via `run()`."""

    def workspace(self) -> Path:
        root = self.tmp / "ws"
        specs = {
            "argoset": (BUILD_AND_TESTS, {"Cargo.toml": "[workspace]\nmembers = []\n"}),
            "cvunify": ("  build: true\n", {"CvUnify.slnx": A_SLNX}),
            "alethefy": (
                BUILD_AND_TESTS,
                {
                    "pyproject.toml": "[project]\nname = 'p'\n",
                    "tests/test_x.py": "import unittest\nclass T(unittest.TestCase):\n"
                    "    def test_a(self):\n        pass\n",
                },
            ),
        }
        for name, (checks, files) in specs.items():
            repo = root / name
            (repo / ".ai-gate").mkdir(parents=True)
            (repo / ".ai-gate" / "gate.yaml").write_text(
                MANIFEST.format(checks=checks), encoding="utf-8"
            )
            for relative, body in files.items():
                target = repo / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(body, encoding="utf-8")
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
            subprocess.run(
                [
                    "git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "base",
                ],
                cwd=repo,
                check=True,
            )
        return root

    def manifests(self, root: Path) -> dict:
        return {
            path.name: path.read_bytes()
            for path in sorted(root.glob("*/.ai-gate/gate.yaml"))
        }

    def test_a_dry_run_over_a_workspace_writes_nothing(self):
        root = self.workspace()
        before = self.manifests(root)
        report = run(root, apply=False)
        self.assertEqual(len(report.outcomes), 3)
        self.assertEqual(self.manifests(root), before, "a dry run changed a manifest")
        self.assertFalse(any(o.wrote for o in report.outcomes))

    def test_apply_then_a_second_apply_is_byte_for_byte_stable(self):
        root = self.workspace()
        run(root, apply=True)
        first = self.manifests(root)
        run(root, apply=True)
        self.assertEqual(self.manifests(root), first, "the second apply changed a manifest")

    def test_the_run_counts_roll_up_statuses(self):
        root = self.workspace()
        report = run(root, apply=False)
        self.assertEqual(report.names(RESOLVED), ["argoset", "cvunify"])
        self.assertEqual(report.names(PARTIAL), ["alethefy"])
        self.assertEqual(report.count(DIRTY), 0)
        self.assertEqual(report.count(REFUSED), 0)
        # `alethefy` is a pure-Python package: one concern bound, one refused.
        self.assertEqual(report.debt_total(), 1)

    def test_the_run_can_be_restricted_to_named_repositories(self):
        root = self.workspace()
        report = run(root, apply=False, only=["cvunify"])
        self.assertEqual([o.repo for o in report.outcomes], ["cvunify"])


# --- the debt record ------------------------------------------


class DebtRecordTests(GitRepoCase):
    def workspace(self) -> Path:
        root = self.tmp / "ws"
        for name, checks, files in [
            (
                "alethefy",
                BUILD_AND_TESTS,
                {
                    "pyproject.toml": "[project]\nname = 'p'\n",
                    "tests/test_x.py": "import unittest\nclass T(unittest.TestCase):\n"
                    "    def test_a(self):\n        pass\n",
                },
            ),
            ("argoset", BUILD_AND_TESTS, {"Cargo.toml": "[workspace]\nmembers = []\n"}),
        ]:
            repo = root / name
            (repo / ".ai-gate").mkdir(parents=True)
            (repo / ".ai-gate" / "gate.yaml").write_text(
                MANIFEST.format(checks=checks), encoding="utf-8"
            )
            for relative, body in files.items():
                target = repo / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(body, encoding="utf-8")
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
            subprocess.run(
                ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base"],
                cwd=repo,
                check=True,
            )
        return root

    def debt_file(self, root: Path) -> Path:
        return root / DEBT_FILE

    def call_main(self, root: Path, *args: str) -> tuple[int, str]:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["--root", str(root), *args])
        return code, buffer.getvalue()

    def test_the_debt_record_is_not_written_on_a_dry_run(self):
        root = self.workspace()
        code, out = self.call_main(root)
        self.assertEqual(code, 3, "debt remaining must exit 3")
        self.assertFalse(self.debt_file(root).exists())
        self.assertIn("(not written; dry run)", out)

    def test_the_debt_record_is_written_on_apply(self):
        root = self.workspace()
        code, out = self.call_main(root, "--apply")
        self.assertEqual(code, 3)
        self.assertTrue(self.debt_file(root).exists())
        self.assertIn("(written)", out)

    def test_the_debt_record_names_the_unresolved_concerns(self):
        root = self.workspace()
        self.call_main(root, "--apply")
        debt = json.loads(self.debt_file(root).read_text(encoding="utf-8"))
        self.assertEqual(
            debt["totals"], {"repositories_with_debt": 1, "unresolved_checks": 1}
        )
        self.assertEqual([r["repo"] for r in debt["repositories"]], ["alethefy"])
        entry = debt["repositories"][0]["unresolved"][0]
        self.assertEqual(entry["concern"], "build")
        self.assertEqual(entry["status"], UNRESOLVED)
        self.assertEqual(entry["reason"], PURE_PYTHON_BUILD)

    def test_the_debt_record_does_not_credit_a_conflict_as_debt(self):
        root = self.tmp / "ws"
        repo = root / "argoset"
        (repo / ".ai-gate").mkdir(parents=True)
        (repo / ".ai-gate" / "gate.yaml").write_text(
            MANIFEST.format(checks=BUILD_AND_TESTS).replace(
                "blocking:",
                "commands:\n  build: 'cargo build --release --all-features'\nblocking:",
            ),
            encoding="utf-8",
        )
        (repo / "Cargo.toml").write_text('[package]\nname = "a"\n', encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base"],
            cwd=repo, check=True,
        )
        code, out = self.call_main(root, "--apply")
        debt = json.loads(self.debt_file(root).read_text(encoding="utf-8"))
        self.assertEqual(code, 0, "a conflict is not debt")
        self.assertEqual(debt["totals"]["unresolved_checks"], 0)
        self.assertEqual(debt["repositories"], [])
        # The summary line is column-aligned, so match the number, not the spacing.
        self.assertRegex(out, r"left in place:\s+1\b")

    def test_by_reason_totals_match_the_check_count(self):
        root = self.workspace()
        report = run(root, apply=False)
        debt = build_debt(report, root)
        self.assertEqual(
            sum(group["checks"] for group in debt["by_reason"]),
            len(report.unresolved()),
        )
        self.assertEqual(debt["totals"]["unresolved_checks"], len(report.unresolved()))

    def test_the_debt_record_is_sorted_everywhere(self):
        root = self.workspace()
        debt = build_debt(run(root, apply=False), root)
        names = [r["repo"] for r in debt["repositories"]]
        self.assertEqual(names, sorted(names))
        for group in debt["by_reason"]:
            self.assertEqual(group["repositories"], sorted(group["repositories"]))
            self.assertEqual(group["entries"], sorted(group["entries"]))
            self.assertEqual(group["checks"], len(set(group["entries"])))

    def test_two_dry_runs_produce_the_same_debt_record(self):
        root = self.workspace()
        first = json.dumps(build_debt(run(root, apply=False), root), indent=2) + "\n"
        second = json.dumps(build_debt(run(root, apply=False), root), indent=2) + "\n"
        self.assertEqual(first, second, "the debt record is not reproducible")

    def test_the_debt_record_carries_no_timestamp(self):
        # A `generated_at` field makes every run a diff and trains reviewers to
        # ignore the file.
        root = self.workspace()
        debt = build_debt(run(root, apply=False), root)
        self.assertNotIn("generated_at", debt)
        self.assertEqual(
            [key for key in debt if "time" in key or "date" in key], []
        )

    def test_the_run_exits_zero_when_nothing_is_unresolved(self):
        root = self.tmp / "ws"
        repo = root / "argoset"
        (repo / ".ai-gate").mkdir(parents=True)
        (repo / ".ai-gate" / "gate.yaml").write_text(
            MANIFEST.format(checks=BUILD_AND_TESTS), encoding="utf-8"
        )
        (repo / "Cargo.toml").write_text("[workspace]\nmembers = []\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base"],
            cwd=repo, check=True,
        )
        code, _out = self.call_main(root, "--apply")
        self.assertEqual(code, 0)

    def test_the_verbose_line_is_empty_for_a_repository_with_no_concerns(self):
        self.unlink_manifest()
        outcome = self.bind()
        self.assertEqual(outcome.status, NO_MANIFEST)
        self.assertEqual(format_detail(outcome, True), "")


# --- the per-repository report line ---------------------------


class OutputTests(RepoCase):
    def test_the_verbose_line_shows_the_command_and_its_evidence(self):
        self.write("Cargo.toml", "[workspace]\nmembers = []\n")
        line = format_detail(self.bind(), verbose=True)
        self.assertIn(
            "build=cargo build --workspace <- Cargo.toml (declares [workspace])", line
        )
        self.assertIn("tests=cargo test --workspace", line)

    def test_the_verbose_line_names_an_unresolved_reason(self):
        self.write("pyproject.toml", "[project]\nname = 'p'\n")
        self.assertIn(
            f"build=UNRESOLVED: {PURE_PYTHON_BUILD}",
            format_detail(self.bind(), verbose=True),
        )

    def test_the_verbose_line_marks_a_conflict_without_printing_its_command(self):
        self.write_manifest(
            text=MANIFEST.format(checks="  build: true\n").replace(
                "blocking:", "commands:\n  build: 'cargo build --release'\nblocking:"
            )
        )
        self.write("Cargo.toml", '[package]\nname = "a"\n')
        self.assertEqual(format_detail(self.bind(), verbose=True), "build=CONFLICT")

    def test_a_quiet_line_is_empty(self):
        self.write("A.sln", A_SOLUTION)
        self.assertEqual(format_detail(self.bind(), verbose=False), "")


# --- the manifest reader --------------------------------------


class ReadManifestTests(RepoCase):
    def test_reads_the_selection_in_the_manifests_own_order(self):
        selected, bound, problem = read_manifest(
            MANIFEST.format(checks="  tests: true\n  build: true\n")
        )
        self.assertEqual(problem, "")
        self.assertEqual(selected, ["tests", "build"])
        self.assertEqual(bound, {})

    def test_a_false_check_is_not_a_selection(self):
        selected, _bound, _problem = read_manifest(
            MANIFEST.format(checks="  build: false\n  tests: true\n")
        )
        self.assertEqual(selected, ["tests"])

    def test_reads_the_existing_commands(self):
        _selected, bound, _problem = read_manifest(WITH_COMMANDS)
        self.assertEqual(bound, {"build": "cargo build --all-targets"})

    def test_roll_up_reports_partial_and_unresolved(self):
        self.assertEqual(roll_up([], 0), RESOLVED)
        self.assertEqual(roll_up([self.outcome("build", UNRESOLVED)], 1), UNRESOLVED)
        self.assertEqual(
            roll_up([self.outcome("build", UNRESOLVED), self.outcome("tests", BOUND)], 2),
            PARTIAL,
        )

    @staticmethod
    def outcome(concern_id, status):
        from bind_gate_commands import ConcernOutcome

        return ConcernOutcome("demo", concern_id, status)


# --- the real fleet, tolerantly --------------------------------


class FleetTest(unittest.TestCase):
    """One end-to-end walk of the real workspace.

    Every other test here uses a fixture. This one exists because the two
    errors found in the field were errors of *scale* — 19 repositories on
    `*.slnx` and a repository labelled `typescript` that is a .NET solution —
    and no fixture proves a count. Every assertion is an invariant that must
    hold however the fleet changes; no test names a repository or a number.
    """

    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).parents[2]
        if not (cls.root / "workspace-governance").is_dir():
            raise unittest.SkipTest(f"workspace root not present: {cls.root}")
        cls.report = run(cls.root, apply=False)

    def test_the_fleet_walk_never_refuses_a_repository(self):
        refused = [o for o in self.report.outcomes if o.status == REFUSED]
        self.assertEqual(
            [(o.repo, o.detail) for o in refused],
            [],
            "a repository the tool cannot read is a finding, not an expected state",
        )


    def test_every_path_a_bound_command_names_really_exists(self):
        # The strongest invariant available without running anything: if a
        # command names a file, that file must be in the repository. A binder
        # that points the gate at a path that is not there would fail every
        # check it wires up.
        checked = 0
        for outcome in self.report.outcomes:
            for concern in outcome.concerns:
                if concern.status != BOUND:
                    continue
                for path in paths_in(concern.command) | paths_in(concern.evidence):
                    self.assertTrue(
                        (self.root / outcome.repo / path).exists(),
                        f"{outcome.repo}/{concern.concern}: names a path that is not "
                        f"in the repository: {path}",
                    )
                    checked += 1
        self.assertGreater(checked, 0, "no path was checked at all")

    def test_the_fleet_exercises_the_slnx_path_at_scale(self):
        # The `.slnx` regression, at the scale it actually appeared: many
        # repositories in this fleet carry no `*.sln` at all, and a `*.sln`-only
        # search silently finds nothing in them. A `.slnx` repository must still
        # get a .NET command. Asserted as "at least one exists" and never as a
        # count, so ordinary fleet churn cannot break it.
        from_slnx = [
            (outcome.repo, concern.concern, concern.command)
            for outcome in self.report.outcomes
            for concern in outcome.concerns
            if concern.status == BOUND and ".slnx" in concern.command
        ]
        self.assertTrue(
            from_slnx,
            "no .slnx repository received a .NET command; the .sln-only search bug "
            "is back, or the fleet no longer uses .slnx",
        )
        for repo, concern_id, command in from_slnx:
            for path in paths_in(command):
                self.assertTrue(
                    (self.root / repo / path).exists(),
                    f"{repo}/{concern_id}: {command} names a file that is not there",
                )

    def test_no_bound_dotnet_command_is_missing_its_entry_file(self):
        # A `dotnet` command must name a solution or a project. A repository
        # with neither is expected to be refused, not handed a bare `dotnet
        # build` that cannot run.
        checked = 0
        for outcome in self.report.outcomes:
            for concern in outcome.concerns:
                if concern.status != BOUND:
                    continue
                if not concern.command.startswith("dotnet "):
                    continue
                checked += 1
                self.assertTrue(
                    paths_in(concern.command),
                    f"{outcome.repo}/{concern.concern}: {concern.command} names no file",
                )
        self.assertGreater(checked, 0, "no .NET command was bound across the fleet")

    def test_every_unresolved_concern_carries_a_reason(self):
        for concern in self.report.unresolved():
            self.assertTrue(
                concern.reason,
                f"{concern.repo}/{concern.concern} is unresolved with no reason",
            )

    def test_every_bound_concern_carries_a_command_and_its_evidence(self):
        for outcome in self.report.outcomes:
            for concern in outcome.concerns:
                if concern.status != BOUND:
                    continue
                self.assertTrue(concern.command, f"{outcome.repo}/{concern.concern}")
                self.assertTrue(
                    concern.evidence, f"{outcome.repo}/{concern.concern} has no evidence"
                )


# Suffixes that make a token a file rather than prose. A concern's evidence is
# a sentence, so only these are read as paths and checked against the disk.
BUILD_FILE_SUFFIXES = (
    ".sln", ".slnx", ".csproj", ".fsproj", ".vbproj",
    ".json", ".toml", ".yaml", ".yml", ".ini", ".cfg",
    ".mjs", ".js", ".ts", ".sh", ".py", ".gradle", ".xml",
)
PATH_TOKEN = re.compile(r"^[A-Za-z0-9_.\-/]+$")


def paths_in(text: str) -> set:
    """Every build-file path named in `text`, and nothing that is only prose."""
    found = set()
    for token in text.replace("(", " ").replace(")", " ").replace("`", " ").split():
        cleaned = token.strip(",;:'\"`")
        if PATH_TOKEN.match(cleaned) and cleaned.endswith(BUILD_FILE_SUFFIXES):
            found.add(cleaned)
    return found


if __name__ == "__main__":
    unittest.main()
