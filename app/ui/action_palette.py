from PyQt5.QtCore import pyqtSignal, Qt, QMimeData
from PyQt5.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QAbstractItemView,
    QWidget, QVBoxLayout, QLineEdit
)


MIME_ACTION_TYPE = "application/x-rpa-action-type"


# Какое действие в какую группу попадает
# Какое действие в какую группу попадает
ACTION_GROUPS = [
    ("Основное", [
        "wait", "type_text", "paste_text", "press_key", "run_program", "cmd",
        "python_eval", "ask_yesno", "set_variable", "wait_window_gone", "log_message",
        "separator",
    ]),
    ("Мышь и координаты", [
        "click_xy"
    ]),
    ("Изображения", [
        "wait_image", "click_image", "click_image_in_window",
        "wait_image_gone", "screenshot", "ocr_region",
    ]),
    ("Окна и элементы", [
        "find_window", "window_focus", "window_click_xy", "window_click_element",
        "read_element",
        "window_state", "window_move", "window_resize",
        "window_move_resize", "window_send_message",
    ]),
    ("Управление потоком", [
        "if_start", "else", "end_if",
        "for_each_start", "end_for",
        "while_start", "end_while",
        "repeat_start", "end_repeat",
        "try_start", "catch", "end_try",
        "break", "continue",
        "run_scenario",
    ]),
    ("Базы данных", [
        "sql", "sql_many"
    ]),
    ("Проверки (условия)", [
        "check_image", "check_process", "check_window", "check_file"
    ]),
    ("Процессы и службы", [
        "kill_process", "start_service", "stop_service"
    ]),
    ("Файлы", [
        "copy_file", "move_file", "delete_file",
        "find_files", "set_file_attr", "check_file"
    ]),
    ("Архивы", [
        "add_to_archive", "extract_archive"
    ]),
    ("Специальные", [
        "uni_stat_2003"
    ]),
]


class ActionPaletteTree(QTreeWidget):
    actionChosen = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragOnly)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setStyleSheet(
            "QTreeWidget { font-size: 12px; }"
            "QTreeWidget::item { padding: 3px 4px; }"
            "QTreeWidget::item:hover { background: #e0e7ff; }"
        )

        self.itemDoubleClicked.connect(self._on_double_click)
        self._saved_expanded = None   # состояние групп до начала поиска
        self._populate()

    def _populate(self):
        from app.actions.registry import ACTION_REGISTRY

        # Создаём индекс — какие действия уже распределены по группам
        grouped = set()
        for _, types in ACTION_GROUPS:
            grouped.update(types)

        for group_name, types in ACTION_GROUPS:
            group_item = QTreeWidgetItem(self, [group_name])
            group_item.setFlags(Qt.ItemIsEnabled)
            font = group_item.font(0)
            font.setBold(True)
            group_item.setFont(0, font)
            group_item.setExpanded(True)

            for action_type in types:
                if action_type not in ACTION_REGISTRY:
                    continue
                cls  = ACTION_REGISTRY[action_type][0]
                icon = getattr(cls, "icon", "•")
                leaf = QTreeWidgetItem(group_item, [f"{icon}  {cls.name}"])
                leaf.setData(0, Qt.UserRole, action_type)
                leaf.setFlags(
                    Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled
                )

        # Прочие — действия, которые забыли распределить
        misc = [t for t in ACTION_REGISTRY.keys() if t not in grouped]
        if misc:
            group_item = QTreeWidgetItem(self, ["Прочее"])
            group_item.setFlags(Qt.ItemIsEnabled)
            font = group_item.font(0); font.setBold(True); group_item.setFont(0, font)
            group_item.setExpanded(True)
            for action_type in misc:
                cls  = ACTION_REGISTRY[action_type][0]
                icon = getattr(cls, "icon", "•")
                leaf = QTreeWidgetItem(group_item, [f"{icon}  {cls.name}"])
                leaf.setData(0, Qt.UserRole, action_type)
                leaf.setFlags(
                    Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled
                )

    def _on_double_click(self, item):
        action_type = item.data(0, Qt.UserRole)
        if action_type:
            self.actionChosen.emit(action_type)

    def mimeData(self, items):
        m = QMimeData()
        if items:
            action_type = items[0].data(0, Qt.UserRole)
            if action_type:
                m.setData(MIME_ACTION_TYPE, action_type.encode("utf-8"))
                m.setText(action_type)
        return m

    def filter_text(self, text):
        """Фильтрация: показать только листья, чей текст содержит подстроку."""
        needle = (text or "").lower().strip()

        # Запоминаем состояние групп один раз — при старте поиска
        if needle and self._saved_expanded is None:
            self._saved_expanded = {
                i: self.topLevelItem(i).isExpanded()
                for i in range(self.topLevelItemCount())
            }

        for i in range(self.topLevelItemCount()):
            group = self.topLevelItem(i)
            any_visible = False
            for j in range(group.childCount()):
                leaf = group.child(j)
                visible = (needle == "") or (needle in leaf.text(0).lower())
                leaf.setHidden(not visible)
                any_visible |= visible
            group.setHidden(not any_visible)
            if needle:
                group.setExpanded(any_visible)

        # Поиск очищен — возвращаем группы в прежнее состояние
        if not needle:
            if self._saved_expanded is not None:
                for i in range(self.topLevelItemCount()):
                    self.topLevelItem(i).setExpanded(
                        self._saved_expanded.get(i, True)
                    )
                self._saved_expanded = None
            else:
                for i in range(self.topLevelItemCount()):
                    self.topLevelItem(i).setExpanded(True)


class ActionPalette(QWidget):
    """
    Палитра: дерево групп + поле поиска снизу.
    actionChosen(type) — двойной клик
    """
    actionChosen = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.tree = ActionPaletteTree()
        self.tree.actionChosen.connect(self.actionChosen.emit)
        layout.addWidget(self.tree, 1)

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 Поиск действия…")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.tree.filter_text)
        layout.addWidget(self.search)