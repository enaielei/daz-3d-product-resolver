import pytest

from daz_resolver.discovery import discover, selected_paths, studio_settings


def test_dim_profiles_and_provenance(tmp_path):
    accounts = tmp_path / "DAZ 3D/InstallManager/UserAccounts"
    accounts.mkdir(parents=True)
    for name in ("a", "b"):
        (accounts / f"{name}.ini").write_text(
            "[General]\nDownloadPath=Z:/packages\nCurInstallPath=Z:/lib\n"
            "OverrideManifestDir=\nOverrideThumbnailDir=Z:/thumbs\n"
            "[InstallPaths]\nsize=2\n1\\InstallPath=Z:/first\n"
            "1\\InstallPathTitle=First\n2\\InstallPath=Z:/second\n"
        )
    result = discover(tmp_path, tmp_path / "public")
    assert result["selection_required"]
    profile = result["dim_profiles"][0]
    assert [p["path"] for p in profile["install_paths"]] == ["Z:/first", "Z:/second"]
    assert profile["manifest"]["provenance"] == "inferred-default"
    assert profile["thumbnail"]["provenance"] == "detected"
    with pytest.raises(ValueError, match="Multiple DIM"):
        selected_paths(result, None, None)


def test_studio_adapter_order_and_versions():
    values = {
        "NumContentDirs": 2,
        "ContentDir0": "first",
        "ContentDir1": "second",
        "NumPoserDirs": 1,
        "PoserDir0": "poser",
        "CloudDir": "cloud",
    }
    settings = studio_settings(lambda key, name: values[name])
    assert [s["id"] for s in settings] == ["Studio6", "Studio4"]
    assert settings[0]["content"] == ["first", "second"]
    with pytest.raises(ValueError, match="Multiple Studio"):
        selected_paths({"dim_profiles": [], "studio_settings": settings}, None, None)
