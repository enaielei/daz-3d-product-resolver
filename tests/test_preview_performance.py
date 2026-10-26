import json

import pytest

from daz_resolver.diagnostics import RunDiagnostics
from daz_resolver.engine import LibraryLookup, Plan, make_plan
from daz_resolver.index import index_sources
from daz_resolver.install import install
from daz_resolver.paths import ResolverError


def test_check_only_does_not_hash_unique_product_payloads(fixture):
    source, _, _ = fixture
    inventory = index_sources([source])
    stages = []
    plan = make_plan(inventory, progress=lambda c, t, stage: stages.append(stage))
    assert not plan.blocked
    assert all(not e.sha256 for product in plan.products for e in product.files)
    assert not any("Comparing payload bytes" in s for s in stages)
    assert plan.configuration["payload_verification"] == "shared-files-only"
    assert stages[-1] == "Check complete"


def test_source_overlap_requires_provider_and_installs_whole_union(tmp_path):
    source = tmp_path / "sources"
    for name, shared, unique in [("A", "first", "one"), ("B", "second", "two")]:
        data = source / name / "data"
        data.mkdir(parents=True)
        (data / "shared.txt").write_text(shared)
        (data / f"{name}.txt").write_text(unique)
    preview = make_plan(index_sources([source]))
    assert preview.blocked
    assert len(preview.overlaps["data/shared.txt"]) == 2
    assert not any("disagree" in text for text in preview.reports)
    chosen = next(p.id for p in preview.products if p.source.endswith("B"))
    destination = tmp_path / "library"
    plan = make_plan(index_sources([source]), destination, choices={"data/shared.txt": chosen})
    assert not plan.blocked
    assert len(plan.products) == 2
    install(Plan.from_dict(plan.to_dict()))
    assert (destination / "data/shared.txt").read_text() == "second"
    assert (destination / "data/A.txt").read_text() == "one"
    assert (destination / "data/B.txt").read_text() == "two"


def test_readonly_preview_cannot_be_edited_into_unverified_install(fixture):
    source, _, destination = fixture
    plan = make_plan(index_sources([source]))
    plan.destination = str(destination)
    with pytest.raises(ResolverError, match="hashes required"):
        install(plan)
    assert not destination.exists()


def test_lookup_scans_each_directory_once_and_does_not_cache_across_runs(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    for i in range(50):
        (data / f"{i}.txt").write_text("file")
    from pathlib import Path

    original = Path.iterdir
    calls = []

    def counted(path):
        calls.append(path)
        return original(path)

    monkeypatch.setattr(Path, "iterdir", counted)
    lookup = LibraryLookup()
    for i in range(50):
        assert lookup.find(tmp_path, f"DATA/{i}.txt")
    assert calls.count(data) == 1
    assert calls.count(tmp_path) == 1
    (data / "new.txt").write_text("new")
    assert LibraryLookup().find(tmp_path, "data/new.txt")


def test_private_diagnostics_records_configuration_progress_and_result(tmp_path, fixture):
    source, _, _ = fixture
    log = RunDiagnostics(tmp_path / "logs", "check", {"mode": "install-all", "check_only": True})
    log.progress(1, 2, "Indexing product inventories")
    log.finish(make_plan(index_sources([source])))
    records = [json.loads(line) for line in log.path.read_text().splitlines()]
    assert [r["event"] for r in records] == ["started", "progress", "completed"]
    assert records[0]["build"].endswith("preview.2")
    result = records[-1]["result"]
    assert result["product_count"] == 2
    assert "files" not in result["products"][0] or isinstance(result["products"][0]["files"], int)
    assert result["payload_verification"] == "shared-files-only"
