"""
Тёмная тема приложения. Мягкий тёмно-серый (не чёрный), читаемый текст.
apply_theme(app, dark) — переключение; LIGHT = пустой QSS (стандартный вид).
"""

LIGHT_QSS = ""

DARK_QSS = """
* {
    color: #e6e8ec;
    selection-background-color: #3b82f6;
    selection-color: #ffffff;
}

QMainWindow, QWidget, QDialog {
    background-color: #2b2d33;
}

QLabel {
    background: transparent;
    color: #cfd3da;
}

/* Заголовки секций (жирные QLabel) и обычный текст одинаково читаемы */

QPushButton {
    background-color: #3a3e46;
    color: #e6e8ec;
    border: 1px solid #4a4f59;
    border-radius: 4px;
    padding: 5px 10px;
}
QPushButton:hover  { background-color: #454a54; border-color: #5a606b; }
QPushButton:pressed { background-color: #2f333a; }
QPushButton:checked { background-color: #3b5bdb; border-color: #4c6ef5; color: #ffffff; }
QPushButton:disabled { background-color: #303338; color: #6b7079; border-color: #3a3e46; }

QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #24262b;
    color: #e6e8ec;
    border: 1px solid #444852;
    border-radius: 4px;
    padding: 3px 5px;
    selection-background-color: #3b82f6;
    selection-color: #ffffff;
}
QPlainTextEdit, QTextEdit { padding: 4px; }
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #4c6ef5;
}

QComboBox QAbstractItemView {
    background-color: #2f323a;
    color: #e6e8ec;
    border: 1px solid #444852;
    selection-background-color: #3b5bdb;
    selection-color: #ffffff;
}
QComboBox::drop-down { border: none; width: 18px; }

/* Списки и деревья */
QListWidget, QTreeWidget, QTreeView, QListView {
    background-color: #24262b;
    color: #e6e8ec;
    border: 1px solid #3a3e46;
    border-radius: 4px;
    outline: none;
}
QListWidget::item, QTreeWidget::item { padding: 2px 4px; }
QListWidget::item:selected, QTreeWidget::item:selected,
QTreeView::item:selected, QListView::item:selected {
    background-color: #3b5bdb;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #32353c;
    color: #cfd3da;
    border: 1px solid #3a3e46;
    padding: 3px;
}

QCheckBox { background: transparent; color: #e6e8ec; spacing: 6px; }
QCheckBox::indicator {
    width: 15px; height: 15px;
    border: 1px solid #5a606b; border-radius: 3px; background: #24262b;
}
QCheckBox::indicator:checked { background: #4c6ef5; border-color: #4c6ef5; }

/* Меню */
QMenu {
    background-color: #2f323a;
    color: #e6e8ec;
    border: 1px solid #444852;
}
QMenu::item:selected { background-color: #3b5bdb; color: #ffffff; }
QMenu::separator { height: 1px; background: #444852; margin: 4px 6px; }

/* Сплиттер */
QSplitter::handle { background-color: #3a3e46; }
QSplitter::handle:hover { background-color: #4c6ef5; }

/* Скроллбары */
QScrollBar:vertical {
    background: #24262b; width: 12px; margin: 0;
}
QScrollBar::handle:vertical {
    background: #4a4f59; min-height: 24px; border-radius: 6px;
}
QScrollBar::handle:vertical:hover { background: #5a606b; }
QScrollBar:horizontal {
    background: #24262b; height: 12px; margin: 0;
}
QScrollBar::handle:horizontal {
    background: #4a4f59; min-width: 24px; border-radius: 6px;
}
QScrollBar::handle:horizontal:hover { background: #5a606b; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }

QToolTip {
    background-color: #32353c;
    color: #e6e8ec;
    border: 1px solid #4c6ef5;
}

QTabBar::tab {
    background: #32353c; color: #cfd3da;
    padding: 5px 10px; border: 1px solid #3a3e46;
}
QTabBar::tab:selected { background: #3b5bdb; color: #ffffff; }
"""


def apply_theme(app, dark):
    """Применить тему к QApplication. dark=True — тёмная, иначе светлая (стандартная)."""
    app.setStyleSheet(DARK_QSS if dark else LIGHT_QSS)
