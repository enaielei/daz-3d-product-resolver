import gzip
import json
import stat
import subprocess
import sys
import zipfile

import pytest
from conftest import dson
from typer.testing import CliRunner

from daz_resolver.cli import app
from daz_resolver.dson import references
from daz_resolver.engine import Plan, make_plan
from daz_resolver.index import index_sources
from daz_resolver.install import install, recover
from daz_resolver.paths import ResolverError, relative


def test_end_to_end_whole_products_cycles_and_no_write_rerun(fixture):
    source, scene, destination = fixture
    inventory = index_sources([source])
    plan = make_plan(inventory, destination, [scene])
    assert not plan.blocked
    assert len(plan.products) == 2
    assert len(plan.operations) == 5
    assert not destination.exists()  # planning is read-only
    assert install(Plan.from_dict(plan.to_dict()))["written"] == 5
    assert (destination / "People/optional.duf").exists()
    assert not (destination / "Manifest.dsx").exists()
    assert not (destination / "Supplement.dsx").exists()
    before = {p: p.stat().st_mtime_ns for p in destination.rglob("*")}
    assert install(make_plan(inventory, destination, [scene]))["written"] == 0
    assert before == {p: p.stat().st_mtime_ns for p in destination.rglob("*")}
    assert (source / "Extracted/data/a.dsf").exists()


def test_install_all_uses_same_engine(fixture):
    source, _, destination = fixture
    plan = make_plan(index_sources([source]), destination)
    assert len(plan.products) == 2
    assert install(plan)["written"] == 5


def test_existing_libraries_precede_source_and_follow_dependencies(fixture, tmp_path):
    source, scene, destination = fixture
    existing = tmp_path / "existing"
    (existing / "DATA").mkdir(parents=True)
    (existing / "DATA/A.DSF").write_bytes(dson("/Runtime/Textures/b.png"))
    plan = make_plan(index_sources([source]), destination, [scene], [existing])
    assert len(plan.products) == 1
    assert plan.products[0].archive


def test_uri_gzip_relative_map_urls():
    document = {
        "asset_info": {"url": "ignore"},
        "image_library": [{"map": [{"url": "/Runtime/Textures/a%20b.png#id"}]}],
        "scene": {"nodes": [{"url": "../b.dsf#node"}, {"url": "#local"}]},
    }
    assert references(gzip.compress(json.dumps(document).encode()), "data/sub/a.dsf") == [
        "Runtime/Textures/a b.png",
        "data/b.dsf",
    ]


@pytest.mark.parametrize(
    "name",
    [
        "../x",
        "/x",
        "C:/x",
        "a/../../x",
        "a\\..\\x",
        "a/CON.txt",
        "a/x.",
        "a//b",
        "x:stream",
        "a/\x00x",
    ],
)
def test_unsafe_paths(name):
    with pytest.raises(ResolverError):
        relative(name)


@pytest.mark.parametrize("payload", [b"not json", b"{}", b"[1]", b"{bad"])
def test_malformed_scene_blocks(fixture, payload):
    source, scene, destination = fixture
    scene.write_bytes(payload)
    assert make_plan(index_sources([source]), destination, [scene]).blocked


def test_missing_dependency(fixture):
    source, scene, destination = fixture
    scene.write_bytes(dson("/absent.dsf"))
    plan = make_plan(index_sources([source]), destination, [scene])
    assert plan.missing == ["absent.dsf"]
    with pytest.raises(ResolverError):
        install(plan)


def test_competing_products_require_choice(fixture):
    source, scene, destination = fixture
    other = source / "Other/data"
    other.mkdir(parents=True)
    (other / "a.dsf").write_bytes(dson())
    inventory = index_sources([source])
    plan = make_plan(inventory, destination, [scene])
    ids = plan.ambiguities["data/a.dsf"]
    assert len(ids) == 2
    assert not make_plan(
        inventory, destination, [scene], choices={"data/a.dsf": ids[1]}
    ).ambiguities


def test_identical_ref_with_different_whole_product_is_ambiguous(fixture):
    source, scene, destination = fixture
    other = source / "Other/data"
    other.mkdir(parents=True)
    (other / "a.dsf").write_bytes((source / "Extracted/data/a.dsf").read_bytes())
    assert make_plan(index_sources([source]), destination, [scene]).ambiguities


