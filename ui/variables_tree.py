from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QAbstractItemView


class VariablesTree(QTreeWidget):
    """
    Дерево переменных, экспортируемых шагами сценария.
    Корни — шаги (например '3. find_case'), листья — имена колонок.
    Перетаскивание листа в QLineEdit / QPlainTextEdit вставляет
    строку вида '{find_case.ID}'.
    """

    def __init__(self):
        super().__init__()
        self.setHeaderLabel("Переменные")
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragOnly)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    def mimeData(self, items):
        m = QMimeData()
        if not items:
            return m
        item = items[0]
        # только листья (колонки)
        if item.parent() is None:
            return m
        namespace = item.parent().data(0, Qt.UserRole)
        column    = item.text(0)
        m.setText(f"{{{namespace}.{column}}}")
        return m

    def rebuild(self, actions):
        """
        Перестраивает дерево из списка ActionModel.
        Использует action.output_vars() для определения namespace + колонок.
        """
        self.clear()
        from actions.registry import ACTION_REGISTRY

        for i, model in enumerate(actions):
            cls = ACTION_REGISTRY[model.action_type][0]
            action = cls(model.params)
            out = action.output_vars()
            if not out:
                continue
            namespace, columns = out

            root = QTreeWidgetItem(self)
            root.setText(0, f"{i + 1}. {namespace}")
            root.setData(0, Qt.UserRole, namespace)
            root.setFlags(Qt.ItemIsEnabled)  # корень не таскается

            for col in columns:
                leaf = QTreeWidgetItem(root)
                leaf.setText(0, col)
                leaf.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)

            root.setExpanded(True)