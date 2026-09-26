# Package Backlog

Implementation-ready handoffs for the remaining packages of the workspace
maturity initiative. Each section is self-contained: a fresh conversation can
read one section, open the named repository, author its OpenSpec change from the
requirements below, implement, verify against the oracle, then archive and
commit.

Packages 3 and 8 are already authored as OpenSpec changes in this repository and
are **not** repeated here:

- `openspec/changes/portfolio-vocabulary-normalization/` — package 3.
- `openspec/changes/governance-front-door/` — package 8.

Shipped packages: 1 `registry-and-declaration-integrity`, 2
`shared-rules-single-source` (both archived under `openspec/changes/archive/`).

Remaining here: 4 `gate-run-evidence`, 5 `platform-adoption-dotnet`,
6 `platform-adoption-rust`, 7 `contracts-single-source`.

Cross-repo packages (4–7) change a different repository from the one this file
lives in. Author the change in the **owning** repository listed for the package,
following that repository's own OpenSpec process, and reference this file for
context. Do not implement a cross-repo package from inside `workspace-governance`.

---

## Package 4 — `gate-run-evidence`

**Outcome.** Real gate runs are produced and recorded as evidence that populates
`release_evidence`, so a `deployable` claim rests on an executed gate rather than
a hand-written state.

**Owner.** `driftwatchdog` (Rust, the gate executor). Governance-side vocabulary
already exists in `workspace-governance` (`docs/capabilities.md`, the
`release_evidence` block of `.project.json`).

**Current evidence.**
- 73 `.ai-gate/gate.yaml` declarations exist, all `runtime: driftwatchdog`; only
  `driftwatchdog`'s own CI invokes the gate. `workspace-governance/.ai-gate/gate.yaml`
  notes "Driftwatchdog Gate bindings are not yet active for this bootstrap".
- The 7 deployable pilots carry `release_evidence` fields in state `configured`
  pointing at pilot-context placeholders (`docs/adoption-queue.md`).
- No SBOM or provenance artefact exists anywhere in the portfolio.

**Boundary.** driftwatchdog gains a gate-run record type and a
`--emit-evidence` path; workspace-governance consumes the record to set
`release_evidence` state `verified`. Do not re-implement evidence vocabulary in
Rust — consume `docs/capabilities.md`'s field and state names.

**Dependencies.** Packages 1, 2, 3 (shipped/authored).

**Spec requirements (author as `gate-run-evidence` in driftwatchdog).**
- R1 A gate run against a project emits a record naming project, revision,
  toolchain, checks, and per-check outcome.
- R2 The record is schema-valid against the governance `release_evidence` field
  names and states.
- R3 Consuming the record sets `release_evidence.<field>` to `verified` only for
  checks that actually ran and passed; missing checks stay `unverified`.
- R4 A record whose revision differs from the project's `HEAD` MUST NOT verify
  anything (it is stale).
- R5 A gate run that cannot execute a check MUST record `blocked`/`unverified`,
  never a pass.

**Failure policy.** Unreadable declaration → no run; check exit code alone is not
evidence (record stdout digest); partial runs never verify the unrun checks.

**Verification oracle.** A gate run over a synthetic project emits a record the
governance audit accepts; the audit's `release_evidence` state changes only for
executed checks; a stale-revision record is rejected. driftwatchdog's own suite
plus `workspace_check.py --root .. --audit` stay green.

**Start a new conversation with.** "In `/home/paul/code/driftwatchdog`, author and
implement the `gate-run-evidence` OpenSpec change per
`/home/paul/code/workspace-governance/docs/package-backlog.md`."

---

## Package 5 — `platform-adoption-dotnet`

**Outcome.** `dotnet-platform-libs` is consumable through one documented path,
with a working source/package switch and real publish.

