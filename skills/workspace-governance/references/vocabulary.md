# Kind, profile, marker, and secret vocabulary

## Read first

- `vocabulary.json` — the single machine-readable source for the canonical
  profiles, kinds, `placeholder_markers`, and `secret_field_substrings`.
- `openspec/specs/portfolio-vocabulary/spec.md` — the canonical contract. It
  owns the sets and the enforcement codes (`PROFILE_UNKNOWN`,
  `KIND_UNKNOWN`, `PROFILE_DOC_UNKNOWN`); this reference does not repeat them.
- `profiles/product.json` — one profile document as an example; the
  `profiles/` directory holds one document per canonical profile.

## Run

- `scripts/workspace_check.py` loads the canonical sets and the secret scan
  from `vocabulary.json` instead of a local list.
- `scripts/product_code_quality.py` defaults its placeholder markers from
  `vocabulary.json`; a per-project `placeholder_markers` override still wins.
- `scripts/vocabulary.py` is the shared loader. A missing, unparseable,
  duplicate-bearing, or empty-list vocabulary makes each consumer exit
  non-zero; there is no empty-list fallback.

## Rules of the road

- Consume the governance vocabulary; never re-declare a field name, a state,
  a `kind`, or a `profile` locally.
- Kind is descriptive and never drives requirements; only `profile` does.
- The secret list only ever grows; dropping a term silently weakens the audit
  and is forbidden.
