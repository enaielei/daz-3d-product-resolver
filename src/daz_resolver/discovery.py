"""Read-only adapters for DIM INI profiles and Windows Studio registry settings."""

import configparser
import os
import sys
from pathlib import Path


def dim_profile(path: Path, shared: Path) -> dict:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(path, encoding="utf-8-sig")
    general = parser["General"] if parser.has_section("General") else {}

    def setting(key, default=None):
        value = general.get(key, "").strip()
        return {
            "path": value or (str(default) if default else None),
            "provenance": "detected" if value else "inferred-default",
        }

    paths = []
    section = parser["InstallPaths"] if parser.has_section("InstallPaths") else {}
    count = min(int(section.get("size", "0")), 1000)
    for i in range(1, count + 1):
        value = section.get(f"{i}\\InstallPath", "")
        if value:
            paths.append(
                {
                    "path": value,
                    "title": section.get(f"{i}\\InstallPathTitle", ""),
                    "provenance": "detected",
                }
            )
    return {
        "profile": str(path),
        "archive": setting("DownloadPath"),
        "current_install": setting("CurInstallPath"),
        "install_paths": paths,
        "manifest": setting("OverrideManifestDir", shared / "ManifestFiles"),
        "thumbnail": setting("OverrideThumbnailDir", shared / "Thumbnails"),
    }


def studio_settings(reader=None) -> list[dict]:
    if reader is None:
        if sys.platform != "win32":
            return []
        import winreg

        def reader(key, name):
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as handle:
                return winreg.QueryValueEx(handle, name)[0]

    settings = []
    for version in ("Studio6", "Studio4"):
        key = f"Software\\DAZ\\{version}"
        item = {"id": version, "provenance": "detected", "content": [], "poser": []}
        found = False
        for field, count_name, prefix in (
            ("content", "NumContentDirs", "ContentDir"),
            ("poser", "NumPoserDirs", "PoserDir"),
        ):
            try:
                count = min(int(reader(key, count_name)), 1000)
                found = True
            except (OSError, ValueError, TypeError):
                count = 0
            for i in range(count):
                try:
                    item[field].append(str(reader(key, f"{prefix}{i}")))
                except OSError:
                    pass
        try:
            item["cloud"] = str(reader(key, "CloudDir"))
            found = True
        except OSError:
            item["cloud"] = None
        if found:
            settings.append(item)
    return settings


def discover(appdata: Path | None = None, public: Path | None = None) -> dict:
    appdata = appdata or Path(os.environ.get("APPDATA", ""))
    public = public or Path(os.environ.get("PUBLIC", "")) / "Documents"
    profiles, reports = [], []
    accounts = appdata / "DAZ 3D/InstallManager/UserAccounts"
    for path in sorted(accounts.glob("*.ini")):
        try:
            profiles.append(dim_profile(path, public / "DAZ 3D/InstallManager"))
        except (OSError, ValueError, configparser.Error) as exc:
            reports.append(f"{path}: {exc}")
    settings = studio_settings()
    return {
        "dim_profiles": profiles,
        "studio_settings": settings,
        "reports": reports,
        "selection_required": len(profiles) > 1 or len(settings) > 1,
    }


def selected_paths(discovery: dict, profile: str | None, studio: str | None):
    profiles, settings = discovery["dim_profiles"], discovery["studio_settings"]
    if len(profiles) > 1 and not profile:
        raise ValueError("Multiple DIM profiles: select --profile explicitly")
    if len(settings) > 1 and not studio:
        raise ValueError("Multiple Studio settings: select --studio explicitly")
    selected = (
        next((p for p in profiles if p["profile"] == profile), None)
        if profile
        else (profiles[0] if profiles else None)
    )
    mapped = (
        next((s for s in settings if s["id"] == studio), None)
        if studio
        else (settings[0] if settings else None)
    )
    if profile and not selected or studio and not mapped:
        raise ValueError("Unknown discovery selection")
    sources = (
        [Path(selected["archive"]["path"])] if selected and selected["archive"]["path"] else []
    )
    libraries = [Path(p) for p in mapped["content"] + mapped["poser"]] if mapped else []
    return sources, libraries
