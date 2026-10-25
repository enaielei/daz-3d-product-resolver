# Project instructions

Keep the engine portable and independent of Qt. Both interfaces use the same plan and installer.
Use synthetic fixtures only; real source/library/game paths are read-only and never committed.
Never execute product scripts or write DAZ/DIM settings. Installation requires an explicit library.
Reject unsafe paths and stale plans before writes. Preserve sources and back up replacements.
Run `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pytest`.
Use Conventional Commits on `codex/` branches; preserve the human author and append
`Co-authored-by: Codex <noreply@openai.com>` for materially assisted commits.
Do not merge without human authorization. Keep limitations honest in documentation.
