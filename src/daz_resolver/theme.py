"""Shared Daz 3D theme tokens, palette and styles for every desktop surface."""

from pathlib import Path

from PySide6.QtGui import QColor, QPalette

TOKENS = {
    "text": "#243b43",
    "canvas": "#f3f6f5",
    "sidebar": "#173b3e",
    "sidebar_text": "#c8dcd8",
    "sidebar_muted": "#a5c6bf",
    "step": "#bed4ce",
    "step_selected": "#2c5554",
    "accent_muted": "#41756b",
    "heading": "#183c3e",
    "muted": "#62767c",
    "stat": "#184e44",
    "border": "#dce5e1",
    "notice": "#e5f0eb",
    "notice_text": "#245447",
    "warning": "#fff1d9",
    "warning_text": "#805714",
    "error": "#fce8e5",
    "error_text": "#963d36",
    "success": "#dff1e7",
    "success_text": "#215b40",
    "control_border": "#cbd9d3",
    "hover": "#eaf2ef",
    "hover_border": "#84aa9d",
    "focus": "#318978",
    "disabled_text": "#93a49e",
    "disabled": "#e9eeeb",
    "disabled_border": "#dce4df",
    "accent": "#247564",
    "accent_hover": "#195d50",
    "accent_disabled": "#b3c9c0",
    "disabled_on_accent": "#f6f9f7",
    "quiet": "#437268",
    "input_border": "#cfdbd5",
    "selection": "#d3e9df",
    "list": "#fbfdfb",
    "list_border": "#e0e8e2",
    "row_border": "#edf1ee",
    "list_selection": "#dceee5",
    "list_selection_text": "#184d3e",
    "indicator": "#819e92",
    "table_border": "#dde5df",
    "alternate": "#f8faf8",
    "table_selection": "#deeee5",
    "header": "#edf3ef",
    "header_border": "#d9e4dd",
    "header_text": "#486158",
    "tab_text": "#62776e",
    "tab_selected": "#205a4b",
    "progress_track": "#dce7df",
    "progress": "#31856e",
    "tool": "#496e60",
    "surface": "#ffffff",
    "on_accent": "#ffffff",
    "scroll_track": "#e9efec",
    "scroll_handle": "#a2b7ad",
    "scroll_hover": "#718f81",
    "step_done": "#b6ead1",
    "step_attention": "#ffe0a3",
}