**Owner.** `dotnet-platform-libs` (C#/.NET).

**Current evidence.**
- `build/Platform.Consumer.props` injects only a `ProjectReference` to
  `Platform.Core`, and only when `TargetFramework == net10.0`.
- `PlatformAsSource` is computed in the workspace `Directory.Build.props` and
  described as the source/package switch, but `Platform.Consumer.props` never
  reads it — it is dead configuration.
- Workspace root default TFM is `net8.0`; the platform is `net10.0`-only, so
  default-TFM consumers silently get nothing. `mewo` (a consumer) targets
  `net8.0`.
- Consumer defaults (Nullable, analyzers, warnings-as-errors, central package
  management) are not propagated; each consumer re-derives them.
- No `dotnet nuget push` exists anywhere: the GitHub Packages feed is declared in
  the workspace `nuget.config` but never published to.
- 7 repos adopt via `PackageReference` with four different feed paths and
  hand-written pack scripts; 7 more are documented as "starting points".

**Boundary.** `build/Platform.Consumer.props` (+ a `.targets` if needed), the
platform's `Directory.Build.props`/`Directory.Packages.props`, `global.json`, and
a release workflow that pushes. Do not edit consumer repositories in this change.

**Dependencies.** None (parallel with 6, 7).

**Spec requirements (author as `platform-adoption-dotnet` in dotnet-platform-libs).**
- R1 One documented consumption path; `PlatformAsSource` is honoured (source →
  `ProjectReference`, package → `PackageReference`).
- R2 Consumer defaults (Nullable, `LangVersion`, analyzers, warnings policy) are
  propagated to `net10.0` consumers, with an explicit opt-out.
- R3 The TFM contract is explicit: a consumer on an unsupported TFM fails with a
  named diagnostic rather than silently receiving nothing.
- R4 One version source (no hard-coded `0.1.0` across consumers) and one publish
  path that actually pushes to the declared feed.
- R5 A conformance fixture proves a fresh consumer restores, builds, and tests
  from the published feed.

**Failure policy.** Missing checkout with `PlatformAsSource=true` → explicit
restore error; unsupported TFM → explicit diagnostic; publish without
credentials → fail loudly, never silently skip.

**Verification oracle.** `scripts/conformance.sh` restores/builds/tests a
consumer from the feed; a consumer on `net8.0` gets the named diagnostic; the
release workflow pushes a versioned package.

**Start a new conversation with.** "In `/home/paul/code/dotnet-platform-libs`,
author and implement the `platform-adoption-dotnet` OpenSpec change per
`/home/paul/code/workspace-governance/docs/package-backlog.md`."

---

## Package 6 — `platform-adoption-rust`

**Outcome.** `rust-platform-libs` has the baseline, consumer recipe and
conformance harness the .NET platform already has, so its crates are adoptable.

**Owner.** `rust-platform-libs` (Rust).

**Current evidence.**
- 20 repositories contain a `Cargo.toml`; **one** (`trailCrew`) consumes a
  platform crate, by a hand-written `path = "../rust-platform-libs/crates/..."`.
- No shared `rustfmt.toml`, `clippy.toml`, `deny.toml` or `.cargo/config.toml`
  exists at the workspace root; the three that exist disagree (three rustfmt
  styles; two clippy profiles).
- No MSRV policy: `rust-version` ranges 1.74–1.85, and four repos declare none.
- Editions are mixed (2021 vs 2024) even among shared repos.
- `rust-platform-libs` CI runs only `cargo test --workspace` — no fmt, clippy or
  deny gate; `publish = false`; no consumer bootstrap, no conformance script.
- The only cross-repo contract mechanism is
  `crates/platform-contracts/tests/fixture_parity.rs`, covering 4 of 9 families.

**Boundary.** `rust-platform-libs` workspace metadata, lints, toolchain pin, a
consumer recipe doc, a conformance script, and its CI. Do not edit consumer
repositories in this change.

**Dependencies.** None (parallel with 5, 7); package 7 extends the parity walk.

**Spec requirements (author as `platform-adoption-rust` in rust-platform-libs).**
- R1 A committed shared baseline (`rustfmt.toml`, `clippy.toml`, `[workspace.lints]`)
  that consumers can adopt verbatim.
- R2 A declared MSRV policy, pinned by `rust-toolchain.toml`, enforced in CI.
- R3 A documented consumer recipe (path dependency or versioned git dependency)
  replacing hand-written paths.
- R4 CI runs fmt, clippy `-D warnings`, `cargo deny`, and tests.
- R5 A conformance harness packs and consumes a real consumer crate, mirroring
  the .NET `conformance.sh`.

**Failure policy.** Missing toolchain → CI fails with the pinned version; lint
drift → CI fails; unpublished/pinned consumer cannot resolve → conformance fails.

**Verification oracle.** The conformance harness builds and tests a consumer;
`cargo fmt --check`, `cargo clippy -D warnings`, `cargo deny check` and
`cargo test --workspace` all pass in CI.

**Start a new conversation with.** "In `/home/paul/code/rust-platform-libs`,
author and implement the `platform-adoption-rust` OpenSpec change per
`/home/paul/code/workspace-governance/docs/package-backlog.md`."

---

## Package 7 — `contracts-single-source`

**Outcome.** `platform-contracts` is the single contract source, consumed by both
platforms across all 9 families, with no hand-copied fixtures.

**Owner.** `platform-contracts` (language-neutral JSON Schema + Python tooling),
with consumption changes in `rust-platform-libs` and `dotnet-platform-libs`.

**Current evidence.**
- 12 schemas, 9 registered families, 108 canonical fixtures, a validator and 32
  tests exist.
- Only `rust-platform-libs/crates/platform-contracts/tests/fixture_parity.rs`
  consumes the repository, and only for **4 of 9** families (`identity-subject`,
  `permission-decision`, `tenant-context`, `audit-event`); the remaining 5 are a
  pending ROADMAP item.
- `dotnet-platform-libs/tests/Platform.ConsumerConformance/Fixtures/contracts/`
  **hand-copies** 12 fixtures instead of consuming the source.
- Nothing clones `platform-contracts` in CI; the Rust walker relies on a local
  `PLATFORM_CONTRACTS_DIR`/`../platform-contracts` checkout.
- The secret-field vocabulary is declared here *and* re-derived in
  `rust-platform-libs` and in governance (see package 3).

**Boundary.** `platform-contracts` (schemas/fixtures/tools/docs) plus the
consumption sites in the two platform repos. Split the consumption work into its
own change in each consumer repo if the repositories cannot be coordinated.

**Dependencies.** Packages 5, 6; reconcile the secret list with package 3's
`vocabulary.json`.

**Spec requirements (author as `contracts-single-source` in platform-contracts).**
- R1 All 9 registered families are exercised by a parity walk in each consuming
  language.
- R2 Consumers reference the schema source; no fixture is hand-copied.
- R3 CI clones or vendors the pinned contract revision so the walk runs without a
  developer-local checkout.
- R4 A contract change that breaks a consumer fails that consumer's build.
- R5 The secret-field vocabulary has one authoritative list, consumed rather than
  re-derived.

**Failure policy.** Missing contract source in CI → fail, never skip the walk;
unknown family → fail; version mismatch → fail with both versions named.

**Verification oracle.** Fixture parity reports 9/9 families in both languages;
the .NET conformance fixtures are gone (consumed instead); a deliberately broken
schema fails both consumers.

**Start a new conversation with.** "In `/home/paul/code/platform-contracts`,
author and implement the `contracts-single-source` OpenSpec change per
`/home/paul/code/workspace-governance/docs/package-backlog.md`."

---

## Coordination rules for every package

- One repository per change; author it where it is owned, per that repository's
  AGENTS/OpenSpec process, with the repository's own two-commit discipline.
- Consume the shipped governance vocabulary; never re-declare a field name, a
  state name, a kind or a profile locally.
- If a package reveals a second lifecycle, owner or acceptance oracle, stop and
  propose a follow-up package with a dependency edge rather than expanding scope.
- The `workspace-governance` audit is the portfolio oracle: after any package,
  `python3 scripts/workspace_check.py --root .. --audit --json` must stay at
  0 errors.
