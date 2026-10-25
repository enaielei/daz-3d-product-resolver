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
