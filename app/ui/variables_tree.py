from PyQt5.QtCore import Qt, QMimeData, QEvent
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QAbstractItemView, QToolTip


_DRAG_ROLE = Qt.UserRole


class VariablesTree(QTreeWidget):
    def __init__(self):
        super().__init__()
        self.setHeaderLabel("Переменные")
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragOnly)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self._context_provider = None

    def set_context_provider(self, provider):
        """provider() → словарь живого контекста (для всплывающих подсказок)."""
        self._context_provider = provider

    def viewportEvent(self, event):
        if event.type() == QEvent.ToolTip and self._context_provider:
            item = self.itemAt(event.pos())
            drag = item.data(0, _DRAG_ROLE) if item else None
            if drag:
                from app.ui.var_inspector import resolve_path, format_compact
                try:
                    ctx = self._context_provider() or {}
                    found, value = resolve_path(ctx, drag)
                except Exception:
                    found = False
                if found:
                    QToolTip.showText(event.globalPos(), format_compact(value), self)
                    return True
                else:
                    QToolTip.showText(event.globalPos(),
                                      "нет значения (сценарий не запускался "
                                      "или переменная ещё не заполнена)", self)
                    return True
        return super().viewportEvent(event)

    def mimeData(self, items):
        m = QMimeData()
        if items:
            drag = items[0].data(0, _DRAG_ROLE)
            if drag:
                m.setText(drag)
        return m

    def _add_node(self, parent, node):
        item = QTreeWidgetItem(parent)
        item.setText(0, node.get("label", ""))
        drag = node.get("drag")
        if drag:
            item.setData(0, _DRAG_ROLE, drag)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)
        else:
            item.setFlags(Qt.ItemIsEnabled)
        for child in node.get("children", []) or []:
            self._add_node(item, child)
        return item

    def rebuild(self, actions):
        self.clear()
        from app.actions.registry import ACTION_REGISTRY

        for i, model in enumerate(actions):
            cls    = ACTION_REGISTRY[model.action_type][0]
            action = cls(model.params)
            node   = action.output_vars()
            if not node:
                continue
            wrapped = dict(node)
            wrapped["label"] = f"{i + 1}. {node.get('label', '')}"
            top = self._add_node(self.invisibleRootItem(), wrapped)
            top.setExpanded(True)
            # Также раскрыть подузел current если есть
            for k in range(top.childCount()):
                child = top.child(k)
                if child.text(0) == "current":
                    child.setExpanded(True)