def test_conflict_keep_replace_and_backup(fixture):
    source, _, destination = fixture
    target = destination / "Documentation/readme.txt"
    target.parent.mkdir(parents=True)
    target.write_text("user version")
    inventory = index_sources([source])
    assert make_plan(inventory, destination).blocked
    keep = make_plan(inventory, destination, conflicts={"Documentation/readme.txt": "keep"})
    install(keep)
    assert target.read_text() == "user version"
    replace = make_plan(inventory, destination, conflicts={"Documentation/readme.txt": "replace"})
    result = install(replace)
    assert target.read_text() == "Synthetic product"
    journal = json.loads(__import__("pathlib").Path(result["journal"]).read_text())
    backup = __import__("pathlib").Path(result["journal"]).parent / journal["writes"][0]["backup"]
    assert backup.read_text() == "user version"


@pytest.mark.parametrize("change", ["source", "destination"])
def test_stale_plan_rejected_before_writes(fixture, change):
    source, _, destination = fixture
    plan = make_plan(index_sources([source]), destination)
    if change == "source":
        (source / "Extracted/data/a.dsf").write_bytes(b"changed")
    else:
        (destination / "data").mkdir(parents=True)
        (destination / "data/a.dsf").write_bytes(b"user file")
    with pytest.raises(ResolverError):
        install(plan)
    assert not (destination / ".daz-product-resolver").exists()


def test_cancel_rolls_back_and_preserves_user_changes(fixture):
    source, _, destination = fixture
    stopped = False
    changed = []

    def progress(current, total, name):
        nonlocal stopped
        target = destination / name
        target.write_bytes(b"user edit")
        changed.append(target)
        stopped = True

    with pytest.raises(ResolverError, match="Cancelled"):
        install(make_plan(index_sources([source]), destination), lambda: stopped, progress)
    assert changed[0].read_bytes() == b"user edit"
    assert (
        len(
            [
                p
                for p in destination.rglob("*")
                if p.is_file() and ".daz-product-resolver" not in p.parts
            ]
        )
        == 1
    )
    assert any(recover(destination).values())


def test_failure_rolls_back_replacement(fixture):
    source, _, destination = fixture
    target = destination / "Documentation/readme.txt"
    target.parent.mkdir(parents=True)
    target.write_text("old")
    plan = make_plan(
        index_sources([source]), destination, conflicts={"Documentation/readme.txt": "replace"}
    )

    def fail(*_):
        raise OSError("simulated IO failure")

    with pytest.raises(OSError):
        install(plan, progress=fail)
    assert target.read_text() == "old"
    assert not (destination / "data/a.dsf").exists()


def test_no_destination_and_overlap_rejected(fixture):
    source, _, _ = fixture
    inventory = index_sources([source])
    for destination in [None, source, source / "Extracted/new"]:
        with pytest.raises(ResolverError):
            install(make_plan(inventory, destination))


@pytest.mark.parametrize("kind", ["traversal", "symlink", "software", "broken", "duplicate"])
def test_bad_archives_are_reported(tmp_path, kind):
    archive = tmp_path / "bad.zip"
    if kind == "broken":
        archive.write_bytes(b"broken")
    else:
        with zipfile.ZipFile(archive, "w") as z:
            if kind == "traversal":
                z.writestr("Content/../../escape", "bad")
            elif kind == "symlink":
                info = zipfile.ZipInfo("Content/linked")
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                z.writestr(info, "outside")
            elif kind == "software":
                z.writestr("Content/plugin.dll", "code")
            else:
                z.writestr("Content/a", "a")
                z.writestr("Content/A", "b")
    inventory = index_sources([tmp_path])
    assert not inventory.products
    assert inventory.reports


def test_nested_roots_and_ambiguous_boundary(tmp_path):
    root = tmp_path / "bundle"
    (root / "data").mkdir(parents=True)
    (root / "other/Content/People").mkdir(parents=True)
    (root / "data/a").write_text("a")
    assert "Ambiguous" in index_sources([tmp_path]).reports[0]
    assert index_sources([tmp_path], [root]).products


