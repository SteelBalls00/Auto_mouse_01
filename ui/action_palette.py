from PyQt5.QtCore import pyqtSignal, QSize, Qt, QMimeData
from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QAbstractItemView


MIME_ACTION_TYPE = "application/x-rpa-action-type"


class ActionPalette(QListWidget):
    """
    Палитра доступных действий.
    - Двойной клик — добавляет действие в сценарий
    - Drag — перетаскивание в список шагов вставит действие
    """
    actionChosen = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setIconSize(QSize(20, 20))
        self.setUniformItemSizes(True)
        self.setSpacing(2)
        self.setStyleSheet(
            "QListWidget { font-size: 12px; }"
            "QListWidget::item { padding: 6px 8px; }"
            "QListWidget::item:hover { background: #e0e7ff; }"
        )

        # Drag & Drop — только источник
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragOnly)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

        self.itemDoubleClicked.connect(self._on_double_click)

        self._populate()

    def _populate(self):
        from actions.registry import ACTION_REGISTRY
        for action_type, (cls, _) in ACTION_REGISTRY.items():
            icon = getattr(cls, "icon", "•")
            item = QListWidgetItem(f"{icon}  {cls.name}")
            item.setData(Qt.UserRole, action_type)
            self.addItem(item)

    def _on_double_click(self, item):
        action_type = item.data(Qt.UserRole)
        if action_type:
            self.actionChosen.emit(action_type)

    def mimeData(self, items):
        m = QMimeData()
        if items:
            action_type = items[0].data(Qt.UserRole)
            if action_type:
                m.setData(MIME_ACTION_TYPE, action_type.encode("utf-8"))
                m.setText(action_type)
        return m