STYLE_TEMPLATE = """
QWidget { font-family: 'Segoe UI'; font-size: 13px; color: @text@; }
QMainWindow, QWidget#canvas { background: @canvas@; }
QWidget#pageContent, QWidget#pageViewport { background: @canvas@; }
QFrame#sidebar { background: @sidebar@; border: none; }
QFrame#sidebar QLabel { color: @sidebar_text@; background: transparent; }
QLabel#brand { color: @surface@; font-size: 20px; font-weight: 700; }
QLabel#sidebarNote { color: @sidebar_muted@; font-size: 12px; }
QPushButton#step { text-align: left; padding: 15px 12px; color: @step@;
    border: none; background: transparent; border-radius: 8px; }
QPushButton#step:checked { background: @step_selected@; color: @surface@; font-weight: 600; }
QLabel#eyebrow { color: @accent_muted@; font-weight: 600; font-size: 11px; }
QLabel#title { font-size: 28px; font-weight: 700; color: @heading@; }
QLabel#subtitle, QLabel#muted { color: @muted@; }
QLabel#sectionTitle { font-size: 15px; font-weight: 600; }
QLabel#statValue { font-size: 25px; font-weight: 700; color: @stat@; }
QFrame#card { background: @surface@; border: 1px solid @border@; border-radius: 10px; }
QFrame#card QLabel, QFrame#card QWidget { background: transparent; }
QLabel#notice { background: @notice@; color: @notice_text@; padding: 13px; border-radius: 7px; }
QLabel#notice[tone='warning'] { background: @warning@; color: @warning_text@; }
QLabel#notice[tone='error'] { background: @error@; color: @error_text@; }
QLabel#notice[tone='success'] { background: @success@; color: @success_text@; }
QPushButton { background: @surface@; border: 1px solid @control_border@; border-radius: 7px;
    padding: 9px 15px; font-weight: 600; min-height: 18px; }
QPushButton:hover { background: @hover@; border-color: @hover_border@; }
QPushButton:focus, QComboBox:focus, QLineEdit:focus, QListWidget:focus {
    border: 2px solid @focus@; }
QPushButton:disabled { color: @disabled_text@;
background: @disabled@;
border-color: @disabled_border@;
}
QPushButton#primary { background: @accent@; border-color: @accent@; color: @on_accent@; }
QPushButton#primary:hover { background: @accent_hover@; }
QPushButton#primary:disabled { background: @accent_disabled@;
border-color: @accent_disabled@;
color: @disabled_on_accent@;
}
QPushButton#quiet { background: transparent; border: none; color: @quiet@; padding: 6px; }
QLineEdit, QComboBox { background: @surface@; border: 1px solid @input_border@; border-radius: 6px;
    padding: 9px; selection-background-color: @selection@; }
QListWidget { background: @list@; border: 1px solid @list_border@; border-radius: 6px; }
QListWidget::item { padding: 7px; border-bottom: 1px solid @row_border@; }
QListWidget::item:selected { background: @list_selection@; color: @list_selection_text@; }
QRadioButton, QCheckBox { spacing: 9px; padding: 5px 0; }
QRadioButton::indicator { width: 16px; height: 16px; border: 1px solid @indicator@;
    border-radius: 9px; background: @surface@; }
QRadioButton::indicator:checked { width: 8px; height: 8px; border: 5px solid @accent@; }
QCheckBox::indicator { width: 17px; height: 17px; border: 1px solid @indicator@;
    border-radius: 3px; background: @surface@; }
QCheckBox::indicator:checked { image: url('@CHECK@'); border-color: @accent@; }
QTableWidget, QTreeWidget, QTextEdit, QPlainTextEdit { background: @surface@;
border: 1px solid @table_border@;
    border-radius: 6px; alternate-background-color: @alternate@;
    selection-background-color: @table_selection@; selection-color: @heading@; }
QHeaderView::section { background: @header@; border: none;
    border-bottom: 1px solid @header_border@;
padding: 10px;
font-weight: 600;
color: @header_text@;
}
QTreeWidget::item { padding: 9px 4px; }
QTabWidget::pane { border: none; padding-top: 10px; }
QTabBar::tab { background: transparent; padding: 10px 15px; color: @tab_text@;
    border-bottom: 2px solid transparent; }
QTabBar::tab:selected { border-bottom: 2px solid @accent@;
color: @tab_selected@;
font-weight: 600;
}
QProgressBar { border: none; background: @progress_track@; border-radius: 4px; height: 8px; }
QProgressBar::chunk { background: @progress@; border-radius: 4px; }
QToolButton { border: none; color: @tool@; padding: 8px 0; }
QScrollArea { border: none; background: transparent; }
QToolTip { background: @sidebar@; color: @surface@; padding: 5px; border: none; }

QDialog, QMessageBox, QInputDialog { background: @surface@; color: @text@; }
QDialog QLabel, QMessageBox QLabel, QInputDialog QLabel { color: @text@; background: transparent; }
QMenu { background: @surface@; color: @text@; border: 1px solid @border@; }
QMenu::item:selected { background: @selection@; color: @text@; }
QComboBox QAbstractItemView { background: @surface@; color: @text@;
    selection-background-color: @selection@; selection-color: @text@; }
QScrollBar:vertical { background: @scroll_track@; width: 12px; margin: 0; border: none; }
QScrollBar:horizontal { background: @scroll_track@; height: 12px; margin: 0; border: none; }
QScrollBar::handle:vertical { background: @scroll_handle@; min-height: 30px; border-radius: 5px; }
QScrollBar::handle:horizontal { background: @scroll_handle@; min-width: 30px; border-radius: 5px; }
QScrollBar::handle:hover { background: @scroll_hover@; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; border: none; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QAbstractScrollArea::corner { background: @scroll_track@; border: none; }
QPushButton#step[state='done'] { color: @step_done@; }
QPushButton#step[state='attention'] { color: @step_attention@; }
QPushButton#step[state='running'] { color: @surface@; }
"""


def application_style():
    style = STYLE_TEMPLATE
    for name, color in TOKENS.items():
        style = style.replace(f"@{name}@", color)
    return style.replace("@CHECK@", (Path(__file__).parent / "assets/check.svg").as_posix())


def light_palette():
    palette = QPalette()
    for role, color in (
        (QPalette.ColorRole.Window, TOKENS["canvas"]),
        (QPalette.ColorRole.Base, TOKENS["surface"]),
        (QPalette.ColorRole.AlternateBase, TOKENS["alternate"]),
        (QPalette.ColorRole.WindowText, TOKENS["text"]),
        (QPalette.ColorRole.Text, TOKENS["text"]),
        (QPalette.ColorRole.Button, TOKENS["surface"]),
        (QPalette.ColorRole.ButtonText, TOKENS["text"]),
        (QPalette.ColorRole.ToolTipBase, TOKENS["sidebar"]),
        (QPalette.ColorRole.ToolTipText, TOKENS["surface"]),
        (QPalette.ColorRole.PlaceholderText, TOKENS["muted"]),
        (QPalette.ColorRole.Highlight, TOKENS["selection"]),
        (QPalette.ColorRole.HighlightedText, TOKENS["text"]),
    ):
        palette.setColor(role, QColor(color))
    for role in (
        QPalette.ColorRole.Text,
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.ButtonText,
    ):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(TOKENS["disabled_text"]))
    return palette


def apply_theme(app):
    app.setStyle("Fusion")
    app.setPalette(light_palette())
    app.setStyleSheet(application_style())
