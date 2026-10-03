# Project Agent Instructions

- Read `HANDOFF.md` before work.
- Use OpenSpec for non-trivial changes.
- Use BFS → DFS → BFS for impact, implementation, and regression review.
- Run the declared verification command before completion.
- Build/test/skeleton success is not runtime or release evidence.
- Assess shared infrastructure before duplication; see `docs/adoption-grant.md` and `docs/capabilities.md` in the governance repository. Assess a named sibling or a published package for an existing capability before writing a local implementation, and name the specific sibling, project id, or package you assessed — an un-named assessment is not an assessment.
- Do not edit a sibling repository without scope authorization. This restriction governs *source* changes to another repository. It does not govern *consuming* a sibling's published artifact: a pinned, checksum-verified package coordinate, its registration in this repository's own composition root, and this repository's own tests are consumer-side changes. Under a valid `adoption_grant` in this repository's `.project.json`, replacing a local implementation with a registered shared provider is authorized without separate cross-repo approval, and must be recorded in this repository's `capabilities[].consumes[]` and in `adoption/adoptions.json`. A source-level coupling — a `ProjectReference`, a relative path, or a `../` dependency on a sibling checkout — remains forbidden regardless of any grant, as does bumping a provider's version.
- Keep the capability local when ownership, privacy, lifecycle, or dependency direction makes that the correct boundary. Record that decision as a `declines[]` entry in `.project.json` with a rationale from the closed vocabulary and an evidence reference that resolves in this repository; prose in a document is not a decline.
- Each completed OpenSpec spec/change requires exactly two commits: first the implementation/tests/archive commit, then a HANDOFF.md-only pointer/evidence commit.

Detailed rules: `.ai-rules/workflow.md` and `.ai-rules/completion.md`.
