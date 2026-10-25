"""A guided desktop workflow backed by the portable planning/install engine."""

import json
import sys
import threading
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .discovery import discover, selected_paths
from .engine import make_plan
from .index import index_sources
from .install import install
from .ui_widgets import PathPicker, application_style, card, label, light_palette, size_text


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
        self.resize(1120, 860)
        self.setMinimumSize(940, 720)
        self.setPalette(light_palette())
        self.setStyleSheet(application_style())
        self.worker = self.plan = self.inventory = self.discovery = None
        self.busy = False
        self.operation = "check"
        self.product_choices = {}
        self.conflict_decisions = {}
        self.inputs = {}
        canvas = QWidget()
        canvas.setObjectName("canvas")
        self.setCentralWidget(canvas)
        root = QHBoxLayout(canvas)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        left = QVBoxLayout(sidebar)
        left.setContentsMargins(23, 34, 23, 24)
        left.setSpacing(12)
        left.addWidget(label("DAZ PRODUCT\nRESOLVER", "brand"))
        left.addWidget(label("Your content, connected.", "sidebarNote"))
        left.addSpacing(35)
        self.steps = []
        for i, title in enumerate(
            ("1   Choose content", "2   Set up libraries", "3   Review and install")
        ):
            button = QPushButton(title)
            button.setObjectName("step")
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, n=i: self.go(n))
            left.addWidget(button)
            self.steps.append(button)
        left.addStretch()
        left.addWidget(label("LOCAL & OFFLINE", "sidebarNote"))
        left.addWidget(label(f"v{__version__} · Preview", "sidebarNote"))
        left.addWidget(
            label("Uses the products you already\nhave. Copies whole products.", "sidebarNote")
        )
        help_button = QPushButton("Quick guide")
        help_button.clicked.connect(self.help)
        left.addWidget(help_button)
        root.addWidget(sidebar)
        body = QVBoxLayout()
        body.setContentsMargins(30, 25, 30, 22)
        body.setSpacing(13)
        body.addWidget(label("A LITTLE LESS SEARCHING. A LITTLE MORE CREATING.", "eyebrow"))
        self.title = label("", "title")
        self.subtitle = label("", "subtitle")
        body.addWidget(self.title)
        body.addWidget(self.subtitle)
        self.notice = label("", "notice")
        self.notice.hide()
        body.addWidget(self.notice)
        self.pages = QStackedWidget()
        body.addWidget(self.pages, 1)
        self.setup_page()
        self.libraries_page()
        self.review_page()
        self.activity = QWidget()
        activity_layout = QVBoxLayout(self.activity)
        activity_layout.setContentsMargins(0, 0, 0, 0)
        self.activity_label = label("", "muted")
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        activity_layout.addWidget(self.activity_label)
        activity_layout.addWidget(self.progress)
        self.activity.hide()
        body.addWidget(self.activity)
        footer = QHBoxLayout()
        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(lambda: self.go(max(0, self.pages.currentIndex() - 1)))
        footer.addWidget(self.back_button)
        footer.addStretch()
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel)
        self.cancel_button.hide()
        footer.addWidget(self.cancel_button)
        self.plan_button = QPushButton("Check again")
        self.plan_button.clicked.connect(self.build_plan)
        footer.addWidget(self.plan_button)
        self.next_button = QPushButton("Continue to libraries →")
        self.next_button.setObjectName("primary")
        self.next_button.clicked.connect(self.next)
        footer.addWidget(self.next_button)
        self.install_button = QPushButton("Install products")
        self.install_button.setObjectName("primary")
        self.install_button.clicked.connect(self.execute)
        footer.addWidget(self.install_button)
        body.addLayout(footer)
        root.addLayout(body, 1)
        for key, control in self.inputs.items():
            control.textChanged.connect(lambda _, k=key: self.changed(k))
        self.scene_mode.toggled.connect(self.mode_changed)
        self.go(0)

    def page(self):
        content = QWidget()
        content.setObjectName("pageContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(13)
        scroll = QScrollArea()
        scroll.viewport().setObjectName("pageViewport")
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        self.pages.addWidget(scroll)
        return layout

    def picker_card(self, layout, key, title, description):
        frame, inside = card(title, description)
        picker = PathPicker("scene" if key == "scene" else "folder", title)
        self.inputs[key] = picker
        inside.addWidget(picker)
        layout.addWidget(frame)
        return frame

    def setup_page(self):
        layout = self.page()
        frame, inside = card("What would you like to do?")
        self.scene_mode = QRadioButton("Find missing content for my scenes")
        self.scene_mode.setChecked(True)
        self.all_mode = QRadioButton("Install all products in my source folders")
        group = QButtonGroup(self)
        group.addButton(self.scene_mode)
        group.addButton(self.all_mode)
        inside.addWidget(self.scene_mode)
        inside.addWidget(self.all_mode)
        layout.addWidget(frame)
        self.scene_card = self.picker_card(
            layout,
            "scene",
            "Your scenes or presets",
            "Add the .duf or .dsf files you want to use. We’ll check their file references.",
        )
        self.picker_card(
            layout,
            "source",
            "Where are your downloaded products?",
            "Add folders containing product ZIPs or extracted products. "
            "Nothing is moved or deleted.",
        )
        layout.addStretch()

    def libraries_page(self):
        layout = self.page()
        frame, inside = card(
            "Let’s find your existing content",
            "Existing libraries are checked first, so you don’t install what you already have.",
        )
        row = QHBoxLayout()
        self.detect_button = QPushButton("Find my DAZ folders")
        self.detect_button.clicked.connect(self.detect)
        row.addWidget(self.detect_button)
        self.discovery_note = label("Or add your folders manually below.", "muted")
        row.addWidget(self.discovery_note, 1)
        inside.addLayout(row)
        self.detection_controls = QWidget()
        detected = QVBoxLayout(self.detection_controls)
        detected.setContentsMargins(0, 0, 0, 0)
        self.profile = QComboBox()
        self.profile.setAccessibleName("DIM profile")
        self.studio = QComboBox()
        self.studio.setAccessibleName("DAZ Studio version settings")
        detected.addWidget(label("Choose the settings to use", "muted"))
        detected.addWidget(self.profile)
        detected.addWidget(self.studio)
        self.use_button = QPushButton("Add these detected folders")
        self.use_button.clicked.connect(self.use_detected)
        detected.addWidget(self.use_button)
        self.detection_controls.hide()
        inside.addWidget(self.detection_controls)
        layout.addWidget(frame)
        self.picker_card(
            layout,
            "library",
            "Already installed content libraries",
            "DAZ library roots usually contain data, People or Runtime folders.",
        )
        frame, inside = card(
            "Where should missing products be installed?",
            "Choose a DAZ content library. Files go here only after you review and click Install.",
        )
        row = QHBoxLayout()
        self.inputs["destination"] = QLineEdit()
        self.inputs["destination"].setAccessibleName("Install into library")
        self.inputs["destination"].setPlaceholderText("Choose an installation library…")
        row.addWidget(self.inputs["destination"], 1)
        self.destination_button = QPushButton("Choose folder…")
        self.destination_button.clicked.connect(self.browse_destination)
        row.addWidget(self.destination_button)
        inside.addLayout(row)
        self.preview_only = QCheckBox("Check only — I’ll choose an install folder later")
        self.preview_only.toggled.connect(self.preview_changed)
        inside.addWidget(self.preview_only)
        layout.addWidget(frame)
        self.advanced_toggle = QToolButton()
        self.advanced_toggle.setText("Advanced: product folder boundaries")
        self.advanced_toggle.setCheckable(True)
        layout.addWidget(self.advanced_toggle)
        self.advanced = QWidget()
        advanced_layout = QVBoxLayout(self.advanced)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        self.picker_card(
            advanced_layout,
            "product_root",
            "Explicit product folders",
            "Only needed if a check reports an ambiguous extracted product boundary.",
        )
        self.advanced.hide()
        self.advanced_toggle.toggled.connect(self.advanced.setVisible)
        layout.addWidget(self.advanced)
        layout.addStretch()

    def review_page(self):
        layout = self.page()
        row = QHBoxLayout()
        self.stats = []
        for text in ("Selected products", "To copy", "Already identical"):
            frame, inside = card()
            value = label("—", "statValue")
            inside.addWidget(value)
            inside.addWidget(label(text, "muted"))
            self.stats.append(value)
            row.addWidget(frame, 1)
        layout.addLayout(row)
        self.review_hint = label("Run a check to see what your scenes need.", "muted")
        layout.addWidget(self.review_hint)
        self.tabs = QTabWidget()
        self.products_table = QTableWidget(0, 4)
        self.products_table.setHorizontalHeaderLabels(
            ["Product folder or package", "Type", "Files", "Size"]
        )
        self.products_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.products_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.products_table.verticalHeader().hide()
        self.products_table.setAlternatingRowColors(True)
        self.products_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.tabs.addTab(self.products_table, "Products")
        self.attention = QTreeWidget()
        self.attention.setHeaderLabels(["File or package", "What to do", "Your choice"])
        self.attention.setRootIsDecorated(False)
        self.attention.setWordWrap(True)
        self.attention.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.attention.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.attention.setColumnWidth(2, 230)
        self.tabs.addTab(self.attention, "Needs attention")
        self.tabs.setMinimumHeight(230)
        layout.addWidget(self.tabs, 1)
        self.open_button = QPushButton("Open installation library")
        self.open_button.clicked.connect(self.open_library)
        self.open_button.hide()
        layout.addWidget(self.open_button)
        toggle = QToolButton()
        toggle.setText("Technical details (optional)")
        toggle.setCheckable(True)
        layout.addWidget(toggle)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setAccessibleName("Technical JSON details")
        self.output.setMinimumHeight(170)
        self.output.hide()
        toggle.toggled.connect(self.output.setVisible)
        layout.addWidget(self.output)

    def say(self, text, tone=""):
        self.notice.setText(text)
        self.notice.setProperty("tone", tone)
        self.notice.style().unpolish(self.notice)
        self.notice.style().polish(self.notice)
        self.notice.setVisible(bool(text))

    def go(self, index):
        if self.busy:
            return
        self.pages.setCurrentIndex(index)
        self.title.setText(
            (
                "Find what your scene needs.",
                "Tell us where your content lives.",
                "Check. Review. Create.",
            )[index]
        )
        self.subtitle.setText(
            (
                "Start with your scenes and the products you already downloaded.",
                "We’ll look in your libraries before searching your source folders.",
                "Review whole products and any decisions before files are copied.",
            )[index]
        )
        for i, button in enumerate(self.steps):
            button.setChecked(i == index)
        self.refresh_actions()

    def next(self):
        if self.pages.currentIndex() == 0:
            if not self.paths("source"):
                self.say("Add at least one folder containing your downloaded products.", "warning")
                return
            if self.scene_mode.isChecked() and not self.paths("scene"):
                self.say("Add a scene file, or choose “Install all products” above.", "warning")
                return
            self.say("")
            self.go(1)
        else:
            self.build_plan()

    def refresh_actions(self):
        index = self.pages.currentIndex()
        self.back_button.setVisible(index > 0)
        self.back_button.setEnabled(not self.busy)
        self.next_button.setVisible(index < 2)
        self.next_button.setText(
            "Continue to libraries →" if index == 0 else "Check dependencies →"
        )
        self.next_button.setEnabled(not self.busy)
        self.plan_button.setVisible(index == 2)
        self.plan_button.setEnabled(not self.busy)
        self.install_button.setVisible(index == 2)
        actionable = bool(
            self.plan and any(o.action in {"copy", "replace"} for o in self.plan.operations)
        )
        self.install_button.setEnabled(
            bool(
                not self.busy
                and self.plan
                and self.plan.destination
                and not self.plan.blocked
                and actionable
            )
        )
        self.cancel_button.setVisible(self.busy)
        for button in self.steps:
            button.setEnabled(not self.busy)

    def invalidate(self):
        self.plan = None
        self.open_button.hide()
        self.refresh_actions()

    def changed(self, key):
        self.inputs[key].setProperty("provenance", "user")
        self.product_choices.clear()
        self.conflict_decisions.clear()
        self.invalidate()
        if self.pages.currentIndex() == 2:
            self.say("Your folders changed. Check again to refresh the review.", "warning")

    def mode_changed(self):
        self.scene_card.setVisible(self.scene_mode.isChecked())
        self.invalidate()

    def preview_changed(self):
        self.inputs["destination"].setEnabled(not self.preview_only.isChecked())
        self.invalidate()

    def paths(self, key):
        if key == "destination":
            value = self.inputs[key].text().strip()
            return [Path(value)] if value else []
        return self.inputs[key].paths()

    def browse_destination(self):
        value = QFileDialog.getExistingDirectory(self, "Choose the DAZ library to install into")
        if value:
            self.preview_only.setChecked(False)
            self.inputs["destination"].setText(value)

    def start(self, task, callback, operation="check"):
        if self.busy:
            return
        self.operation = operation
        self.busy = True
        self.say("")
        self.activity.show()
        self.activity_label.setText(
            {
                "check": "Checking your content… This does not install files.",
                "discover": "Looking for DAZ settings…",
                "install": "Installing and verifying products…",
            }[operation]
        )
        self.progress.setRange(0, 0)
        for index in (0, 1):
            self.pages.widget(index).setEnabled(False)
        self.tabs.setEnabled(False)
        self.refresh_actions()
        self.worker = Worker(task, self)
        self.worker.done.connect(callback)
        self.worker.failed.connect(self.failed)
        self.worker.progress.connect(self.show_progress)
        self.worker.finished.connect(self.finished)
        self.worker.start()

    def finished(self):
        self.busy = False
        for index in (0, 1):
            self.pages.widget(index).setEnabled(True)
        self.inputs["destination"].setEnabled(not self.preview_only.isChecked())
        self.tabs.setEnabled(True)
        self.activity.hide()
        self.refresh_actions()

    def failed(self, message):
        cancelled = self.worker and self.worker.cancelled.is_set()
        title = "Operation cancelled." if cancelled else "We couldn’t finish this operation."
        self.say(f"{title} {message}", "warning" if cancelled else "error")
        self.output.setPlainText(json.dumps({"error": message}, indent=2))

    def show_progress(self, current, total, path):
        self.progress.setRange(0, total)
        self.progress.setValue(current)
        self.activity_label.setText(f"{current} of {total} files · {path}")

    def cancel(self):
        if self.worker:
            self.worker.cancelled.set()
            self.activity_label.setText("Stopping safely… Please wait for the current file.")

    def detect(self):
        self.start(lambda *_: discover(), self.show_discovery, "discover")

    def show_discovery(self, value):
        self.discovery = value
        self.profile.clear()
        self.studio.clear()
        self.profile.addItem("Choose a DIM profile…", None)
        self.studio.addItem("Choose a Studio version…", None)
        for item in value["dim_profiles"]:
            self.profile.addItem(Path(item["profile"]).stem, item["profile"])
            self.profile.setItemData(
                self.profile.count() - 1, item["profile"], Qt.ItemDataRole.ToolTipRole
            )
        for item in value["studio_settings"]:
            self.studio.addItem(item["id"], item["id"])
        if self.profile.count() == 2:
            self.profile.setCurrentIndex(1)
        if self.studio.count() == 2:
            self.studio.setCurrentIndex(1)
        self.detection_controls.show()
        self.discovery_note.setText(
            f"Found {len(value['dim_profiles'])} DIM profile(s) and "
            f"{len(value['studio_settings'])} Studio setting(s)."
        )
        self.output.setPlainText(json.dumps(value, indent=2))
        self.say(
            "Choose settings below, then add the detected folders. "
            "Your DAZ settings stay unchanged."
        )

    def use_detected(self):
        if not self.discovery:
            return
        try:
            sources, libraries = selected_paths(
                self.discovery, self.profile.currentData(), self.studio.currentData()
            )
            for key, paths in (("source", sources), ("library", libraries)):
                existing = self.paths(key)
                self.inputs[key].add_paths(paths)
                self.inputs[key].setProperty(
                    "provenance", "user + detected" if existing else "detected"
                )
            self.say(
                "Detected folders added. Choose an install library below, or use Check only.",
                "success",
            )
        except ValueError as exc:
            self.say(str(exc), "warning")

    def build_plan(self):
        if self.busy:
            return
        self.invalidate()
        paths = {k: self.paths(k) for k in self.inputs}
        if not paths["source"] or (self.scene_mode.isChecked() and not paths["scene"]):
            self.go(0)
            self.say(
                "Add your product folders and scene files first, or choose Install all products.",
                "warning",
            )
            return
        if not paths["destination"] and not self.preview_only.isChecked():
            self.go(1)
            self.say(
                "Choose where to install, or select Check only for a read-only preview.", "warning"
            )
            return
        if self.all_mode.isChecked():
            paths["scene"] = []
        if self.preview_only.isChecked():
            paths["destination"] = []
        provenance = {k: edit.property("provenance") or "user" for k, edit in self.inputs.items()}
        choices, conflicts = dict(self.product_choices), dict(self.conflict_decisions)

        def task(cancel, progress):
            inventory = index_sources(paths["source"], paths["product_root"], cancel)
            result = make_plan(
                inventory,
                paths["destination"][0] if paths["destination"] else None,
                paths["scene"],
                paths["library"],
                choices,
                conflicts,
                cancel,
            )
            for key in ("source", "library"):
                for item in result.configuration["sources" if key == "source" else "libraries"]:
                    item["provenance"] = provenance[key]
            return result, inventory

        self.go(2)
        self.start(task, self.show_plan)

    def decision(self, key, value, product=False):
        decisions = self.product_choices if product else self.conflict_decisions
        if value:
            decisions[key] = value
        else:
            decisions.pop(key, None)
        self.invalidate()
        self.say(
            "Choice saved. Select Check again to update your review before installing.", "warning"
        )

    def attention_row(self, name, reason, choices=None, callback=None):
        item = QTreeWidgetItem([name, reason, ""])
        item.setToolTip(0, name)
        item.setToolTip(1, reason)
        self.attention.addTopLevelItem(item)
        if choices:
            combo = QComboBox()
            combo.setAccessibleName(f"Choose action for {name}")
            combo.addItem("Choose an action…", None)
            for text, value in choices:
                combo.addItem(text, value)
                combo.setItemData(combo.count() - 1, text, Qt.ItemDataRole.ToolTipRole)
            combo.currentIndexChanged.connect(lambda _: callback(combo.currentData()))
            self.attention.setItemWidget(item, 2, combo)

    def show_plan(self, value):
        if isinstance(value, tuple):
            value, self.inventory = value
        self.plan = value
        self.pages.setCurrentIndex(2)
        self.title.setText("Here’s what we found.")
        self.subtitle.setText("Whole products are installed, so their related files stay together.")
        for i, button in enumerate(self.steps):
            button.setChecked(i == 2)
        self.stats[0].setText(str(len(value.products)))
        self.stats[1].setText(size_text(value.estimated_bytes))
        self.stats[2].setText(str(sum(o.action == "skip" for o in value.operations)))
        self.products_table.setRowCount(len(value.products))
        for row, product in enumerate(value.products):
            texts = (
                Path(product.source).stem,
                "ZIP package" if product.archive else "Folder",
                str(len(product.files)),
                size_text(sum(e.size for e in product.files)),
            )
            for column, text in enumerate(texts):
                item = QTableWidgetItem(text)
                item.setToolTip(product.source)
                self.products_table.setItem(row, column, item)
        self.attention.clear()
        for name in value.missing:
            self.attention_row(
                name, "Not found. Add a source folder containing this file’s product."
            )
        candidates = {p.id: p for p in self.inventory.products} if self.inventory else {}
        for name, ids in value.ambiguities.items():
            options = [(candidates[pid].source if pid in candidates else pid, pid) for pid in ids]
            self.attention_row(
                name,
                "More than one product matches. Choose which one to use.",
                options,
                lambda choice, n=name: self.decision(n, choice, True),
            )
        for op in value.operations:
            if op.action == "conflict":
                self.attention_row(
                    op.path,
                    "A different file already exists in your install library.",
                    [
                        ("Keep my existing file", "keep"),
                        ("Replace it (back up original)", "replace"),
                    ],
                    lambda choice, n=op.entry.path: self.decision(n, choice),
                )
        for report in value.reports:
            self.attention_row(
                report.removeprefix("ERROR: "),
                "Resolve this before installing."
                if report.startswith("ERROR:")
                else "Package skipped or needs review.",
            )
        count = self.attention.topLevelItemCount()
        self.tabs.setTabText(1, f"Needs attention ({count})")
        pending = sum(o.action in {"copy", "replace"} for o in value.operations)
        self.install_button.setText(f"Install {len(value.products)} product(s)")
        self.review_hint.setText(
            f"{pending} files to copy · {len(value.operations)} files reviewed"
            + (f" · Install into {value.destination}" if value.destination else " · Preview only")
        )
        if value.blocked:
            self.say(
                "Some items need your attention. Resolve the items below, then Check again.",
                "warning",
            )
            self.tabs.setCurrentIndex(1)
        elif not pending:
            self.say(
                "You’re all set. All static file references we checked are already available."
                if not value.products
                else "Everything is already installed. No files need to be copied.",
                "success",
            )
        elif not value.destination:
            self.say("Preview complete. Go Back to choose an install library when you’re ready.")
        else:
            self.say("Ready to install. Review the products below, then select Install.", "success")
        if not value.products and not value.operations and self.all_mode.isChecked():
            self.say(
                "No supported products were found. "
                "Review Needs attention or add another source folder.",
                "warning",
            )
        self.output.setPlainText(json.dumps(value.to_dict(), indent=2))
        self.refresh_actions()

    def execute(self):
        if not self.plan or self.busy or not self.install_button.isEnabled():
            return
        plan = self.plan
        self.plan = None
        self.last_destination = plan.destination
        self.start(
            lambda cancel, progress: install(plan, cancel, progress), self.show_result, "install"
        )

    def show_result(self, result):
        self.title.setText("Your content is ready.")
        self.say(
            f"Installation complete. {result['written']} files copied and verified.", "success"
        )
        self.review_hint.setText(
            "Products are in your selected library. You can now reopen your scene in DAZ Studio."
        )
        self.open_button.show()
        self.output.setPlainText(json.dumps(result, indent=2))

    def open_library(self):
        if getattr(self, "last_destination", None):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.last_destination))

    def help(self):
        QMessageBox.information(
            self,
            "A quick guide",
            "1. Add your DAZ scenes (.duf/.dsf), or choose Install all products.\n\n"
            "2. Add source folders: the ZIPs or extracted products you downloaded.\n\n"
            "3. Add libraries: folders where your DAZ content is already installed.\n\n"
            "4. Choose an install library, then Check dependencies. Checking is read-only.\n\n"
            "5. Review products and any choices. Install copies whole products, "
            "backs up replacements "
            "and verifies the files. Sources are preserved.\n\n"
            "This checks static file references. "
            "It does not run scripts or register products with DIM.",
        )

    def closeEvent(self, event):
        if self.busy:
            self.cancel()
            self.say(
                "Stopping safely. Please wait for the operation to finish, then close the window.",
                "warning",
            )
            event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = Window()
    window.show()
    if "--smoke-test" in sys.argv:
        QTimer.singleShot(300, app.quit)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
