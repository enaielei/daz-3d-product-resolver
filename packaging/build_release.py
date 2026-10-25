"""Package an already-built Windows app as portable ZIP and per-user installer."""

import argparse
import hashlib
import shutil
import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iscc", type=Path, required=True)
    args = parser.parse_args()
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
    app = ROOT / "dist/Daz3DProductResolver"
    output = ROOT / "dist/release"
    output.mkdir(exist_ok=True)
    subprocess.run(
        [
            str(args.iscc.resolve()),
            f"/DAppVersion={version}",
            f"/DBuildRoot={app}",
            f"/DOutputRoot={output}",
            str(ROOT / "packaging/installer.iss"),
        ],
        check=True,
        cwd=ROOT,
    )
    name = f"Daz3DProductResolver-{version}-windows-x64-portable"
    archive = Path(shutil.make_archive(str(output / name), "zip", app.parent, app.name))
    installer = output / f"Daz3DProductResolver-{version}-windows-x64-setup.exe"
    lines = []
    for path in (installer, archive):
        with path.open("rb") as stream:
            checksum = hashlib.file_digest(stream, "sha256").hexdigest()
        lines.append(f"{checksum}  {path.name}")
    (output / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