def test_cli_json_and_install_agree(fixture, tmp_path):
    source, scene, destination = fixture
    runner = CliRunner()
    output = tmp_path / "plan.json"
    result = runner.invoke(
        app,
        [
            "plan",
            "--source",
            str(source),
            "--scene",
            str(scene),
            "--destination",
            str(destination),
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 0, result.output
    plan = json.loads(result.stdout)
    assert len(plan["products"]) == 2
    result = runner.invoke(app, ["install", str(output)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["written"] == 5


def test_added_source_file_stales_whole_product_plan(fixture):
    source, _, destination = fixture
    plan = make_plan(index_sources([source]), destination)
    (source / "Extracted/People/new.txt").write_text("new whole-product file")
    with pytest.raises(ResolverError, match="inventory changed"):
        install(plan)
    assert not destination.exists()


def test_edited_plan_cannot_omit_or_remap_product_files(fixture):
    source, _, destination = fixture
    plan = make_plan(index_sources([source]), destination)
    plan.operations.pop()
    with pytest.raises(ResolverError, match="whole selected products"):
        install(plan)
    plan = make_plan(index_sources([source]), destination)
    plan.operations[0].path = "other.txt"
    with pytest.raises(ResolverError):
        install(plan)


def test_wrapper_documentation_preserved(tmp_path):
    product = tmp_path / "product"
    (product / "Content/People").mkdir(parents=True)
    (product / "Content/People/a.txt").write_text("content")
    (product / "Documentation").mkdir()
    (product / "Documentation/a.txt").write_text("docs")
    (product / "Manifest.dsx").write_text("plumbing")
    inventory = index_sources([product])
    assert {e.path for e in inventory.products[0].files} == {"People/a.txt", "Documentation/a.txt"}


def test_archive_resource_limit(tmp_path, monkeypatch):
    import daz_resolver.index as module

    monkeypatch.setattr(module, "MAX_FILE_BYTES", 5)
    archive = tmp_path / "large.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("Content/data/file", b"too large")
    inventory = index_sources([archive])
    assert not inventory.products
    assert "resource limit" in inventory.reports[0]


def test_gzip_scene_and_indirect_cycle(fixture):
    source, scene, destination = fixture
    scene.write_bytes(gzip.compress(scene.read_bytes()))
    plan = make_plan(index_sources([source]), destination, [scene])
    assert len(plan.products) == 2
    assert not plan.blocked


def test_index_reads_metadata_and_only_selected_payloads_are_hashed(fixture):
    source, scene, destination = fixture
    inventory = index_sources([source])
    assert all(not e.sha256 for p in inventory.products for e in p.files)
    plan = make_plan(inventory, destination, [scene])
    assert all(len(e.sha256) == 64 for p in plan.products for e in p.files)


def test_index_cancel_is_not_successful_empty_inventory(fixture):
    source, _, _ = fixture
    with pytest.raises(ResolverError, match="Cancelled"):
        index_sources([source], cancel=lambda: True)


def test_dson_node_qualified_references():
    assert references(
        dson(
            "Figure:#local?value",
            "Figure:/data/morph.dsf#shape?value",
            "name:/Figure:../b.dsf#shape?value",
            "id:/Figure:/data/a%23b.dsf#shape?value",
        ),
        "data/sub/a.dsf",
    ) == ["data/morph.dsf", "data/b.dsf", "data/a#b.dsf"]


@pytest.mark.parametrize(
    "value", ["C:/outside/file.dsf#id", "https://site/file.dsf#id", "file:///outside/file.dsf#id"]
)
def test_dson_network_and_drive_references_remain_unsupported(value):
    with pytest.raises(ResolverError):
        references(dson(value))


def test_abrupt_process_exit_recovers_original_replacement(tmp_path):
    source = tmp_path / "source"
    (source / "data").mkdir(parents=True)
    (source / "data/file.txt").write_text("new")
    destination = tmp_path / "library"
    (destination / "data").mkdir(parents=True)
    (destination / "data/file.txt").write_text("old")
    script = """
import os, sys
from pathlib import Path
from daz_resolver.index import index_sources
from daz_resolver.engine import make_plan
from daz_resolver.install import install
plan = make_plan(index_sources([Path(sys.argv[1])]), Path(sys.argv[2]),
                 conflicts={'data/file.txt': 'replace'})
install(plan, progress=lambda *_: os._exit(17))
"""
    process = subprocess.run(
        [sys.executable, "-c", script, str(source), str(destination)], check=False, timeout=30
    )
    assert process.returncode == 17
    assert (destination / "data/file.txt").read_text() == "new"
    assert list(recover(destination).values()) == [[]]
    assert (destination / "data/file.txt").read_text() == "old"
    assert (source / "data/file.txt").read_text() == "new"
