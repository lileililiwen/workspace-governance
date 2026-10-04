## ADDED Requirements

### Requirement: The real shape is detected from disk

A repository's project shape MUST be determined by reading its files, and
MUST NOT be read from the `stack` label in `.project.json`, because that
label disagrees with the disk for a large minority of the fleet. The
declared `stack` MUST NOT be passed into detection at all. Detection MUST
recognise, at any depth, a `*.sln` or `*.slnx` solution, a `*.csproj`
tree, a `Cargo.toml` together with whether it declares `[workspace]`, a
`package.json` together with which of its `scripts` keys exist, Python
test configuration, and a `pubspec.yaml`. A directory walk MUST NOT enter
`.git`, `node_modules`, `target`, `bin`, `obj`, `.venv`, `venv`, `dist`,
`build`, `.next`, `site-packages`, `.dart_tool` or the language caches, so
that a vendored file cannot be mistaken for the repository's own evidence.

`.slnx` MUST be treated as a solution on the same footing as `.sln`,
because repositories that use it pin an SDK that reads it natively and a
`*.sln`-only search finds no solution in them at all.

#### Scenario: The label is wrong and the files are not

- **WHEN** a repository declares `stack: typescript` and carries a
  solution file at its root alongside a nested `package.json`
- **THEN** the solution is the detected shape and no command is derived
  from the declared label

#### Scenario: A solution in the new file format

- **WHEN** a repository carries `LoreMix.slnx` and no `*.sln`
- **THEN** `LoreMix.slnx` is detected as the solution, and a command
  derived from it names `LoreMix.slnx`

#### Scenario: A vendored file is not evidence

- **WHEN** the only `conftest.py` in a repository is under
  `.venv/…/site-packages/`
- **THEN** it is not read, and it does not make the repository a pytest
  project

### Requirement: A command is derived per concern from the detected shape

For each concern a repository's manifest already selects, a command MUST
be derived from the detected shape and the files present, and never from
a default. A `.sln` or `.slnx` solution MUST yield `dotnet build <entry>`
and `dotnet test <entry>`; a `[workspace]` `Cargo.toml` MUST yield
`cargo build --workspace` and `cargo test --workspace`; a `Cargo.toml`
without `[workspace]` MUST yield `cargo build` and `cargo test`; a
`package.json` MUST yield `npm run build` and `npm test` **only** when
the `build` and `test` script keys respectively exist; a Python
repository with pytest configuration MUST yield `pytest`. A manifest
nested below the repository root MUST be reachable, and the derived
command MUST carry the working directory that reaches it. A `.sln` entry
point MUST be the solution when one exists, and otherwise exactly one
`.csproj`; a repository with several `.csproj` files and no solution MUST
NOT have one chosen for it.

#### Scenario: The workspace flag follows the manifest

- **WHEN** a repository's `Cargo.toml` declares `[workspace]`
- **THEN** the derived `build` command is `cargo build --workspace` and
  the derived `tests` command is `cargo test --workspace`

#### Scenario: No workspace flag means no flag

- **WHEN** a repository's `Cargo.toml` declares no `[workspace]`
- **THEN** the derived `build` command is `cargo build`, not
  `cargo build --workspace`

#### Scenario: The exact script key is used

- **WHEN** a repository's `package.json` declares `scripts.test`
- **THEN** the derived `tests` command is `npm test`, and the command
  names the script key that exists on disk

#### Scenario: A nested manifest carries its directory

- **WHEN** the only `Cargo.toml` is at `rust/Cargo.toml`
- **THEN** the derived `tests` command begins `cd rust &&` and names the
  nested manifest

### Requirement: An unknown shape is refused, never guessed

When no command can be derived for a concern, the concern MUST be
recorded as `unresolved` with the reason and the evidence, and no command
MUST be written. This applies to an unrecognised shape, a `package.json`
that lacks the required script key, an undetectable test runner, a
`package.json` without a `build` script where a build was asked for, a
pure-Python repository where a `build` was asked for, and a Flutter
repository where a target platform would have to be invented. A wrong
command MUST be treated as worse than an honest gap. The tool MUST NOT
read a repository's `notes:` prose or any other free text to recover a
command.

#### Scenario: The script key does not exist

- **WHEN** a repository's `package.json` has no `test` key and the
  manifest selects `tests`
- **THEN** `tests` is `unresolved` with the reason naming the missing
  `scripts.test` key, and no `commands.tests` entry is written

#### Scenario: A pure-Python repository has no build step

- **WHEN** a Python repository's manifest selects `build`
- **THEN** `build` is `unresolved` with the reason stating that a
  pure-Python package has no build step, and no command is written

#### Scenario: A test runner cannot be determined

- **WHEN** a repository has test files but none that `pytest` or
  `unittest` can be shown to collect
- **THEN** `tests` is `unresolved` with the reason naming what was
  looked for

### Requirement: Two equally plausible entry points stay unresolved

Where a repository contains more than one entry point that can answer the
same concern, the concern MUST be `unresolved` and the reason MUST name
every candidate, unless exactly one candidate is at the repository root.
Candidates that cannot answer the concern MUST be excluded before the
root-versus-nested comparison is made. There MUST be no tiebreaker and no
preference for one toolchain over another, because a tie means the
repository genuinely has two answers and choosing one would assert a shape
it does not have.

