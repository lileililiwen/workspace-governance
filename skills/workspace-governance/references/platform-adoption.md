# Shared library adoption (.NET / Rust)

Adoption lives in the owning repositories; this reference only routes there.

## Read first

- `docs/package-backlog.md` — the package index. It names the owning
  repository and the OpenSpec change for each adoption package, including the
  dotnet-platform-libs consumer bootstrap, the rust-platform-libs consumer
  baseline, and the platform-contracts consumer parity follow-up.
- `scripts/init_project.py` — adopts a project with `--profile` and `--kind`
  without copying shared gate runtimes, installers, caches, or credentials.

## Rules of the road

- One repository per change; never implement a cross-repo package from
  another repository.
- Consume the governance vocabulary from `vocabulary.json`; never re-declare
  it in an adopting project.
- Shared runtimes stay centralized; product repositories keep only their
  declarations and exceptions.
