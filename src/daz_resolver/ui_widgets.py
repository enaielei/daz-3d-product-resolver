"""Reusable controls and a calm, high-contrast desktop theme."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

STYLE = """
QWidget { font-family: 'Segoe UI'; font-size: 13px; color: #243b43; }
QMainWindow, QWidget#canvas { background: #f3f6f5; }
QFrame#sidebar { background: #173b3e; border: none; }
QFrame#sidebar QLabel { color: #c8dcd8; background: transparent; }
QLabel#brand { color: white; font-size: 20px; font-weight: 700; }
QLabel#sidebarNote { color: #a5c6bf; font-size: 12px; }
QPushButton#step { text-align: left; padding: 15px 12px; color: #bed4ce;
    border: none; background: transparent; border-radius: 8px; }
QPushButton#step:checked { background: #2c5554; color: white; font-weight: 600; }
QLabel#eyebrow { color: #41756b; font-weight: 600; font-size: 11px; }
QLabel#title { font-size: 28px; font-weight: 700; color: #183c3e; }
QLabel#subtitle, QLabel#muted { color: #62767c; }
QLabel#sectionTitle { font-size: 15px; font-weight: 600; }
QLabel#statValue { font-size: 25px; font-weight: 700; color: #184e44; }
QFrame#card { background: white; border: 1px solid #dce5e1; border-radius: 10px; }
QFrame#card QLabel, QFrame#card QWidget { background: transparent; }
QLabel#notice { background: #e5f0eb; color: #245447; padding: 13px; border-radius: 7px; }
QLabel#notice[tone='warning'] { background: #fff1d9; color: #805714; }
QLabel#notice[tone='error'] { background: #fce8e5; color: #963d36; }
QLabel#notice[tone='success'] { background: #dff1e7; color: #215b40; }
QPushButton { background: white; border: 1px solid #cbd9d3; border-radius: 7px;
    padding: 9px 15px; font-weight: 600; min-height: 18px; }
