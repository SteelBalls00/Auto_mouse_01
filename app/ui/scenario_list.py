from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QListWidget, QAbstractItemView

from app.ui.action_palette import MIME_ACTION_TYPE


class ScenarioList(QListWidget):
    """
    Список шагов сценария.
    - Принимает drop действий из палитры (новый шаг)
    - Принимает internal-move — переставляет шаги местами
    Сигналы:
      actionDropped(action_type, insert_at)
      stepMoved(from_index, to_index)
    """
    actionDropped = pyqtSignal(str, int)
    stepMoved     = pyqtSignal(int, int)
    contextRequested = pyqtSignal(int, "QPoint")

    def __init__(self):
        super().__init__()
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setAcceptDrops(True)
        # Источник drag (наш список) И приёмник drop (палитра + наш список)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        # CopyAction — чтобы Qt НЕ удалял исходный элемент. Реальное перемещение
        # делает модель через сигнал stepMoved → MainWindow._on_step_moved.
        self.setDefaultDropAction(Qt.CopyAction)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context)

    def _on_context(self, pos):
        item = self.itemAt(pos)
        if item is None:
            return
        row = self.row(item)
        self.contextRequested.emit(row, self.mapToGlobal(pos))

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        md = event.mimeData()

        # 1) Из палитры — новое действие
        if md.hasFormat(MIME_ACTION_TYPE):
            action_type = bytes(md.data(MIME_ACTION_TYPE)).decode("utf-8")
            insert_at = self._calc_insert_index(event.pos())
            self.actionDropped.emit(action_type, insert_at)
            event.acceptProposedAction()
            return

        # 2) Внутреннее перемещение — все правки делает модель,
        #    Qt-вью при CopyAction исходный элемент не удаляет.
        if event.source() is self:
            from_index = self.currentRow()
            to_index = self._calc_insert_index(event.pos())
            if to_index > from_index:
                to_index -= 1
            if from_index != to_index and from_index >= 0:
                self.stepMoved.emit(from_index, to_index)
            # НЕ вызываем event.acceptProposedAction() — иначе Qt
            # попытается ещё и сам что-то скопировать
            event.ignore()
            return

        super().dropEvent(event)

    def _calc_insert_index(self, pos):
        target = self.itemAt(pos)
        if target is None:
            return self.count()
        row  = self.row(target)
        rect = self.visualItemRect(target)
        return row if pos.y() < rect.center().y() else row + 1