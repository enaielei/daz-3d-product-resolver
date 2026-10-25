# Daz 3D Product Resolver

Offline Python 3.12+ tool to resolve static DUF/DSF dependencies and copy **whole products**
from extracted folders or ZIP packages into an explicitly selected content library.
Without scenes, it installs all supported indexed products. No purchased content is included.

## Development and use

Install [uv](https://docs.astral.sh/uv/), then `uv sync --locked --all-extras`.
Run `uv run daz-3d-product-resolver --help` or
`uv run daz-3d-product-resolver-desktop`.

```sh
uv run daz-3d-product-resolver discover
uv run daz-3d-product-resolver plan --source /packages --scene /scenes/example.duf --library /existing --destination /new-library --output plan.json
uv run daz-3d-product-resolver install plan.json
```

Plans are read-only JSON. Review selected products, missing references, ambiguity, conflicts,
and estimated bytes before installation. Repeat source, scene and library arguments as needed.
Use `--choose relative/path=PRODUCT_ID` for competing products and
`--conflict relative/path=keep` or `=replace` for existing differing files, then re-plan.
Use `--product-root` for explicit extracted boundaries reported as ambiguous.
`--detected` enables discovered sources/libraries; select `--profile` and `--studio` when
multiple settings exist. Discovery never chooses an active profile or installation destination.

Installation revalidates sources and destination expectations, backs up replacements,
journals writes separately from DIM, and verifies hashes. Identical reruns write no files.
`recover DESTINATION` rolls back interrupted transactions while retaining changed user files.
Keep source/destination trees idle during installation. See [limitations](docs/architecture.md).

## Validation and Windows build

```sh
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run pyinstaller packaging/windows.spec --noconfirm
```

The locked [PyInstaller](https://pyinstaller.org/en/stable/usage.html) build produces a
Windows folder application under `dist/`. Build on Windows; do not cross-compile.
CI exercises the portable engine on Windows, Linux and macOS and builds/smoke-tests Windows.
These checks do not establish acceptance with real libraries on every platform.

MIT licensed. Not affiliated with DAZ 3D. No account configuration writes, credentials,
telemetry, product downloads, source deletion, DIM registration or Smart Content import.