QPushButton:hover { background: #eaf2ef; border-color: #84aa9d; }
QPushButton:focus, QComboBox:focus, QLineEdit:focus, QListWidget:focus {
    border: 2px solid #318978; }
QPushButton:disabled { color: #93a49e; background: #e9eeeb; border-color: #dce4df; }
QPushButton#primary { background: #247564; border-color: #247564; color: white; }
QPushButton#primary:hover { background: #195d50; }
QPushButton#primary:disabled { background: #b3c9c0; border-color: #b3c9c0; color: #f6f9f7; }
QPushButton#quiet { background: transparent; border: none; color: #437268; padding: 6px; }
QLineEdit, QComboBox { background: white; border: 1px solid #cfdbd5; border-radius: 6px;
    padding: 9px; selection-background-color: #d3e9df; }
QListWidget { background: #fbfdfb; border: 1px solid #e0e8e2; border-radius: 6px; }
QListWidget::item { padding: 7px; border-bottom: 1px solid #edf1ee; }
QListWidget::item:selected { background: #dceee5; color: #184d3e; }
QRadioButton, QCheckBox { spacing: 9px; padding: 5px 0; }
QRadioButton::indicator, QCheckBox::indicator { width: 17px; height: 17px; }
QTableWidget, QTreeWidget, QTextEdit { background: white; border: 1px solid #dde5df;
    border-radius: 6px; alternate-background-color: #f8faf8;
    selection-background-color: #deeee5; selection-color: #183c3e; }
QHeaderView::section { background: #edf3ef; border: none;
    border-bottom: 1px solid #d9e4dd; padding: 10px; font-weight: 600; color: #486158; }
QTreeWidget::item { padding: 9px 4px; }
QTabWidget::pane { border: none; padding-top: 10px; }
QTabBar::tab { background: transparent; padding: 10px 15px; color: #62776e;
    border-bottom: 2px solid transparent; }
QTabBar::tab:selected { border-bottom: 2px solid #247564; color: #205a4b; font-weight: 600; }
QProgressBar { border: none; background: #dce7df; border-radius: 4px; height: 8px; }
QProgressBar::chunk { background: #31856e; border-radius: 4px; }
QToolButton { border: none; color: #496e60; padding: 8px 0; }
QScrollArea { border: none; background: transparent; }
QToolTip { background: #173b3e; color: white; padding: 5px; border: none; }
"""


def light_palette():
    palette = QPalette()
    for role, color in (
        (QPalette.ColorRole.Window, "#f3f6f5"),
        (QPalette.ColorRole.Base, "#ffffff"),
        (QPalette.ColorRole.WindowText, "#243b43"),
        (QPalette.ColorRole.Text, "#243b43"),
        (QPalette.ColorRole.Button, "#ffffff"),
        (QPalette.ColorRole.ButtonText, "#243b43"),
        (QPalette.ColorRole.Highlight, "#dceee5"),
        (QPalette.ColorRole.HighlightedText, "#184d3e"),
    ):
        palette.setColor(role, QColor(color))
    return palette


def label(text, name=""):
    widget = QLabel(text)
    widget.setObjectName(name)
    widget.setWordWrap(True)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    return widget


def card(title="", description=""):
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(20, 17, 20, 17)
    layout.setSpacing(10)
    if title:
        layout.addWidget(label(title, "sectionTitle"))
    if description:
        layout.addWidget(label(description, "muted"))
    return frame, layout


def size_text(size):
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024


class PathPicker(QWidget):
    """Native path lists; separator syntax is an internal compatibility interface only."""

    textChanged = Signal(str)

    def __init__(self, kind, name):
        super().__init__()
        self.kind = kind
        self.setAcceptDrops(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.list = QListWidget()
        self.list.setAccessibleName(name)
        self.list.setMaximumHeight(94)
        self.list.setMinimumHeight(67)
        self.list.setToolTip("You can also drag files or folders here.")
        layout.addWidget(self.list)
        row = QHBoxLayout()
        self.add_button = QPushButton("Add scene files…" if kind == "scene" else "Add folder…")
        self.add_button.clicked.connect(self.browse)
        row.addWidget(self.add_button)
        manual = QPushButton("Enter path…")
        manual.setObjectName("quiet")
        manual.clicked.connect(self.enter_path)
        row.addWidget(manual)
        row.addStretch()
        remove = QPushButton("Remove")
        remove.setObjectName("quiet")
        remove.clicked.connect(self.remove)
        row.addWidget(remove)
        layout.addLayout(row)

    def paths(self):
        return [Path(self.list.item(i).text()) for i in range(self.list.count())]

    def text(self):
        return " | ".join(map(str, self.paths()))

    def setText(self, value):
        self.set_paths([Path(p.strip()) for p in value.split("|") if p.strip()])

    def set_paths(self, paths):
        self.list.clear()
        for path in dict.fromkeys(map(str, paths)):
            self.list.addItem(path)
            self.list.item(self.list.count() - 1).setToolTip(path)
        self.textChanged.emit(self.text())

    def add_paths(self, paths):
        self.set_paths([*self.paths(), *paths])

    def remove(self):
        for item in self.list.selectedItems():
            self.list.takeItem(self.list.row(item))
        self.textChanged.emit(self.text())

    def browse(self):
        if self.kind == "scene":
            values, _ = QFileDialog.getOpenFileNames(
                self, "Choose your DAZ scene or preset", "", "DAZ files (*.duf *.dsf)"
            )
        else:
            value = QFileDialog.getExistingDirectory(self, "Choose a folder")
            values = [value] if value else []
        if values:
            self.add_paths([Path(v) for v in values])

    def enter_path(self):
        value, ok = QInputDialog.getText(self, "Add a path", "File or folder path:")
        if ok and value.strip():
            self.add_paths([Path(value.strip().strip('"'))])

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        if self.kind == "scene":
            paths = [p for p in paths if p.is_file() and p.suffix.lower() in {".duf", ".dsf"}]
        else:
            paths = [p for p in paths if p.is_dir()]
        self.add_paths(paths)
        event.acceptProposedAction()
