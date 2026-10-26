import json
import zipfile

import pytest


def dson(*urls):
    return json.dumps(
        {"asset_info": {"id": "example"}, "scene": {"nodes": [{"url": url} for url in urls]}}
    ).encode()


@pytest.fixture
def fixture(tmp_path):
    source = tmp_path / "sources"
    product = source / "Extracted"
    (product / "data").mkdir(parents=True)
    (product / "People").mkdir()
    (product / "Documentation").mkdir()
    (product / "data/a.dsf").write_bytes(dson("/Runtime/Textures/b.png", "/data/a.dsf"))
    (product / "People/optional.duf").write_bytes(dson("/missing-optional.png"))
    (product / "Documentation/readme.txt").write_text("Synthetic product")
    archive = source / "Texture.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("Content/Runtime/Textures/b.png", b"synthetic image")
        z.writestr("Content/Props/whole.txt", b"not referenced, still copied")
        z.writestr(
            "Manifest.dsx",
            '<DAZInstallManifest><File TARGET="Content" '
            'ACTION="Install" VALUE="Content/Runtime/Textures/b.png"/>'
            '<File TARGET="Content" ACTION="Install" VALUE="Content/Props/whole.txt"/>'
            "</DAZInstallManifest>",
        )
        z.writestr("Supplement.dsx", "installer plumbing")
    scene = tmp_path / "scene.duf"
    scene.write_bytes(dson("/data/a.dsf#node"))
    return source, scene, tmp_path / "library"
