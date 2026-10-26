"""Reusable controls and a calm, high-contrast desktop theme."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


def label(text, name=""):
    widget = QLabel(text)
    widget.setObjectName(name)
    widget.setWordWrap(True)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    return widget


class PageScrollArea(QScrollArea):
    """Pixel scrolling with predictable wheel distance instead of layout-sized jumps."""

    def wheelEvent(self, event):
        bar = self.verticalScrollBar()
        delta = event.pixelDelta().y() or round(event.angleDelta().y() / 120 * 48)
        if delta and bar.maximum() > bar.minimum():
            bar.setValue(bar.value() - delta)
            event.accept()
        else:
            super().wheelEvent(event)


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
        self.list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list.verticalScrollBar().setSingleStep(24)
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
                self, "Choose your Daz 3D scene or preset", "", "Daz 3D files (*.duf *.dsf)"
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
