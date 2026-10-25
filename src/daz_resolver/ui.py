"""Desktop review and execution surface; all expensive work runs off the UI thread."""

import json
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .cli import pairs
from .discovery import discover, selected_paths
from .engine import make_plan
from .index import index_sources
from .install import install


class Worker(QThread):
    done = Signal(object)
    failed = Signal(str)
    progress = Signal(int, int, str)

    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task
        self.cancelled = threading.Event()

    def run(self):
        try:
            self.done.emit(self.task(self.cancelled.is_set, self.progress.emit))
        except Exception as exc:
            self.failed.emit(str(exc))


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Daz 3D Product Resolver")
        self.resize(1000, 760)
        self.worker = None
        self.plan = None
        self.discovery = None
        widget = QWidget()
        self.setCentralWidget(widget)
        layout = QVBoxLayout(widget)
        layout.addWidget(
            QLabel("Offline whole-product installation · Review a plan before copying")
        )
        self.inputs = {}
        for key, label in (
            ("source", "Source folders"),
            ("library", "Existing libraries"),
            ("scene", "DUF/DSF scenes (optional)"),
            ("product_root", "Explicit product roots (optional)"),
            ("destination", "Destination library (required for install)"),
        ):
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            edit = QLineEdit()
            edit.setPlaceholderText("Use Browse to add; separate multiple paths with |")
            self.inputs[key] = edit
            row.addWidget(edit, 1)
            button = QPushButton("Browse…")
            button.clicked.connect(lambda checked=False, k=key: self.browse(k))
            row.addWidget(button)
            layout.addLayout(row)
            edit.textChanged.connect(self.invalidate)
        layout.addWidget(QLabel("Multiple paths use | separators. Inputs are user overrides."))
        row = QHBoxLayout()
        self.detect_button = QPushButton("Discover settings")
        self.detect_button.clicked.connect(self.detect)
        row.addWidget(self.detect_button)
        self.profile = QComboBox()
        self.studio = QComboBox()
        self.profile.addItem("Select DIM profile", None)
        self.studio.addItem("Select Studio settings", None)
        row.addWidget(self.profile, 1)
        row.addWidget(self.studio, 1)
        self.use_button = QPushButton("Use selected settings")
        self.use_button.clicked.connect(self.use_detected)
        row.addWidget(self.use_button)
        layout.addLayout(row)
        self.choices = QLineEdit()
        self.choices.setPlaceholderText("Product choices: relative/path=PRODUCT_ID | …")
        self.conflicts = QLineEdit()
        self.conflicts.setPlaceholderText("Conflict decisions: relative/path=keep or =replace | …")
        for edit in (self.choices, self.conflicts):
            edit.textChanged.connect(self.invalidate)
            layout.addWidget(edit)
        row = QHBoxLayout()
        self.plan_button = QPushButton("Build read-only plan")
        self.plan_button.clicked.connect(self.build_plan)
        self.install_button = QPushButton("Install reviewed products")
        self.install_button.setEnabled(False)
        self.install_button.clicked.connect(self.execute)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel)
        for button in (self.plan_button, self.install_button, self.cancel_button):
            row.addWidget(button)
        layout.addLayout(row)
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output, 1)

    def invalidate(self):
        self.plan = None
        self.install_button.setEnabled(False)

    def paths(self, key):
        return [Path(p.strip()) for p in self.inputs[key].text().split("|") if p.strip()]

    def browse(self, key):
        if key == "scene":
            values, _ = QFileDialog.getOpenFileNames(
                self, "Select scenes", "", "DSON (*.duf *.dsf)"
            )
        else:
            value = QFileDialog.getExistingDirectory(self, "Select folder")
            values = [value] if value else []
        if values:
            old = self.inputs[key].text()
            self.inputs[key].setText(
                " | ".join(([old] if old and key != "destination" else []) + values)
            )

    def start(self, task, callback):
        if self.worker and self.worker.isRunning():
            return
        self.install_button.setEnabled(False)
        self.plan_button.setEnabled(False)
        self.detect_button.setEnabled(False)
        self.use_button.setEnabled(False)
        for edit in [*self.inputs.values(), self.choices, self.conflicts]:
            edit.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress.setRange(0, 0)
        self.worker = Worker(task, self)
        self.worker.done.connect(callback)
        self.worker.failed.connect(lambda message: self.output.setPlainText(f"Error: {message}"))
        self.worker.progress.connect(self.show_progress)
        self.worker.finished.connect(self.finished)
        self.worker.start()

    def finished(self):
        self.plan_button.setEnabled(True)
        self.detect_button.setEnabled(True)
        self.use_button.setEnabled(True)
        for edit in [*self.inputs.values(), self.choices, self.conflicts]:
            edit.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.install_button.setEnabled(
            bool(self.plan and self.plan.destination and not self.plan.blocked)
        )

    def show_progress(self, current, total, path):
        self.progress.setRange(0, total)
        self.progress.setValue(current)
        self.statusBar().showMessage(path)

    def cancel(self):
        if self.worker:
            self.worker.cancelled.set()

    def detect(self):
        self.start(lambda *_: discover(), self.show_discovery)

    def show_discovery(self, value):
        self.discovery = value
        self.profile.clear()
        self.studio.clear()
        self.profile.addItem("Select DIM profile", None)
        self.studio.addItem("Select Studio settings", None)
        for item in value["dim_profiles"]:
            self.profile.addItem(item["profile"], item["profile"])
        for item in value["studio_settings"]:
            self.studio.addItem(item["id"], item["id"])
        self.output.setPlainText(json.dumps(value, indent=2))

    def use_detected(self):
        if not self.discovery:
            return
        try:
            sources, libraries = selected_paths(
                self.discovery, self.profile.currentData(), self.studio.currentData()
            )
            self.inputs["source"].setText(" | ".join(map(str, sources)))
            self.inputs["library"].setText(" | ".join(map(str, libraries)))
        except ValueError as exc:
            self.output.setPlainText(str(exc))

    def build_plan(self):
        self.invalidate()
        paths = {k: self.paths(k) for k in self.inputs}
        try:
            choices = pairs([p.strip() for p in self.choices.text().split("|") if p.strip()])
            conflicts = pairs([p.strip() for p in self.conflicts.text().split("|") if p.strip()])
            if not paths["source"]:
                raise ValueError("Select at least one source folder")
        except ValueError as exc:
            self.output.setPlainText(str(exc))
            return

        def task(cancel, progress):
            inventory = index_sources(paths["source"], paths["product_root"], cancel)
            return make_plan(
                inventory,
                paths["destination"][0] if paths["destination"] else None,
                paths["scene"],
                paths["library"],
                choices,
                conflicts,
                cancel,
            )

        self.start(task, self.show_plan)

    def show_plan(self, value):
        self.plan = value
        self.output.setPlainText(json.dumps(value.to_dict(), indent=2))

    def execute(self):
        plan = self.plan
        self.plan = None
        if plan:
            self.start(
                lambda cancel, progress: install(plan, cancel, progress),
                lambda result: self.output.setPlainText(json.dumps(result, indent=2)),
            )

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.cancel()
            self.statusBar().showMessage("Waiting for cancellation and safe rollback…")
            event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    window = Window()
    window.show()
    if "--smoke-test" in sys.argv:
        QTimer.singleShot(300, app.quit)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
