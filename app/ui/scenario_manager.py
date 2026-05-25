import os
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem,
    QMenu, QAbstractItemView
)
from PyQt5.QtGui import QColor

from app.scenario import recent


class ScenarioManager(QWidget):
    """
    Панель управления сценариями: Избранное + Недавние.
    Сигнал openRequested(path) — двойной клик / меню «Открыть».
    """
    openRequested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        layout.addWidget(QLabel("Сценарии"))

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._context_menu)
        self.tree.itemDoubleClicked.connect(self._on_double_click)
        self.tree.setStyleSheet(
            "QTreeWidget { font-size: 12px; }"
            "QTreeWidget::item { padding: 3px 2px; }"
            "QTreeWidget::item:hover { background: #e0e7ff; }"
        )
        layout.addWidget(self.tree, 1)

        self.refresh()

    def refresh(self):
        self.tree.clear()

        # Избранное
        fav_root = QTreeWidgetItem(self.tree, ["★ Избранное"])
        fav_root.setFlags(Qt.ItemIsEnabled)
        f = fav_root.font(0); f.setBold(True); fav_root.setFont(0, f)
        fav_root.setExpanded(True)
        for path in recent.get_favorites():
            self._add_leaf(fav_root, path, fav=True)

        # Недавние
        rec_root = QTreeWidgetItem(self.tree, ["🕘 Недавние"])
        rec_root.setFlags(Qt.ItemIsEnabled)
        f = rec_root.font(0); f.setBold(True); rec_root.setFont(0, f)
        rec_root.setExpanded(True)
        favs = set(os.path.abspath(p) for p in recent.get_favorites())
        for path in recent.get_recent():
            if os.path.abspath(path) in favs:
                continue   # не дублируем избранные в недавних
            self._add_leaf(rec_root, path, fav=False)

    def _add_leaf(self, parent, path, fav):
        # Имя сценария = имя папки, где лежит scenario.json
        name = os.path.basename(os.path.dirname(path)) or os.path.basename(path)
        item = QTreeWidgetItem(parent, [("★ " if fav else "") + name])
        item.setData(0, Qt.UserRole, path)
        item.setToolTip(0, path)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

    def _on_double_click(self, item, column):
        path = item.data(0, Qt.UserRole)
        if path:
            self.openRequested.emit(path)

    def _context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if item is None:
            return
        path = item.data(0, Qt.UserRole)
        if not path:
            return

        menu = QMenu(self)
        act_open = menu.addAction("📂 Открыть")
        if recent.is_favorite(path):
            act_fav = menu.addAction("★ Убрать из избранного")
        else:
            act_fav = menu.addAction("☆ В избранное")
        menu.addSeparator()
        act_remove = menu.addAction("✕ Убрать из списка")

        chosen = menu.exec_(self.tree.mapToGlobal(pos))
        if chosen is act_open:
            self.openRequested.emit(path)
        elif chosen is act_fav:
            recent.toggle_favorite(path)
            self.refresh()
        elif chosen is act_remove:
            recent.remove_recent(path)
            self.refresh()

    def note_opened(self, path):
        """Вызвать после открытия/сохранения сценария."""
        recent.add_recent(path)
        self.refresh()