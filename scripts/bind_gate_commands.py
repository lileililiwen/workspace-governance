#!/usr/bin/env python3
"""Bind every gate check a repository declares to a command derived from disk.

Ruling D18 in this workspace: *a verifier that no gate runs does not gate;
wire every check into the gate that blocks, or it is documentation.* Measured
on 2026-10-04, 76 of 81 repositories declared gate checks, 69 of them declared
at least one required check with no command bound, and 283 required checks were
unbound in total. The Gate's own wording for that state is `UNBOUND` — "no
command declared for this concern; no execution was attempted" — and it counts
the project as failing.

`bind_verification_command.py` closed the same gap for the one concern whose
command a repository declares for itself. It cannot close this one, because a
`verification.command` is not a per-concern command: `kairosa`'s is
`openspec validate --all --strict --no-interactive`, which is not a test
command, and it is already bound there. This tool is about the other concerns.

## Why this walks the disk and never reads the label

`.project.json` `stack` disagrees with the disk for 27 of the 81 repositories
by shape alone. `linglitch` declares `typescript` and carries a .NET solution
under `backend/` with its Node manifest under `frontend/`. `alltools-platform`
declares `python` and has no Python at its root. `loreMix` declares `typescript`
and has `LoreMix.slnx` at its root. 19 repositories carry **no `*.sln` at all**
and use `*.slnx` instead, which a `.sln` glob cannot see.

So `stack` is not an argument of any function here. It is not read, and it
cannot leak in later.

## What the gate selects, and why the debt record had to learn it

A manifest selects a check two ways: by listing it under `checks:`, and by
naming a `profile:` whose default set the gate schedules anyway. The gate
fails on an unbound *required* check either way. This tool originally read
only the first, so a repository whose only unbound checks came from its
profile dropped out of `repositories` altogether — 30 repositories and 122
checks, while the gate was failing on all of them. A debt record naming 48
of 170 gaps reads as complete, which is worse than no record at all.

`PROFILE_DEFAULTS` and `gate_required` now mirror the gate's own resolution,
and `GateOracleTest` in `tests/test_bind_gate_commands.py` checks that
mirror against the real binary: the (repository, concern) pairs in this
record MUST equal the set `driftwatchdog gate --dry-run` reports as unbound.
The table is a copy of `profile_defaults` in
`driftwatchdog/src/gate/manifest.rs`; the test is what keeps the copy honest,
and it skips rather than fails when the binary has not been built.

A check only the profile scheduled is **derived first**. The gate's
`.ai-gate` reader refuses a manifest whose `commands:` names a check the
manifest does not select (`aigate.rs:213`), so this tool used to record such
a check as debt and write nothing. That was the right refusal guarding the
wrong boundary: a repository naming `profile: product` has already committed
to the concerns that profile schedules, and the gate already fails it for not
binding them, so the correct write is **both** a `checks: <id>: true` entry
and a `commands: <id>` entry. It is done in one operation, and only when a
checker is genuinely reachable — see `governance_concern`. Where none is, the
concern stays in the debt record, because a selection with no command behind
it is a worse state than the gap it replaced.

## The gate protocol, and which checkers can satisfy it

`driftwatchdog/src/commands/gate.rs:206-208` builds
`AdapterInput { program: "sh", args: ["-c", cmd], working_dir: proj.root }`
and `checker/runner.rs:103` gives the child `Stdio::null()`. **A bound command
gets no stdin.** The environment is not cleared (`runner.rs:99`), so it
inherits this process's. A command must therefore work from argv and the
inherited environment and report through stdout and its exit code.

That protocol is what decides the producers:

* `workspace_check.py --json` emits `{findings: [{code, level, message,
  project}], summary}` — exactly `parse_report`'s shape at
  `governance/mod.rs:141`, with exit 0/1 expected. **Bound.**
* `product_code_quality.py` is fail-closed on a `quality` block and exits 2
  without one. It emits `schema_version`, not the `version` `parse_envelope`
  requires (`adapters.rs:1040`), so it always takes the text-mode exit-code
  path. **Bound only where the repository already declares that policy.**
* `forge_governance_adapter.py` reads `sys.stdin.read()` and emits an
  observation (`status`/`detail`/`evidence`), not a findings report. With no
  stdin it reads an empty input, and the report parser would not recognise the
  output. **Never bound** — it is a one-input adapter, not a checker.

`workspace_check.py --root ..` passes the workspace root explicitly on
purpose. Its default is the directory holding `projects.json`, which is this
repository, and from a sibling that default makes all 81 registered projects
report `PROJECT_MISSING` against the sibling's own subdirectories. 81 false
findings is not a pass.

## What it refuses to do

* **Never invents a command.** An unknown shape, a `package.json` without the
  script the concern needs, an undetectable test runner, a pure-Python
  `build`, and two equally plausible entry points are all *unresolved*, with
  the reason and the evidence. A wrong command is worse than an honest gap.
* **Never invents a policy.** `placeholder-threshold` and
  `product-code-boundary` need a `quality` block in the repository's own
  `.project.json`. Which directories are product, which languages, and what
  threshold are owner decisions, so the block is named in the debt record and
  left unwritten.
* **Never binds a concern the gate does not require.** Only a check the
  manifest selected, or one its `profile:` scheduled and it did not disable,
  exempt, or already bind. A disabled, exempted, `"optional"`, or
  unselected check is left alone whether or not a command could be derived.
* **Never overwrites an operator's binding.** An existing `commands.<concern>`
  that differs from the derived one is a `CONFLICT` and is left exactly as it
  is. An identical one is `ALREADY_BOUND`.
* **Never mines prose.** A command written in a manifest's `notes:` is not
  recovered from it; a check named in free text is not a declaration this tool
  can act on.
* **Never writes without `--apply`.** The default is a dry run.
* **Never exits clean while debt remains.** Exit 3, with no flag to suppress it.

## Idempotence

The second run over an already-bound repository derives the same commands,
finds them already present, and writes nothing, so the file is byte-for-byte
unchanged. The generated comment is written once, guarded by its own marker
text, so a partial binding does not accumulate a second copy of it.

## Deletion

This host's `rm` is a recoverable-delete shim that prints to stdout and can
fail. Nothing here deletes anything.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from bind_verification_command import (  # noqa: E402
    entry_value,
    discover_repos,
    is_dirty,
    top_level_block_bounds,
    yaml_scalar,
)

PROJECT_JSON = ".project.json"
GATE_YAML = ".ai-gate/gate.yaml"
DEBT_FILE = "gate-debt.json"

# One line a reader can grep for to tell generated policy from hand-written
# policy without opening this file. Doubled quotes stay literal inside a
# double-quoted Python string only when escaped, so it is written plainly.
GENERATED_MARKER = "workspace-governance/scripts/bind_gate_commands.py"
GENERATED_COMMENT = (
    f"  # Generated by {GENERATED_MARKER} from the files on disk in this\n"
    "  # repository, for the concerns this manifest already selects under\n"
    "  # `checks:`. A verifier that no gate runs does not gate (ruling D18).\n"
    "  # Re-run the generator to update these; do not hand-edit. Concerns it\n"
    "  # could not derive are recorded in gate-debt.json, not guessed.\n"
)

# Directories that hold a dependency's files rather than this repository's.
# `alethefy`'s only `conftest.py` is `.venv/…/site-packages/numpy/conftest.py`;
# reading it would make a vendored file look like pytest configuration.
SKIP_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        "target",
        "bin",
        "obj",
        ".venv",
        "venv",
        "dist",
        "build",
        ".next",
        ".nuxt",
        "site-packages",
        ".dart_tool",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "__pycache__",
        ".gradle",
        "vendor",
        "TestResults",
    }
)

MAX_DEPTH = 6

SOLUTION_SUFFIXES = (".sln", ".slnx")
PROJECT_SUFFIX = ".csproj"

# Per-concern status.
BOUND = "BOUND"
ALREADY_BOUND = "ALREADY_BOUND"
CONFLICT = "CONFLICT"
UNRESOLVED = "UNRESOLVED"

# Per-repository roll-up.
RESOLVED = "RESOLVED"
PARTIAL = "PARTIAL"
NO_MANIFEST = "NO_MANIFEST"
DIRTY = "DIRTY"
REFUSED = "REFUSED"

# A concern is only debt when it has no command at all. A `CONFLICT` has a
# command: a person wrote it, the gate will run it, and this tool leaves it
# alone. Counting that as debt would report 123 wired checks as unbound,
# which is the opposite of what the Gate sees.
NOT_RESOLVED = (UNRESOLVED,)

# Concerns whose command is a repository-wide property rather than a
# per-language one. `labrys` binds its `repository_integrity` to exactly
# this, and `therapist-commons` binds its `repository` to the same command.
REPOSITORY_CONCERNS = ("repository", "repository_integrity")

# The three concern ids three repositories use for the same OpenSpec change-name
# preflight. One script, three labels, because the labels are per-repository
# vocabulary and the command is the same file in all of them.
OPENSPEC_NAME_CONCERNS = (
    "openspec_names",
    "openspec_change_names",
    "openspec_name_preflight",
)

OPENSPEC_NAMES_SCRIPT = "scripts/check-openspec-change-names.mjs"

# Concern id -> repository script, for the checks a repository implements as its
# own script rather than as a build-system command. The path is exact; a
# repository that has not written the script does not get a command.
SCRIPT_CONCERNS = {
    "product_quality": ("python3 scripts/product_code_quality.py .", "scripts/product_code_quality.py"),
}

SCRIPT_SUFFIXES = (".sh", ".mjs", ".js", ".py")

# The concerns a build system answers. A concern outside this set is a
# repository's own check, and is looked for as a script instead.
SHAPE_CONCERNS = ("build", "tests", "security", "format", "lint")

# --- what a `profile:` selects -----------------------------------

# The concerns a built-in gate profile schedules on its own, mirroring
# `profile_defaults` in driftwatchdog's `src/gate/manifest.rs` (checked
# against the built binary by `GateOracleTest`, which fails if this table
# and the gate ever disagree).
#
# This is the selection a manifest makes by naming a profile rather than by
# listing a check. `aesthra` lists six concerns and says `profile: product`;
# the gate then schedules four more it never wrote down, and fails on the
# three that bind no command. A binder that reads only the `checks:` block
# cannot see them, which is exactly how 30 repositories whose only unbound
# checks were profile-scheduled went missing from the debt record while the
# gate was failing on them.
PRODUCT_PROFILE_CONCERNS = (
    "governance-quality",
    "placeholder-threshold",
    "product-code-boundary",
    "source-file-size",
)
RELEASE_GATE_CONCERNS = ("capability-conformance", "release-evidence")
DEPLOYABLE_CONCERNS = ("ci-contract", "compose-contract")

PROFILE_DEFAULTS: dict[str, tuple[str, ...]] = {
    "backend": ("api-contract", "migration", "secret-scan"),
    "frontend": ("a11y", "api-contract", "responsive"),
    "full": ("a11y", "api-contract", "migration", "responsive", "secret-scan"),
    "minimal": (),
    "product": PRODUCT_PROFILE_CONCERNS,
    "rust-product": PRODUCT_PROFILE_CONCERNS,
    "release": RELEASE_GATE_CONCERNS,
    "deployable": DEPLOYABLE_CONCERNS,
}

# The gate runs this one itself, in-process, and never counts it unbound
# (`is_source_file_size_concern`). Deriving a command for it would hand the
# gate a binding for a check it never asks a command for, and recording it
# as debt would name a failure that does not exist.
IN_PROCESS_CONCERNS = frozenset({"source-file-size"})

# The .NET command for each concern, given the resolved entry point. The
# dependency-audit form matches the one .NET security binding already
# proven in this fleet (`therapist-commons`), minus `--format json`, which
# needs SDK 9.0.200+ and would be a portability hazard for a repository
# this tool has not read a `global.json` for.
DOTNET_COMMANDS = {
    "build": lambda entry: f"dotnet build {entry}",
    "tests": lambda entry: f"dotnet test {entry}",
    "security": lambda entry: (
        f"dotnet list {entry} package --vulnerable --include-transitive --no-restore"
    ),
    "format": lambda entry: f"dotnet format {entry} --verify-no-changes",
}

# Declared Python security tooling -> the command that runs it. A Python
# dependency audit is not in the standard library, so unlike `npm audit` it is
# bound only when the repository declares the tool in its own dependencies.
PYTHON_SECURITY_TOOLS = {
    "pip-audit": "pip-audit",
    "pip_audit": "pip-audit",
    "bandit": "bandit -r .",
    "safety": "safety check",
}

DEPENDENCY_FILES = ("requirements.txt", "requirements-dev.txt", "requirements-test.txt", "Pipfile")

# A module-level bare test function starts at column 0. An indented `def
# test_x(self):` is a `unittest.TestCase` method, and treating those as bare
# functions would make every unittest suite in the fleet look like a pytest
# suite: `workspace-governance`'s own 24 test files are all TestCase methods.
BARE_TEST_DEF = re.compile(r"^def\s+test_", re.MULTILINE)
# The same shape at any indent, used only to ask whether a file defines a test
# at all. `alethefy` ships an empty `tests/test_cli_json_contract.py`, and an
# empty file is not evidence for or against any runner.
ANY_TEST_DEF = re.compile(r"^\s*def\s+test_", re.MULTILINE)
IMPORT_PYTEST = re.compile(r"^\s*(import\s+pytest|from\s+pytest\s+import)", re.MULTILINE)
IMPORT_UNITTEST = re.compile(r"^\s*(import\s+unittest|from\s+unittest\s+import)", re.MULTILINE)


# --- reading the manifest's own declarations ------------------


def block_entries(lines: list[str], key: str) -> list[tuple[str, str]]:
    """`(entry, value)` for every `  <entry>: <value>` line in a top-level block.

    The value keeps its own quoting and is stripped of surrounding
    whitespace only, so `commands:` and `checks:` are read the same way
    whichever style wrote them. Comment lines, list items and anything not
    at two-space indentation are skipped.
    """
    bounds = top_level_block_bounds(lines, key)
    if bounds is None:
        return []
    start, end = bounds
    entries = []
    for index in range(start + 1, end):
        line = lines[index]
        if not line.startswith("  ") or line.strip().startswith(("#", "-")):
            continue
        if ":" not in line:
            continue
        entry, value = line.strip().split(":", 1)
        entries.append((entry.strip(), value.strip()))
    return entries


def top_level_scalar(lines: list[str], key: str) -> str:
    """The value of a top-level `key: value` line, unquoted, or `""`."""
    prefix = f"{key}:"
    for line in lines:
        if not line.startswith(prefix):
            continue
        return unquote_scalar(line[len(prefix):].strip())
    return ""


def read_manifest(text: str) -> tuple[list[str], dict[str, str], str]:
    """Return `(selected, commands, problem)` for one manifest.

    `selected` is the concern ids the manifest turned on, in the order the
    manifest lists them, so a binding lands in the order the repository
    declared rather than in the order this tool happened to derive them.
    `problem` is non-empty when the manifest cannot be read as a gate
    manifest, in which case nothing may be written.

    Only a `true` value is a required selection. `false` and `"optional"`
    are read by [`read_gate_policy`] instead: both leave the concern out of
    the gate's unbound set, and `"optional"` is a scheduling decision the
    gate does not fail on.
    """
    lines = text.splitlines(keepends=True)
    if top_level_block_bounds(lines, "checks") is None:
        return [], {}, "no `checks:` block, so the manifest selects nothing to bind"
    selected = [entry for entry, value in block_entries(lines, "checks") if value == "true"]
    bound = dict(block_entries(lines, "commands"))
    return selected, bound, ""


@dataclass
class GatePolicy:
    """The three manifest keys that decide which checks the gate fails on
    without the manifest listing them.

    `profile` names the built-in profile whose default selection applies;
    `disabled` and `exempt` are concerns the manifest took out of that
    selection again, by `checks: <id>: false` and by a `not_applicable:`
    exemption with a reason.
    """

    profile: str
    disabled: frozenset[str] = frozenset()
    exempt: frozenset[str] = frozenset()


def read_gate_policy(text: str) -> GatePolicy:
    """Read the selection the gate resolves from keys other than `checks:`.

    The gate's own `.ai-gate` reader (`driftwatchdog/src/gate/aigate.rs`)
    turns `checks: <id>: false` into a disabled check, which *removes* the
    concern even when a profile selected it, and a `not_applicable`
    exemption removes it from the unbound set. Both are read here for the
    same reason: a check the gate does not fail on is not debt, and naming
    it would over-report in the other direction.
    """
    lines = text.splitlines()
    disabled = {
        entry
        for entry, value in block_entries(lines, "checks")
        if value == "false"
    }
    exempt = {entry for entry, _reason in block_entries(lines, "not_applicable")}
    return GatePolicy(
        profile=top_level_scalar(lines, "profile"),
        disabled=frozenset(disabled),
        exempt=frozenset(exempt),
    )


def gate_required(selected: list[str], policy: GatePolicy) -> list[str]:
    """Every concern the gate would report as an unbound required check.

    The manifest's own `checks:` in the order it declares them, then the
    built-in profile's defaults it did not declare, minus everything the
    gate excuses: a check the manifest disabled, a check exempted under
    `not_applicable`, and the one check the gate executes in-process. What
    comes back is what the debt record must name, so this function and the
    gate's `unbound_required_checks` are required to agree.
    """
    declared = set(selected)
    concerns = list(selected)
    concerns.extend(
        concern
        for concern in PROFILE_DEFAULTS.get(policy.profile, ())
        if concern not in declared and concern not in policy.disabled
    )
    return [
        concern
        for concern in concerns
        if concern not in policy.exempt and concern not in IN_PROCESS_CONCERNS
    ]


def profile_only_reason(concern: str, profile: str) -> str:
    """Why a profile-scheduled check is debt this tool will not write away.

    The gate's `.ai-gate` reader refuses a manifest whose `commands:` names
    a check the manifest does not select, so a command for a check that
    only `profile:` selected would not close the gap — it would make the
    manifest unparseable, which fails the gate harder than the gap does.
    The fix is in the manifest, and it is one line.
    """
    return (
        f"the gate schedules {concern} through `profile: {profile}` and this manifest "
        f"does not select it under `checks:`, so the gate refuses a `commands.{concern}` "
        f"entry for it; select it under `checks:` and add scripts/check-{concern}.* to "
        f"bind it, or exempt it under `not_applicable:` with a reason"
    )



# --- detecting the shape from disk -----------------------------


@dataclass
class Shape:
    """What is actually on disk, and where.

    Every field is a path relative to the repository root. Detection never
    consults `.project.json`.
    """

    solutions: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    crates: list[str] = field(default_factory=list)
    workspaces: list[str] = field(default_factory=list)
    node_manifests: list[str] = field(default_factory=list)
    script_keys: dict[str, list[str]] = field(default_factory=dict)
    pubspecs: list[str] = field(default_factory=list)
    python_dirs: list[str] = field(default_factory=list)
    pytest_configs: list[str] = field(default_factory=list)
    security_tools: list[str] = field(default_factory=list)

    def label(self) -> str:
        """A short shape name for the report and the debt record."""
        if self.solutions or self.projects:
            return "dotnet"
        if self.crates:
            return "rust"
        if self.node_manifests:
            return "node"
        if self.pubspecs:
            return "flutter"
        if self.python_dirs:
            return "python"
        return "unknown"


def walk_files(root: Path, max_depth: int = MAX_DEPTH):
    """Yield `(relative_path, absolute_path)` for every file not under a
    skipped directory.

    `os.walk` is used with in-place pruning so a vendored tree is never
    descended into at all, rather than filtered after the fact.
    """
    root_depth = len(root.parts)
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        if len(current.parts) - root_depth > max_depth:
            dirnames[:] = []
            continue
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for filename in sorted(filenames):
            absolute = current / filename
            yield str(absolute.relative_to(root)), absolute


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def is_test_project(path: str) -> bool:
    """True when a `.csproj` path is a test project by .NET convention.

    Used only where it narrows a choice to exactly one candidate; a
    repository with several test projects and no solution stays unresolved
    rather than picking the first in sorted order.
    """
    parts = Path(path).parts
    name = parts[-1]
    if "tests" in {p.lower() for p in parts} or "test" in {p.lower() for p in parts}:
        return True
    stem = name[: -len(PROJECT_SUFFIX)]
    return stem.endswith((".Tests", ".Test", "Tests", "Test"))


def detect_shape(repo: Path) -> Shape:
    """Walk the repository and return what is on disk. Never raises."""
    shape = Shape()
    dependency_text: list[str] = []

    for relative, absolute in walk_files(repo):
        name = Path(relative).name
        depth = len(Path(relative).parts) - 1

        if name.endswith(SOLUTION_SUFFIXES):
            shape.solutions.append(relative)
            continue
        if name.endswith(PROJECT_SUFFIX):
            shape.projects.append(relative)
            continue
        if name == "Cargo.toml":
            shape.crates.append(relative)
            try:
                if "[workspace]" in absolute.read_text(encoding="utf-8", errors="replace"):
                    shape.workspaces.append(relative)
            except OSError:
                pass
            continue
        if name == "package.json":
            shape.node_manifests.append(relative)
            data = read_json(absolute)
            scripts = data.get("scripts") if isinstance(data, dict) else None
            if isinstance(scripts, dict):
                shape.script_keys[relative] = sorted(str(k) for k in scripts)
            continue
        if name == "pubspec.yaml":
            shape.pubspecs.append(relative)
            continue
        if name in DEPENDENCY_FILES and depth == 0:
            try:
                dependency_text.append(absolute.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                pass
            continue
        if name == "pyproject.toml":
            try:
                dependency_text.append(absolute.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                pass
            continue
        if name in ("pytest.ini", "conftest.py", "tox.ini") and depth <= 1:
            shape.pytest_configs.append(relative)
            continue
        if name == "setup.cfg" and depth == 0:
            try:
                if "[tool:pytest]" in absolute.read_text(encoding="utf-8", errors="replace"):
                    shape.pytest_configs.append(relative)
            except OSError:
                pass
            continue
        if re.fullmatch(r"test_[^/]*\.py|test\.py", name) and Path(relative).parts[0] in (
            "tests",
            "test",
        ):
            if "tests" not in shape.python_dirs and "test" not in shape.python_dirs:
                shape.python_dirs.append(Path(relative).parts[0])
            continue

    for text in dependency_text:
        for tool in PYTHON_SECURITY_TOOLS:
            if tool in text and tool not in shape.security_tools:
                shape.security_tools.append(tool)

    return shape


def python_runner(repo: Path, shape: Shape) -> tuple[str, str]:
    """Return `(command, evidence)` for a Python repository's test runner.

    The two runners are not interchangeable, and picking the wrong one is
    worse than refusing: `unittest` discovery finds no `TestCase` in a
    bare-function file and reports success having run nothing. So the test
    files are read.
    """
    config_evidence = ""
    if shape.pytest_configs:
        for config in shape.pytest_configs:
            try:
                text = (repo / config).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "[tool.pytest.ini_options]" in text or config.endswith("pytest.ini"):
                config_evidence = config
                break
            if config.endswith("conftest.py") and config.count("/") == 0:
                config_evidence = config
                break
            if config.endswith("tox.ini") and "[pytest]" in text:
                config_evidence = config
                break
            if config.endswith("setup.cfg") and "[tool:pytest]" in text:
                config_evidence = config
                break
    if config_evidence:
        return "pytest", config_evidence

    directories = [d for d in ("tests", "test") if (repo / d).is_dir()]
    if not directories:
        return "", "no tests/ or test/ directory, and no pytest configuration"
    needs_pytest = False
    defining = 0
    unittest_files = 0
    for directory in directories:
        for path in sorted((repo / directory).rglob("test_*.py")):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if not ANY_TEST_DEF.search(text):
                # A file that defines no test is collected by nobody, so it
                # says nothing about which runner the repository needs.
                continue
            defining += 1
            if BARE_TEST_DEF.search(text) or IMPORT_PYTEST.search(text):
                needs_pytest = True
            if IMPORT_UNITTEST.search(text) or "TestCase" in text:
                unittest_files += 1
    if not defining:
        return (
            "",
            f"no test_*.py under {directories[0]}/ defines a test, so no runner is detectable",
        )
    if needs_pytest:
        return "pytest", f"{directories[0]}/ holds a test file pytest must collect"
    if unittest_files == defining:
        return (
            f"python3 -m unittest discover -s {directories[0]} -v",
            f"{unittest_files} test file(s) in {directories[0]}/ are unittest.TestCase only",
        )
    return (
        "",
        f"{defining} test file(s) in {directories[0]}/ are neither unittest.TestCase nor a "
        "bare def test_, so no runner is shown to collect them",
    )


# --- deriving a command per concern ---------------------------


@dataclass
class Candidate:
    """One entry point that could answer a concern, and its evidence."""

    command: str
    evidence: str
    root_level: bool


def dotnet_entry(shape: Shape, *, for_tests: bool) -> tuple[str, str]:
    """Return `(entry, evidence)` for `dotnet build` / `dotnet test`.

    A solution is the entry point when one exists. Failing that, exactly
    one `.csproj` may be chosen; several with no solution is a finding, not
    a search to guess through.
    """
    if shape.solutions:
        root = [s for s in shape.solutions if "/" not in s]
        if len(root) == 1:
            return root[0], f"root solution {root[0]}"
        if root:
            return "", f"{len(root)} root solutions ({', '.join(root)}); no single entry point"
        if len(shape.solutions) == 1:
            return shape.solutions[0], f"the only solution, {shape.solutions[0]}"
        return "", f"{len(shape.solutions)} solutions and none at the root"
    if not shape.projects:
        return "", "no .sln, .slnx or .csproj file"
    if for_tests:
        tests = [p for p in shape.projects if is_test_project(p)]
        if len(tests) == 1:
            return tests[0], f"the only test project, {tests[0]}"
        if tests:
            return "", f"{len(tests)} test projects and no solution ({', '.join(tests[:4])})"
    if len(shape.projects) == 1:
        return shape.projects[0], f"the only project, {shape.projects[0]}"
    return "", f"{len(shape.projects)} .csproj files and no solution"


# --- comparing an existing command -----------------------------


def unquote_scalar(raw: str) -> str:
    """Return the string a `commands:` entry holds, whichever style wrote it.

    The comparison against an existing binding has to be semantic, not
    byte-exact. The seven already-wired repositories in this fleet write
    their commands three different ways — `cargo build --workspace`,
    `"git diff --check"`, `'npm test'` — and a byte comparison would call
    all three a conflict with a command this tool derived identically.
    """
    value = raw.strip()
    if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
        return value[1:-1].replace("''", "'")
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return value
        return decoded if isinstance(decoded, str) else value
    # A plain scalar ends at an unquoted ` #`, which YAML treats as a comment.
    marker = value.find(" #")
    return value[:marker].rstrip() if marker != -1 else value


def rust_commands(shape: Shape, concern: str) -> list[Candidate]:
    """One candidate per crate manifest, each carrying its own directory.

    A `Cargo.toml` declaring `[workspace]` manages the crates beneath it, so
    those members are not separate entry points: `alltools-platform` has one
    workspace root and 34 members under it, and offering all 35 would be
    noise rather than ambiguity. A nested manifest needs its directory in
    the command, because the Gate runs each command from the repository root.
    """
    workspace_dirs = {str(Path(m).parent) for m in shape.workspaces}

    def under_a_workspace(directory: str) -> bool:
        # A workspace at the repository root owns every crate beneath it.
        if "." in workspace_dirs:
            return True
        return any(directory.startswith(f"{root}/") for root in workspace_dirs)

    candidates = []
    for manifest in shape.crates:
        directory = str(Path(manifest).parent)
        if manifest not in shape.workspaces and under_a_workspace(directory):
            continue
        is_workspace = manifest in shape.workspaces
        prefix = "" if directory == "." else f"cd {directory} && "
        root_level = directory == "."
        note = "declares [workspace]" if is_workspace else "declares no [workspace]"
        if concern == "build":
            command = f"{prefix}cargo build --workspace" if is_workspace else f"{prefix}cargo build"
        elif concern == "tests":
            command = f"{prefix}cargo test --workspace" if is_workspace else f"{prefix}cargo test"
        elif concern == "security":
            command, note = f"{prefix}cargo audit", "cargo-audit is the Rust dependency audit"
        elif concern == "format":
            command, note = f"{prefix}cargo fmt --all --check", "rustfmt is the Rust formatter"
        else:
            command = (
                f"{prefix}cargo clippy --workspace --all-targets -- -D warnings"
                if is_workspace
                else f"{prefix}cargo clippy --all-targets -- -D warnings"
            )
            note = "clippy is the Rust linter"
        candidates.append(Candidate(command, f"{manifest} ({note})", root_level))
    return candidates


def node_commands(shape: Shape, concern: str) -> list[Candidate]:
    """One candidate per `package.json`, only where the script key exists.

    A manifest without the key cannot answer the concern, so it is not a
    candidate at all — that exclusion happens before any ambiguity is
    reported, or a repository whose root Node tooling has no `test` script
    would be reported ambiguous when its Rust workspace can answer.
    """
    key = {
        "build": "build",
        "tests": "test",
        "lint": "lint",
        "format": "format:check",
    }.get(concern)
    candidates = []
    for manifest in shape.node_manifests:
        scripts = set(shape.script_keys.get(manifest, []))
        directory = str(Path(manifest).parent)
        prefix = "" if directory == "." else f"cd {directory} && "
        root_level = directory == "."
        if concern == "security":
            script = next((s for s in ("security", "audit") if s in scripts), None)
            if script:
                candidates.append(
                    Candidate(
                        f"{prefix}npm run {script}",
                        f"{manifest} declares a {script!r} script",
                        root_level,
                    )
                )
            else:
                candidates.append(
                    Candidate(
                        f"{prefix}npm audit --audit-level=high",
                        f"{manifest} has no security script, so this is the npm dependency audit",
                        root_level,
                    )
                )
            continue
        if key is None or key not in scripts:
            continue
        command = f"{prefix}npm test" if key == "test" else f"{prefix}npm run {key}"
        candidates.append(Candidate(command, f"{manifest} declares scripts.{key}", root_level))
    return candidates


def python_candidates(repo: Path, shape: Shape, concern: str) -> tuple[list[Candidate], str]:
    """Return `(candidates, refusal_reason)` for a Python repository.

    Only one runner is offered, and it is the one the files on disk show can
    collect them. Offering both would make every Python repository ambiguous.
    The refusal reason is returned rather than discarded, so a repository whose
    test files no runner can be shown to collect says exactly that.
    """
    candidates = []
    if concern == "tests":
        command, evidence = python_runner(repo, shape)
        if command:
            candidates.append(Candidate(command, evidence, True))
        else:
            return [], evidence
    elif concern == "security":
        # At most one tool is offered. A repository's dependency file can
        # mention several of these in prose, and offering one candidate per
        # mention would report a false ambiguity for a repository that
        # simply declares one of them.
        for tool in PYTHON_SECURITY_TOOLS:
            if tool in shape.security_tools:
                return [
                    Candidate(
                        PYTHON_SECURITY_TOOLS[tool],
                        f"the repository declares the {tool} dependency",
                        True,
                    )
                ], ""
        if not shape.security_tools:
            return [], (
                "no Python security tool is declared in this repository's pyproject.toml or "
                "requirements*.txt, and a Python dependency audit is not in the standard library"
            )
    return candidates, ""


def flutter_candidates(shape: Shape, concern: str) -> list[Candidate]:
    candidates = []
    for manifest in shape.pubspecs:
        directory = str(Path(manifest).parent)
        prefix = "" if directory == "." else f"cd {directory} && "
        if concern == "tests":
            candidates.append(
                Candidate(f"{prefix}flutter test", f"{manifest} is a Flutter package", directory == ".")
            )
    return candidates


def resolve(candidates: list[Candidate]) -> tuple[Candidate | None, str]:
    """Apply the dominance rule and return `(winner, reason_when_refused)`.

    One answer or none. A root-level entry point beats a nested one; two
    candidates of equal standing are two answers, and choosing between them
    would assert a shape the repository does not have.
    """
    if not candidates:
        return None, ""
    if len(candidates) == 1:
        return candidates[0], ""
    roots = [c for c in candidates if c.root_level]
    if len(roots) == 1:
        return roots[0], ""
    remaining = roots or candidates
    described = "; ".join(f"{c.command} ({c.evidence})" for c in remaining)
    return None, f"{len(remaining)} equally plausible entry points: {described}"


@dataclass
class ConcernOutcome:
    """What happened to one concern of one repository."""

    repo: str
    concern: str
    status: str
    command: str = ""
    evidence: str = ""
    reason: str = ""
    # True when this concern is a `BOUND` that the profile scheduled rather
    # than the manifest, so the write must add a `checks: <id>: true` entry
    # beside the `commands:` entry. The gate refuses a `commands:` entry for
    # an unselected check, so the two are written together or not at all.
    selects: bool = False


# --- concerns this workspace's own checkers answer -------------

# The two checkers in *this* repository that answer a gate concern. Both are
# reached from a sibling repository by a relative path, which is why the
# reachability test below is a file check rather than an assumption: the gate
# runs the bound command with the repository root as the working directory
# (`gate.rs` `AdapterInput { working_dir: proj.root }`), so `../<repo>/…`
# resolves for every repository that is a sibling of this one, and resolves
# to nothing for one that is not.
#
# `workspace_check.py --root .. --project <this repository>` is passed the
# workspace root *and* this repository's own name, both explicitly, and both
# omissions are defects rather than defaults:
#
# * without `--root`, the checker's default is the directory holding
#   `projects.json` — this repository — and run from a sibling that default
#   makes all 81 registered projects report `PROJECT_MISSING` against the
#   sibling's own subdirectories. 81 false findings is not a pass.
# * without `--project`, the checker audits the **whole workspace**, and the
#   gate's concern filters findings by *code*, not by project
#   (`governance/mod.rs`: `if !scope.contains(finding.code.as_str())`), so
#   every repository's gate would be failed by every *other* repository's
#   findings. Measured on this fleet: the workspace audit reports 12
#   in-scope findings and not one of them belongs to `bargora` — 4 come from
#   `chronicleaf`, 3 from `metiscope`, 3 from `openlearning`, 1 from
#   `dotnet-platform-libs`. Scoping to one project is what makes the verdict
#   this repository's own rather than the workspace's.
#
# `--project` matches a registry `id` **or** a registry `path`, and the
# `path` of all 81 registered projects is its directory name, so a
# repository's own directory name resolves for every repository here.
GOVERNANCE_CHECKER = "scripts/workspace_check.py"
GOVERNANCE_COMMAND = (
    "python3 ../workspace-governance/scripts/workspace_check.py "
    "--root .. --project {project} --json"
)
GOVERNANCE_EVIDENCE = "the portfolio checker at ../workspace-governance/scripts/workspace_check.py"

PRODUCT_QUALITY_CHECKER = "scripts/product_code_quality.py"
PRODUCT_QUALITY_COMMAND = "python3 ../workspace-governance/scripts/product_code_quality.py ."
PRODUCT_QUALITY_EVIDENCE = "the product-quality checker at ../workspace-governance/scripts/product_code_quality.py"

# Concern -> the checker that answers it, in this workspace.
#
# `placeholder-threshold` and `product-code-boundary` are answered by the
# same script; they are two gates over one scan, and the scan is a single
# policy read.
GOVERNANCE_CHECKERS: dict[str, tuple[str, str, str]] = {
    "governance-quality": (GOVERNANCE_CHECKER, GOVERNANCE_COMMAND, GOVERNANCE_EVIDENCE),
    "placeholder-threshold": (
        PRODUCT_QUALITY_CHECKER,
        PRODUCT_QUALITY_COMMAND,
        PRODUCT_QUALITY_EVIDENCE,
    ),
    "product-code-boundary": (
        PRODUCT_QUALITY_CHECKER,
        PRODUCT_QUALITY_COMMAND,
        PRODUCT_QUALITY_EVIDENCE,
    ),
}

# The concerns whose checker reads a `quality` block out of the repository's
# own `.project.json` and is fail-closed without it. `product_code_quality.py`
# raises `ConfigError("project declaration is missing the 'quality' block")`
# and exits 2 — a configuration error — rather than scanning, so a repository
# without one has no policy to run and the checker cannot answer the concern
# at all. The threshold and the product roots are an owner decision about
# which directories are product and how many placeholders are tolerable, so
# this tool writes none of them: it names the missing block and leaves the
# concern in the debt record.
QUALITY_POLICY_FILE = ".project.json"
QUALITY_POLICY_KEY = "quality"


def has_quality_policy(repo: Path) -> bool:
    """True when the repository's own `.project.json` declares `quality`.

    Read-only and fail-closed in the same direction as the checker: a
    `.project.json` that is absent, unparseable, or holds no `quality` block
    all answer `False`, because all three make the checker exit 2.
    """
    data = read_json(repo / QUALITY_POLICY_FILE)
    return isinstance(data, dict) and isinstance(data.get(QUALITY_POLICY_KEY), dict)


def governance_concern(repo: Path, concern: str) -> tuple[str, str, str]:
    """Derive one of this workspace's own concerns, or refuse by name.

    A repository's **own** `scripts/check-<concern>.*` wins over the
    workspace default, for the same reason it wins everywhere else here: it
    is more specific than the fallback, and a repository that wrote a script
    for this check meant that script. The workspace checker is consulted only
    when the repository wrote none.

    The gate protocol decides what is possible here. `gate.rs:206-208` runs a
    bound command as `sh -c <cmd>` with the repository root as the working
    directory and **no stdin** (`runner.rs:103`, `Stdio::null()`), so a bound
    command has to work from its argument vector and the inherited
    environment and report through stdout and its exit code. Both commands
    below satisfy that: they take a path, print a report on stdout, and exit
    0/1 (and 2 for a configuration error).

    `forge_governance_adapter.py` does **not** satisfy it and is deliberately
    not bound: it reads `sys.stdin.read()` and emits an observation
    (`status`/`detail`/`evidence`) rather than a findings report, so with no
    stdin it sees an empty input and the gate's report parser would not
    recognise the output. It is a one-input adapter, not a checker.
    """
    entry = GOVERNANCE_CHECKERS.get(concern)
    if entry is None:
        return "", "", f"{concern} is not answered by a checker in this workspace"

    own_command, own_evidence, own_reason = script_concern(repo, concern)
    if own_command:
        return own_command, own_evidence, own_reason

    relative, command, evidence = entry

    if not (repo.parent / "workspace-governance" / relative).is_file():
        return (
            "",
            "",
            f"this repository is not a sibling of a workspace-governance checkout, so "
            f"../workspace-governance/{relative} does not exist and the {concern} "
            f"checker cannot be reached from it; {own_reason}",
        )

    if concern in ("placeholder-threshold", "product-code-boundary"):
        if not has_quality_policy(repo):
            return (
                "",
                "",
                f"{relative} reads a `{QUALITY_POLICY_KEY}` block out of this "
                f"repository's {QUALITY_POLICY_FILE} and is fail-closed without one: "
                f"it exits 2 with `project declaration is missing the "
                f"'{QUALITY_POLICY_KEY}' block` and never scans. The block's "
                f"product_roots, languages and placeholder_threshold are an owner "
                f"decision this tool does not invent; add the block to "
                f"{QUALITY_POLICY_FILE}, or exempt the concern under "
                f"`not_applicable:` with a reason",
            )

    # `{project}` is this repository's own directory name, which is also its
    # `path` in the registry for all 81 registered projects. It is read from
    # the path, not from `.project.json`, on the same rule as everything else
    # here: the label is not an input.
    return command.format(project=repo.name), evidence, ""


def derive(concern: str, shape: Shape, repo: Path) -> tuple[str, str, str]:
    """Return `(command, evidence, reason)` for one concern.

    `command` empty means the concern is unresolved and `reason` says why.
    Every rule is gated on a file existing.
    """
    if concern in REPOSITORY_CONCERNS:
        return "git diff --check", "a git checkout, verified by repository discovery", ""

    if concern in OPENSPEC_NAME_CONCERNS:
        if (repo / OPENSPEC_NAMES_SCRIPT).is_file():
            return f"node {OPENSPEC_NAMES_SCRIPT}", OPENSPEC_NAMES_SCRIPT, ""
        return "", "", f"no {OPENSPEC_NAMES_SCRIPT} in this repository"

    if concern in SCRIPT_CONCERNS:
        command, relative = SCRIPT_CONCERNS[concern]
        if (repo / relative).is_file():
            return command, relative, ""
        return "", "", f"no {relative} in this repository"

    if concern in GOVERNANCE_CHECKERS:
        return governance_concern(repo, concern)

    if concern not in SHAPE_CONCERNS:
        return script_concern(repo, concern)

    has_dotnet = bool(shape.solutions or shape.projects)
    has_python = bool(shape.python_dirs or shape.pytest_configs or (repo / "pyproject.toml").is_file())
    only_python = has_python and not (
        has_dotnet or shape.crates or shape.node_manifests or shape.pubspecs
    )

    if concern == "build" and only_python:
        return (
            "",
            "",
            "a pure-Python package has no build step; a packaging build is an owner "
            "decision, not a derivation",
        )
    if concern == "build" and shape.pubspecs and not (has_dotnet or shape.crates or shape.node_manifests):
        return (
            "",
            "",
            "flutter build needs a target platform this repository does not name",
        )
    if concern == "build" and has_dotnet and not shape.solutions and not shape.projects:
        return "", "", "no .NET project on disk to build"

    candidates: list[Candidate] = []
    if has_dotnet:
        if concern == "lint":
            return (
                "",
                "",
                "no single .NET linter command covers a solution and its projects; "
                "declare scripts/check-lint.* if the repository wants one",
            )
        entry, evidence = dotnet_entry(shape, for_tests=concern == "tests")
        if not entry:
            return "", "", evidence
        candidates.append(
            Candidate(DOTNET_COMMANDS[concern](entry), evidence, "/" not in entry)
        )
    if shape.crates:
        candidates.extend(rust_commands(shape, concern))
    if shape.node_manifests:
        candidates.extend(node_commands(shape, concern))
    refusals: list[str] = []
    if has_python:
        python_candidates_found, python_refusal = python_candidates(repo, shape, concern)
        candidates.extend(python_candidates_found)
        if python_refusal:
            refusals.append(python_refusal)
    if shape.pubspecs:
        candidates.extend(flutter_candidates(shape, concern))

    if not candidates:
        if shape.node_manifests:
            key = {"build": "build", "tests": "test", "lint": "lint", "format": "format:check"}.get(concern)
            if key:
                return (
                    "",
                    "",
                    f"no package.json in this repository declares a {key!r} script, so "
                    f"there is no {concern} command to derive",
                )
        if refusals:
            return "", "", refusals[0]
        if shape.pubspecs and concern not in ("build",):
            return "", "", f"no {concern} rule exists for a Flutter package"
        if concern == "build":
            return "", "", "no recognised project shape on disk"
        if concern == "tests":
            return "", "", "no test runner is detectable on disk"
        return "", "", f"no rule derives a {concern} command from the shape on disk"
    winner, reason = resolve(candidates)
    if winner is None:
        return "", "", reason
    return winner.command, winner.evidence, ""


def script_concern(repo: Path, concern: str) -> tuple[str, str, str]:
    """A concern a repository implements as its own script, or nothing.

    `careBridge` and `openpanel` bind their concerns this way, so the
    convention is read off the disk rather than assumed: a repository that
    has not written the script does not get a command.
    """
    found = [
        suffix
        for suffix in SCRIPT_SUFFIXES
        if (repo / "scripts" / f"check-{concern}{suffix}").is_file()
    ]
    if len(found) == 1:
        relative = f"scripts/check-{concern}{found[0]}"
        return relative, relative, ""
    if len(found) > 1:
        names = ", ".join(f"scripts/check-{concern}{s}" for s in found)
        return "", "", f"{concern} has more than one candidate script: {names}"
    return (
        "",
        "",
        f"no rule derives a {concern} command and this repository has no "
        f"scripts/check-{concern}.* to run",
    )


# --- the outcome types -----------------------------------------


@dataclass
class Outcome:
    """What happened to one repository.

    The first six fields are the sibling's, unchanged, so a caller that
    reads `repo`/`status`/`detail`/`wrote`/`before`/`after` reads the same
    thing here. `concerns` is new because a repository's unit of work in
    this tool is a concern.
    """

    repo: str
    status: str
    detail: str = ""
    wrote: bool = False
    before: str = ""
    after: str = ""
    concerns: list[ConcernOutcome] = field(default_factory=list)
    shape: str = ""


@dataclass
class Report:
    """The whole run, in a form a caller can assert on and a human can read."""

    outcomes: list[Outcome] = field(default_factory=list)

    def add(self, outcome: Outcome) -> None:
        self.outcomes.append(outcome)

    def count(self, status: str) -> int:
        return sum(1 for o in self.outcomes if o.status == status)

    def names(self, status: str) -> list[str]:
        return [o.repo for o in self.outcomes if o.status == status]

    def unresolved(self) -> list[ConcernOutcome]:
        return [c for o in self.outcomes for c in o.concerns if c.status in NOT_RESOLVED]

    def debt_total(self) -> int:
        return len(self.unresolved())

    def conflicts(self) -> list[ConcernOutcome]:
        return [c for o in self.outcomes for c in o.concerns if c.status == CONFLICT]


# --- writing, reusing the sibling's comment-preserving editor ---


def render_checks(text: str, selections: list[str]) -> str:
    """Add `checks: <concern>: true` for each name in `selections`.

    The gate's `.ai-gate` reader refuses a document whose `commands:` names a
    check the manifest does not select (`aigate.rs:213`), so a command for a
    profile-scheduled concern needs this entry to exist. It is written with
    the value `true` and never over an existing key: a repository that
    already lists the concern — as `true`, `false`, or `"optional"` — is
    left exactly as it is, because every one of those is a decision the
    repository made about its own selection.
    """
    if not selections:
        return text
    lines = text.splitlines(keepends=True)
    present = {entry for entry, _value in block_entries(lines, "checks")}
    additions = [name for name in selections if name not in present]
    if not additions:
        return text
    block = top_level_block_bounds(lines, "checks")
    if block is None:
        # `read_manifest` refuses a manifest with no `checks:` block, so this
        # is unreachable from `bind_repo`. It is refused rather than guessed
        # at, because inventing the block would invent the whole selection.
        raise ValueError("manifest has no `checks:` block to add a selection to")
    _start, end = block
    for offset, name in enumerate(additions):
        lines.insert(end + offset, f"  {name}: true\n")
    return "".join(lines)


def render_manifest(text: str, bindings: list[tuple[str, str]]) -> str:
    """Insert `bindings` into the manifest's `commands:` block.

    `bindings` is `(concern, command)` in the order the manifest declares
    its `checks:`, so the result reads in the repository's own order. The
    generated comment is written once, guarded by its marker, so a partial
    binding does not accumulate a second copy.
    """
    if not bindings:
        return text
    lines = text.splitlines(keepends=True)
    block = top_level_block_bounds(lines, "commands")
    if block is None:
        body = [line for line in lines if line.strip()]
        trailing = len(lines) - len(body)
        out = list(lines[: len(lines) - trailing])
        if out and not out[-1].endswith("\n"):
            out[-1] += "\n"
        if out and out[-1].strip():
            out.append("\n")
        out.append("commands:\n")
        out.append(GENERATED_COMMENT)
        for concern, command in bindings:
            out.append(f"  {concern}: {yaml_scalar(command)}\n")
        out.extend(lines[len(lines) - trailing :])
        return "".join(out)

    _start, end = block
    has_comment = any(GENERATED_MARKER in line for line in lines[:end])
    insert_at = end
    if not has_comment:
        lines.insert(insert_at, GENERATED_COMMENT)
        insert_at += 1
    for offset, (concern, command) in enumerate(bindings):
        lines.insert(insert_at + offset, f"  {concern}: {yaml_scalar(command)}\n")
    return "".join(lines)


def classify_repo(repo_path: Path, selected: list[str], bound: dict[str, str],
                  shape: Shape, profile_only: frozenset[str] = frozenset(),
                  profile: str = "") -> list[ConcernOutcome]:
    """Decide each selected concern, without writing anything.

    `selected` is the gate's required set, which is a superset of the
    manifest's own `checks:` — see [`gate_required`]. `profile_only` names
    the ones only the profile scheduled.

    A profile-only concern is **derived first** rather than refused outright.
    The gate's manifest reader rejects a `commands:` entry for a check the
    manifest does not select, so the old answer was to refuse and record the
    gap. But a repository that names `profile: product` has already committed
    to the three concerns that profile schedules, and the gate already fails
    it for not binding them — so where a checker is genuinely reachable, the
    correct write is **both** a `checks:` entry and a `commands:` entry, and
    [`bind_repo`] performs them as one operation.

    Where no checker is reachable, the concern is recorded and neither entry
    is written. That is the case that matters for honesty: a `checks:` entry
    with no command behind it is a worse state than the gap, because it
    makes a declared check one the gate now fails on while still running
    nothing.
    """
    outcomes = []
    for concern in selected:
        if concern in profile_only:
            command, evidence, reason = derive(concern, shape, repo_path)
            if command:
                # Reachable: bound, and `bind_repo` writes the matching
                # `checks:` entry with it.
                outcomes.append(
                    ConcernOutcome(
                        repo_path.name,
                        concern,
                        BOUND,
                        command,
                        evidence,
                        selects=True,
                    )
                )
            else:
                outcomes.append(
                    ConcernOutcome(
                        repo_path.name,
                        concern,
                        UNRESOLVED,
                        reason=reason or profile_only_reason(concern, profile),
                    )
                )
            continue
        if concern in bound:
            command, evidence, _reason = derive(concern, shape, repo_path)
            if not command:
                # Bound, and by an authority other than this tool: the
                # `declared-verification` command the sibling generator
                # writes, or a check this tool has no rule for. The gate will
                # run it, so it is already bound and is left alone.
                outcomes.append(
                    ConcernOutcome(
                        repo_path.name,
                        concern,
                        ALREADY_BOUND,
                        unquote_scalar(bound[concern]),
                        "bound by another authority; this tool derives nothing for it",
                    )
                )
            elif unquote_scalar(bound[concern]) == command:
                outcomes.append(
                    ConcernOutcome(repo_path.name, concern, ALREADY_BOUND, command, evidence)
                )
            else:
                outcomes.append(
                    ConcernOutcome(
                        repo_path.name,
                        concern,
                        CONFLICT,
                        bound[concern],
                        evidence,
                        "an existing command differs from the derived one; left untouched",
                    )
                )
            continue
        command, evidence, reason = derive(concern, shape, repo_path)
        if command:
            outcomes.append(ConcernOutcome(repo_path.name, concern, BOUND, command, evidence))
        else:
            outcomes.append(ConcernOutcome(repo_path.name, concern, UNRESOLVED, reason=reason))
    return outcomes


def roll_up(concerns: list[ConcernOutcome], total_selected: int) -> str:
    outstanding = [c for c in concerns if c.status in NOT_RESOLVED]
    if not outstanding:
        return RESOLVED
    if len(outstanding) == total_selected:
        return UNRESOLVED
    return PARTIAL


# --- the debt record -------------------------------------------


def build_debt(report: Report, root: Path) -> dict:
    """Assemble the debt record.

    No timestamp: a `generated_at` field makes every run a diff and trains
    reviewers to ignore the file. Sorted everywhere, so re-running on an
    unchanged fleet is byte-identical and a change in it is a real change
    in the debt.
    """
    repositories = []
    by_reason: dict[str, list[str]] = {}
    for outcome in sorted(report.outcomes, key=lambda o: o.repo):
        gaps = [c for c in outcome.concerns if c.status in NOT_RESOLVED]
        if not gaps:
            continue
        repositories.append(
            {
                "repo": outcome.repo,
                "shape": outcome.shape,
                "unresolved": [
                    {"concern": c.concern, "status": c.status, "reason": c.reason or c.command}
                    for c in sorted(gaps, key=lambda c: c.concern)
                ],
            }
        )
        for gap in gaps:
            by_reason.setdefault(gap.reason or gap.command, []).append(f"{outcome.repo}:{gap.concern}")

    groups = [
        {
            "reason": reason,
            "checks": len(sorted(set(entries))),
            "repositories": sorted({e.split(":")[0] for e in entries}),
            "entries": sorted(set(entries)),
        }
        for reason, entries in sorted(by_reason.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    ]
    return {
        "generator": "scripts/bind_gate_commands.py",
        "note": (
            "Every check listed here is one the gate would report as UNBOUND: a "
            "check this repository's .ai-gate/gate.yaml selects under `checks:`, or "
            "one its `profile:` schedules by default, with no command bound under "
            "`commands:`. The gate reports UNBOUND for these and fails the project. "
            "A wrong command is worse than a listed gap: resolve these by hand, "
            "then re-run the generator."
        ),
        "totals": {
            "repositories_with_debt": len(repositories),
            "unresolved_checks": sum(g["checks"] for g in groups),
        },
        "by_reason": groups,
        "repositories": repositories,
    }


def write_debt_record(debt: dict, path: Path) -> None:
    path.write_text(json.dumps(debt, indent=2, sort_keys=False) + "\n", encoding="utf-8")


# --- the per-repository driver ---------------------------------


def bind_repo(repo_path: Path, apply: bool = False, check_clean: bool = True) -> Outcome:
    """Bind one repository's gate-required concerns. Never raises."""
    name = repo_path.name
    manifest = repo_path / GATE_YAML
    if not manifest.is_file():
        return Outcome(
            name, NO_MANIFEST, f"no {GATE_YAML}; nothing was written"
        )
    try:
        before = manifest.read_text(encoding="utf-8")
    except OSError as exc:
        return Outcome(name, REFUSED, f"cannot read {GATE_YAML}: {exc}")

    selected, bound, problem = read_manifest(before)
    if problem:
        return Outcome(name, REFUSED, problem)

    policy = read_gate_policy(before)
    required = gate_required(selected, policy)
    profile_only = frozenset(c for c in required if c not in set(selected))

    try:
        shape = detect_shape(repo_path)
    except Exception as exc:  # noqa: BLE001 - a bad repository must not stop the fleet
        return Outcome(name, REFUSED, f"could not inspect the repository: {exc}")

    try:
        concerns = classify_repo(
            repo_path,
            required,
            bound,
            shape,
            profile_only=profile_only,
            profile=policy.profile,
        )
    except Exception as exc:  # noqa: BLE001
        return Outcome(name, REFUSED, f"{GATE_YAML} could not be evaluated: {exc}")

    status = roll_up(concerns, len(required))
    label = f"{len(required)} required check(s)"

    # The dirty check refuses the *write*, not the reading. The gate
    # resolves a dirty repository exactly as it resolves a clean one and
    # fails on the same unbound checks, so leaving them out of the record
    # would hide real debt the moment somebody had work in progress — and
    # an `--apply` run immediately after a previous one would write a
    # record that silently under-reports.
    if check_clean and is_dirty(repo_path):
        return Outcome(
            name,
            DIRTY,
            f"{GATE_YAML} has uncommitted work; {label} classified and recorded, nothing written",
            before=before,
            after=before,
            concerns=concerns,
            shape=shape.label(),
        )

    pending = [c for c in concerns if c.status == BOUND]
    if not pending:
        return Outcome(
            name,
            status,
            f"{label}, all already bound or refused",
            before=before,
            after=before,
            concerns=concerns,
            shape=shape.label(),
        )

    try:
        after = render_manifest(before, [(c.concern, c.command) for c in pending])
        # The `checks:` entry goes in **after** the `commands:` entry and
        # before the single write, so the file on disk never carries a
        # selection with no command behind it at any point. Both land in
        # `after`, which is the only text this function writes.
        selects = [c.concern for c in pending if c.selects]
        if selects:
            after = render_checks(after, selects)
    except Exception as exc:  # noqa: BLE001
        return Outcome(
            name, REFUSED, f"{GATE_YAML} could not be updated: {exc}", concerns=concerns,
            shape=shape.label(),
        )

    if not apply:
        return Outcome(
            name,
            status,
            f"would bind {len(pending)} concern(s): {', '.join(c.concern for c in pending)}",
            before=before,
            after=after,
            concerns=concerns,
            shape=shape.label(),
        )
    try:
        manifest.write_text(after, encoding="utf-8")
    except OSError as exc:
        return Outcome(
            name, REFUSED, f"cannot write {GATE_YAML}: {exc}", concerns=concerns,
            shape=shape.label(),
        )
    return Outcome(
        name,
        status,
        f"bound {len(pending)} concern(s): {', '.join(c.concern for c in pending)}",
        wrote=True,
        before=before,
        after=after,
        concerns=concerns,
        shape=shape.label(),
    )


