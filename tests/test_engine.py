import gzip
import json
import stat
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

    def progress(*_):
        nonlocal stopped
        (destination / "data/a.dsf").write_bytes(b"user edit")
        stopped = True

    with pytest.raises(ResolverError, match="Cancelled"):
        install(make_plan(index_sources([source]), destination), lambda: stopped, progress)
    assert (destination / "data/a.dsf").read_bytes() == b"user edit"
    assert not (destination / "People/optional.duf").exists()
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
