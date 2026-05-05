from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QListWidget,
    QPushButton, QLabel, QTextEdit,
    QVBoxLayout, QHBoxLayout, QMessageBox,
    QComboBox, QFileDialog
)

from models.action_model import ActionModel
from actions.registry import ACTION_REGISTRY
from ui.action_editor import ActionEditor
from scenario.runner import ScenarioRunner
from ui.dialogs import AddActionDialog
from scenario.io import save_scenario, load_scenario

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Python RPA (PyQt5)")
        self.resize(900, 500)

        self.actions = []
        self.current_index = None

        self.list = QListWidget()
        self.editor = ActionEditor()
        self.log = QTextEdit()
        self.log.setReadOnly(True)

        self.list.currentRowChanged.connect(self.on_select)

        btn_add = QPushButton("➕ Добавить")
        btn_del = QPushButton("❌ Удалить")
        btn_run = QPushButton("▶ Запуск")
        btn_save = QPushButton("💾 Сохранить")
        btn_load = QPushButton("📂 Открыть")


        btn_add.clicked.connect(self.add_action)
        btn_del.clicked.connect(self.delete_action)
        btn_run.clicked.connect(self.run_scenario)
        btn_save.clicked.connect(self.save_scenario)
        btn_load.clicked.connect(self.load_scenario)

        left = QVBoxLayout()
        left.addWidget(QLabel("Шаги сценария"))
        left.addWidget(self.list)
        left.addWidget(btn_add)
        left.addWidget(btn_del)
        left.addWidget(btn_save)
        left.addWidget(btn_load)

        right = QVBoxLayout()
        right.addWidget(QLabel("Параметры"))
        right.addWidget(self.editor)
        right.addWidget(QLabel("Лог"))
        right.addWidget(self.log)

        root = QHBoxLayout()
        root.addLayout(left, 2)
        root.addLayout(right, 3)

        bottom = QHBoxLayout()
        bottom.addWidget(btn_run)

        main = QVBoxLayout()
        main.addLayout(root)
        main.addLayout(bottom)

        container = QWidget()
        container.setLayout(main)
        self.setCentralWidget(container)

    def load_scenario(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть сценарий",
            "",
            "JSON (*.json)"
        )
        if not path:
            return

        name, actions = load_scenario(path)

        self.actions = actions
        self.list.clear()

        for a in self.actions:
            self.list.addItem(a.title())

        if self.actions:
            self.list.setCurrentRow(0)

    def save_scenario(self):
        self.editor.apply()

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить сценарий",
            "",
            "JSON (*.json)"
        )
        if not path:
            return

        save_scenario(path, self.actions)

    def add_action(self):
        dlg = AddActionDialog(self)
        if dlg.exec_() != dlg.Accepted:
            return

        action_type = dlg.selected_action()
        params = ACTION_REGISTRY[action_type][1].copy()

        model = ActionModel(action_type, params)
        self.actions.append(model)
        self.list.addItem(model.title())

        row = self.list.count() - 1
        self.list.setCurrentRow(row)
        self.editor.load_action(model)

        # автоматически выделяем добавленный шаг
        row = self.list.count() - 1
        self.list.setCurrentRow(row)
        self.editor.load_action(model)

    def delete_action(self):
        row = self.list.currentRow()
        if row < 0:
            return

        self.actions.pop(row)
        self.list.takeItem(row)

        # выбираем следующий разумный элемент
        if self.actions:
            new_row = min(row, len(self.actions) - 1)
            self.list.setCurrentRow(new_row)
        else:
            self.editor.load_action(None)

    def on_select(self, row):
        # 1. сохранить изменения предыдущего действия
        if self.current_index is not None and 0 <= self.current_index < len(self.actions):
            self.editor.apply()

        # 2. загрузить новое
        if 0 <= row < len(self.actions):
            self.editor.load_action(self.actions[row])
            self.current_index = row
        else:
            self.editor.load_action(None)
            self.current_index = None

    def run_scenario(self):
        self.editor.apply()
        self.log.clear()

        try:
            ScenarioRunner(self.actions, self.log).run()
            self.log.append("✔ Сценарий завершён")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