#### Scenario: A root entry point wins over a nested one

- **WHEN** a repository has a solution at its root and a `package.json`
  with a `test` script in a subdirectory
- **THEN** the solution provides the `tests` command and the nested
  manifest is not consulted

#### Scenario: Two nested candidates are a refusal

- **WHEN** a repository has a solution in one subdirectory and a
  `package.json` with a `test` script in another, and neither is at the
  root
- **THEN** `tests` is `unresolved` and the reason names both candidates

#### Scenario: Two root candidates are a refusal

- **WHEN** a repository has both a solution and a `package.json` with a
  `test` script at its root
- **THEN** `tests` is `unresolved` and the reason names both

#### Scenario: A candidate that cannot answer is not a candidate

- **WHEN** a repository's root `package.json` has no `test` script and a
  nested Rust workspace does
- **THEN** the nested workspace provides the `tests` command, and no
  ambiguity is reported

### Requirement: Only a concern the repository declared is bound

A command MUST be written only for a concern the repository's own
manifest already selected under `checks:`. The tool MUST NOT add a
concern, MUST NOT remove a concern, MUST NOT change a `checks:` value,
and MUST NOT turn a disabled concern on. A concern that is disabled or
absent from `checks:` MUST be left alone whether or not a command could
be derived for it. A command already present for a declared concern MUST
be left byte-for-byte alone when it equals the derived command, and MUST
be reported as a conflict and left untouched when it differs, because an
existing binding is a decision somebody made by hand.

#### Scenario: A concern nobody asked for stays unbound

- **WHEN** a repository's manifest does not select `format` and its
  `Cargo.toml` would allow a `format` command to be derived
- **THEN** no `commands.format` entry is written

#### Scenario: A disabled concern stays disabled

- **WHEN** a repository's manifest records `build: false`
- **THEN** no `build` command is written and the `false` is not changed

#### Scenario: A hand-made binding is not overwritten

- **WHEN** a repository's `commands.tests` differs from the derived
  `tests` command
- **THEN** the concern is reported as a conflict, the existing command is
  left exactly as it is, and the file is not written

### Requirement: A run is dry by default and refuses a dirty manifest

The tool MUST NOT write any file without `--apply`, and a run without it
MUST report what it would do and change nothing on disk. A repository
whose `.ai-gate/gate.yaml` has uncommitted work MUST be skipped rather
than written into, including when that manifest is untracked, and an
unreadable or unparseable manifest MUST be refused by name rather than
rewritten. A run MUST continue past a refused repository to the next one.

#### Scenario: Dry run changes nothing

- **WHEN** the tool runs without `--apply`
- **THEN** every repository's manifest is byte-identical afterwards, and
  the report names what would be bound

#### Scenario: A dirty manifest is skipped

- **WHEN** a repository's `gate.yaml` is modified but uncommitted
- **THEN** that repository is reported as dirty and its manifest is not
  written

### Requirement: Every unresolved check leaves a durable debt record

For every repository that still cannot be fully wired, the tool MUST
leave a machine-readable record naming every unresolved concern and the
reason for each, so that the gap survives the run and cannot be inherited
silently. The record MUST be a committed JSON data file at the governance
root, and MUST hold per-repository entries with the concern id and its
reason, a grouping of the same reasons with the repositories they affect,
and totals. The record MUST NOT carry a timestamp, and every list MUST be
sorted, so that re-running the tool on an unchanged fleet produces a
byte-identical file and a change in the file is a real change in the
debt. The record MUST be written only under `--apply`, and a person
opening it MUST be able to see the grouped reasons before the repository
names.

#### Scenario: The debt names every gap

- **WHEN** a repository has three concerns the tool cannot resolve
- **THEN** the record contains one entry for that repository with all
  three concern ids and their reasons

#### Scenario: The record is stable

- **WHEN** the tool is run twice with `--apply` on an unchanged fleet
- **THEN** the second run's record is byte-identical to the first

#### Scenario: A human sees the cause first

- **WHEN** the record is read
- **THEN** the grouped reasons and their check counts appear before the
  per-repository entries

### Requirement: The run reports per repository and refuses to exit clean on debt

The tool MUST report, for every repository, which concerns it bound, which
it left alone, and which are unresolved with the reason, and MUST roll
those up into a per-repository status of fully resolved, partially
resolved, or fully unresolved. A summary MUST make an unresolved
repository obvious. The tool MUST exit non-zero when any unresolved
concern or conflict remains, MUST NOT offer a flag that suppresses that
exit code, and MUST return a distinct code for an unusable workspace root.
A tool that reports a gap and then exits successfully discards the
finding, which is the defect ruling D18 exists to prevent.

#### Scenario: Debt cannot be ignored

- **WHEN** a run completes with at least one unresolved concern
- **THEN** the tool exits with the debt exit code and prints the number
  of repositories carrying debt

#### Scenario: A clean fleet exits zero

- **WHEN** a run completes with every declared check bound
- **THEN** the tool exits 0

#### Scenario: The roll-up is what a reader sees first

- **WHEN** a run covers a mix of fully resolved, partially resolved and
  fully unresolved repositories
- **THEN** the summary reports all three counts
