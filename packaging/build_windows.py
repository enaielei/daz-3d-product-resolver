"""Build the locked folder application and include dependency license texts."""

import importlib.metadata
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    if sys.platform != "win32":
        raise SystemExit("Build this Windows artifact on Windows")
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "packaging/windows.spec", "--noconfirm"],
        cwd=ROOT,
        check=True,
    )
    output = ROOT / "dist/Daz3DProductResolver"
    shutil.copytree(ROOT / "packaging/licenses", output / "licenses/Qt", dirs_exist_ok=True)
    for name in ("LICENSE", "README.md", "THIRD_PARTY_NOTICES.md", "uv.lock"):
        shutil.copyfile(ROOT / name, output / name)
    for name in (
        "PySide6",
        "PySide6_Essentials",
        "PySide6_Addons",
        "shiboken6",
        "typer",
        "rich",
        "markdown-it-py",
        "mdurl",
        "pygments",
        "defusedxml",
        "annotated-doc",
        "shellingham",
        "typing-extensions",
        "colorama",
        "pyinstaller",
    ):
        distribution = importlib.metadata.distribution(name)
        for item in distribution.files or []:
            if "license" in str(item).casefold() or "copying" in item.name.casefold():
                source = Path(distribution.locate_file(item))
                if source.is_file():
                    # Preserve license subdirectories without copying installed runtime code.
                    relative = Path(*item.parts[1:])
                    destination = output / "licenses" / name / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, destination)
    for name in ("LICENSE", "LICENSE.txt"):
        source = Path(sys.base_prefix) / name
        if source.is_file():
            destination = output / "licenses/CPython" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)


if __name__ == "__main__":
    main()
