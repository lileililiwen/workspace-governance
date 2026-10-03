# Workspace Governance Agent Instructions

- Read `README.md`, `HANDOFF.md`, and the selected OpenSpec change before work.
- Use OpenSpec for non-trivial governance changes.
- Use BFS → DFS → BFS: map portfolio impact, implement one coherent contract, then re-audit all consumers.
- Run `python3 scripts/workspace_check.py --self-check` before completion.
- Run `python3 scripts/jenkins_manifest.py --check` for deployment-related changes.
- Existing projects keep declarations and exceptions; shared runtimes remain centralized.

## Classification

- `role` and `stack` are independent axes. `role` is what a repository is for; `stack` is what it is written in. Never write one into the other's field — a stack-shaped value in `role` is the defect this split exists to remove.
- `kind` is derived, never authored: `kind = stack + "-" + role`, or the bare `role` when `stack` is `none`.
- A repository `id` is immutable once any artifact references it, and is never renamed or normalized to match its directory. A directory whose name is not a valid identifier records an explicit `alias`; the eight `campusMesh`-style entries are already correct and must not be churned.

## Claims and evidence

- A README claim is a factual assertion and is checked against the file tree. Do not write a claim you cannot evidence, and do not name a subject outside the surface vocabulary — state what is true instead. Silence is honest; an unverifiable claim is not.
- Build/test success is not runtime or release evidence.
- A checker that reports OK without performing a comparison is worse than no checker, because it retires the question while answering nothing. A verifier that no gate runs does not gate: wire every check into the gate that blocks, or it is documentation.
- A check that can be switched off is not a check. Do not add an opt-in, an exemption registry, or an environment-variable escape to a check that is meant to hold.

## Shared infrastructure

- Assess shared infrastructure before duplication; name the specific sibling, project id, or package you assessed — an un-named assessment is not an assessment. Under a valid `adoption_grant`, a consumer may repoint onto a registered provider without cross-repo approval; see `docs/adoption-grant.md`.
- A shared package must not impose a version floor on consumers for a dependency only some of them need. Where consumers legitimately diverge on a dependency version, ship source or a template — not a compiled package that silently unifies them.
- Never place a data-access or ORM dependency in a testing package. A testing package exists to be consumed, and an ORM reference drags provider conflicts onto every consumer.
- A checker must not depend on an environment variable being set. A CI runner that lacks it fails exactly as a hard-coded path fails. Prefer a committed, repo-relative input.

## Cross-repo boundary

- Do not edit a sibling repository without scope authorization. Source edits are still gated; consuming a pinned published artifact is not. A `ProjectReference`, relative path, `../` sibling dependency, provider version bump, and promotion to `deployable: true` remain forbidden regardless of any grant.
- A copy of a contract shape is a finding wherever it sits, including in a repository that holds no record of it. Record an exemption by exact path, never by category — a category exemption is how a vendored copy becomes a permanent unexamined shadow.
- When a cross-repo repair is authorized, do it as one separately reviewable commit per repository, ordered by blast radius descending.

## Commit protocol

- Keep exactly one `current_spec` line in `HANDOFF.md` while work is active.
- Each completed OpenSpec spec/change requires exactly two commits: first the implementation/tests/archive commit, then a HANDOFF.md-only pointer/evidence commit.
- Stop after the second commit.

Detailed rules: `.ai-rules/workflow.md` and `.ai-rules/completion.md`.
