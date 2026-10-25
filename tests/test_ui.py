from pathlib import Path

from PySide6.QtWidgets import QComboBox

from daz_resolver.engine import make_plan
from daz_resolver.index import index_sources
from daz_resolver.ui import Window


def test_ui_plan_matches_engine_and_installs(qtbot, fixture):
    source, scene, destination = fixture
    window = Window()
    qtbot.addWidget(window)
    window.show()
    for key, value in {"source": source, "scene": scene, "destination": destination}.items():
        window.inputs[key].setText(str(value))
    with qtbot.waitSignal(window.plan_button.clicked, timeout=5000):
        window.plan_button.click()
    qtbot.waitUntil(
        lambda: window.plan is not None and not window.worker.isRunning(), timeout=15000
    )
    expected = make_plan(index_sources([source]), destination, [scene])
    assert window.plan.to_dict() == expected.to_dict()
    qtbot.waitUntil(window.install_button.isEnabled)
    window.install_button.click()
    qtbot.waitUntil(lambda: not window.worker.isRunning(), timeout=15000)
    assert (destination / "Props/whole.txt").exists()
    qtbot.waitUntil(lambda: '"written": 5' in window.output.toPlainText(), timeout=5000)


def test_edit_invalidates_reviewed_plan(qtbot, fixture):
    source, _, destination = fixture
    window = Window()
    qtbot.addWidget(window)
    window.show_plan(make_plan(index_sources([source]), destination))
    window.inputs["source"].setText("changed")
    assert window.plan is None
    assert not window.install_button.isEnabled()


def configured(qtbot, fixture):
    source, scene, destination = fixture
    window = Window()
    qtbot.addWidget(window)
    window.show()
    for key, path in {"source": source, "scene": scene, "destination": destination}.items():
        window.inputs[key].setText(str(path))
    return window


def checked(qtbot, window):
    window.build_plan()
    qtbot.waitUntil(lambda: window.plan is not None and not window.busy, timeout=15000)


def test_beginner_flow_explains_required_inputs(qtbot):
    window = Window()
    qtbot.addWidget(window)
    window.show()
    assert not window.output.isVisible()
    window.next_button.click()
    assert "Add at least one folder" in window.notice.text()
    assert window.pages.currentIndex() == 0
    assert not window.install_button.isEnabled()


def test_guided_navigation_to_review(qtbot, fixture):
    window = configured(qtbot, fixture)
    window.next_button.click()
    assert window.pages.currentIndex() == 1
    window.next_button.click()
    qtbot.waitUntil(lambda: window.plan is not None and not window.busy, timeout=15000)
    assert window.pages.currentIndex() == 2
    assert window.products_table.rowCount() == 2
    assert window.stats[0].text() == "2"
    assert "Ready to install" in window.notice.text()
    assert window.install_button.isEnabled()


def test_check_only_does_not_require_destination_or_allow_install(qtbot, fixture):
    window = configured(qtbot, fixture)
    window.inputs["destination"].clear()
    window.preview_only.setChecked(True)
    checked(qtbot, window)
    assert window.plan.destination is None
    assert not window.install_button.isEnabled()
    assert "Preview complete" in window.notice.text()
    assert not fixture[2].exists()


def test_install_all_is_explicit(qtbot, fixture):
    window = configured(qtbot, fixture)
    window.inputs["scene"].setText("")
    window.next_button.click()
    assert "Add a scene" in window.notice.text()
    window.all_mode.setChecked(True)
    window.next_button.click()
    assert window.pages.currentIndex() == 1
    checked(qtbot, window)
    assert len(window.plan.products) == 2


def test_conflict_is_chosen_with_dropdown_then_rechecked(qtbot, fixture):
    window = configured(qtbot, fixture)
    target = fixture[2] / "Documentation/readme.txt"
    target.parent.mkdir(parents=True)
    target.write_text("my existing file")
    checked(qtbot, window)
    assert window.plan.blocked
    assert window.tabs.currentIndex() == 1
    combos = window.attention.findChildren(QComboBox)
    combo = next(c for c in combos if c.findData("replace") >= 0)
    combo.setCurrentIndex(combo.findData("replace"))
    assert window.plan is None
    assert not window.install_button.isEnabled()
    checked(qtbot, window)
    assert not window.plan.blocked
    assert any(o.action == "replace" for o in window.plan.operations)
    window.install_button.click()
    qtbot.waitUntil(lambda: not window.busy, timeout=15000)
    assert target.read_text() == "Synthetic product"
    assert "Installation complete" in window.notice.text()


def test_already_available_is_clear_and_no_install_offered(qtbot, fixture):
    from daz_resolver.install import install

    window = configured(qtbot, fixture)
    install(make_plan(index_sources([fixture[0]]), fixture[2], [fixture[1]]))
    checked(qtbot, window)
    assert "You’re all set" in window.notice.text()
    assert not window.install_button.isEnabled()


def test_multiple_detected_settings_require_choice_and_preserve_manual_paths(qtbot, fixture):
    window = configured(qtbot, fixture)
    profile = {"profile": str(Path("profile.ini")), "archive": {"path": "packages"}}
    window.show_discovery(
        {
            "dim_profiles": [profile],
            "studio_settings": [
                {"id": "Studio6", "content": ["library-one"], "poser": []},
                {"id": "Studio4", "content": ["library-two"], "poser": []},
            ],
            "reports": [],
        }
    )
    assert window.studio.currentData() is None
    window.use_detected()
    assert "Multiple Studio" in window.notice.text()
    window.studio.setCurrentIndex(1)
    window.use_detected()
    assert fixture[0] in window.paths("source")
    assert Path("packages") in window.paths("source")
    assert Path("library-one") in window.paths("library")
    assert window.inputs["library"].property("provenance") == "detected"


def test_cancel_keeps_navigation_locked_until_worker_stops(qtbot):
    import threading

    from daz_resolver.paths import ResolverError

    window = Window()
    qtbot.addWidget(window)
    window.show()
    tick = threading.Event()

    def slow_check(cancel, progress):
        while not cancel():
            tick.wait(0.01)
        raise ResolverError("Cancelled")

    window.start(slow_check, lambda _: None)
    assert not window.next_button.isEnabled()
    assert not window.pages.widget(0).isEnabled()
    window.cancel_button.click()
    qtbot.waitUntil(lambda: not window.busy, timeout=5000)
    assert "Operation cancelled" in window.notice.text()
    assert window.next_button.isEnabled()
    assert not window.install_button.isEnabled()


def test_ambiguity_dropdown_selects_containing_product(qtbot, fixture):
    source, _, _ = fixture
    other = source / "Other/data"
    other.mkdir(parents=True)
    (other / "a.dsf").write_text('{"asset_info": {}, "scene": {}}')
    window = configured(qtbot, fixture)
    checked(qtbot, window)
    assert window.plan.ambiguities
    combo = window.attention.findChildren(QComboBox)[0]
    candidate = next(i for i in range(combo.count()) if "Other" in combo.itemText(i))
    combo.setCurrentIndex(candidate)
    assert not window.install_button.isEnabled()
    checked(qtbot, window)
    assert not window.plan.blocked
    assert len(window.plan.products) == 1
    assert Path(window.plan.products[0].source).name == "Other"
