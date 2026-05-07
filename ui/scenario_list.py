from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QListWidget, QAbstractItemView

from ui.action_palette import MIME_ACTION_TYPE


class ScenarioList(QListWidget):
    """
    Список шагов сценария.
    Принимает drop действий из палитры.
    Сигнал actionDropped(action_type, insert_at) — добавить шаг по индексу.
    """
    actionDropped = pyqtSignal(str, int)

    def __init__(self):
        super().__init__()
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DropOnly)
        self.setDefaultDropAction(Qt.CopyAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(MIME_ACTION_TYPE):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(MIME_ACTION_TYPE):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        md = event.mimeData()
        if not md.hasFormat(MIME_ACTION_TYPE):
            super().dropEvent(event)
            return

        action_type = bytes(md.data(MIME_ACTION_TYPE)).decode("utf-8")

        # Куда вставлять — определяем по позиции drop
        pos    = event.pos()
        target = self.itemAt(pos)
        if target is None:
            insert_at = self.count()         # бросили в пустое место → в конец
        else:
            row  = self.row(target)
            rect = self.visualItemRect(target)
            # верхняя половина строки — ВСТАВИТЬ ПЕРЕД ней
            # нижняя половина — ВСТАВИТЬ ПОСЛЕ неё
            insert_at = row if pos.y() < rect.center().y() else row + 1

        self.actionDropped.emit(action_type, insert_at)
        event.acceptProposedAction()