def run(
    root: Path,
    apply: bool = False,
    only: list[str] | None = None,
    check_clean: bool = True,
) -> Report:
    """Bind across the workspace. Never raises."""
    report = Report()
    for repo_path in discover_repos(root):
        if only and repo_path.name not in only:
            continue
        report.add(bind_repo(repo_path, apply=apply, check_clean=check_clean))
    return report


# --- output ----------------------------------------------------


def format_detail(outcome: Outcome, verbose: bool) -> str:
    """The per-repository line: what was bound, what was left, what is open."""
    parts = []
    if verbose:
        for concern in outcome.concerns:
            if concern.status == BOUND:
                parts.append(f"{concern.concern}={concern.command} <- {concern.evidence}")
            elif concern.status == ALREADY_BOUND:
                parts.append(f"{concern.concern}=already-bound")
            elif concern.status == CONFLICT:
                parts.append(f"{concern.concern}=CONFLICT")
            else:
                parts.append(f"{concern.concern}=UNRESOLVED: {concern.reason}")
    return " | ".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="workspace root holding the sibling repositories",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write the bindings and the debt record; without this the run is a dry run",
    )
    parser.add_argument(
        "--debt-out",
        type=Path,
        default=None,
        help=f"where to write the debt record (default: <root>/{DEBT_FILE})",
    )
    parser.add_argument(
        "--repo",
        action="append",
        dest="only",
        help="restrict the run to these repository names (repeatable)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="print the derived command and its on-disk evidence per concern",
    )
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if not root.is_dir():
        print(f"workspace root is not a directory: {root}", file=sys.stderr)
        return 2

    report = run(root, apply=args.apply, only=args.only)
    for outcome in report.outcomes:
        marker = "wrote" if outcome.wrote else outcome.status.lower()
        detail = format_detail(outcome, args.verbose)
        if not detail:
            detail = f" :: {outcome.detail}" if outcome.detail else ""
        print(f"{outcome.repo:32} {marker:12}{detail}")

    debt = build_debt(report, root)
    debt_path = args.debt_out or (root / DEBT_FILE)
    if args.apply:
        write_debt_record(debt, debt_path)

    unresolved = report.unresolved()
    conflicts = report.conflicts()
    print()
    print(f"mode:            {'APPLY' if args.apply else 'DRY RUN'}")
    print(f"repositories:    {len(report.outcomes)}")
    for status in (RESOLVED, PARTIAL, UNRESOLVED, NO_MANIFEST, DIRTY, REFUSED):
        names = report.names(status)
        print(f"{status + ':':18}{len(names):<5}{' '.join(names[:6])}{' ...' if len(names) > 6 else ''}")
    print(f"{'unresolved checks:':18}{len(unresolved)}  (declared, unbound, and underivable)")
    print(f"{'left in place:':18}{len(conflicts)}  (a person wrote a different command; not clobbered)")
    print(f"{'debt record:':18}{debt_path}{' (written)' if args.apply else ' (not written; dry run)'}")
    if unresolved:
        print()
        print("Unresolved concerns, by reason:")
        for group in debt["by_reason"]:
            print(f"  {group['checks']:>3}  {group['reason']}")
    return 3 if unresolved else 0


if __name__ == "__main__":
    raise SystemExit(main())
