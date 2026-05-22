import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QListWidgetItem,
    QPushButton, QLabel, QTextEdit,
    QVBoxLayout, QHBoxLayout, QMessageBox,
    QFileDialog, QSplitter
)

from app.actions.registry import ACTION_REGISTRY
from app.models.action_model import ActionModel
from app.scenario.io import save_scenario, load_scenario
from app.scenario.runner import ScenarioRunner
from app.ui.action_editor import ActionEditor
from app.ui.action_palette import ActionPalette
from app.ui.scenario_list import ScenarioList
from app.ui.variables_tree import VariablesTree


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python RPA")
        self.resize(1000, 600)

        self.actions       = []
        self.current_index = None
        self._runner       = None
        self._scenario_path = None

        self._build_ui()

    # ── Построение UI ────────────────────────────────────────────────
    def _build_ui(self):
        # ── Палитра действий (самая левая) ────────────────────────────
        self.palette = ActionPalette()
        self.palette.actionChosen.connect(self._add_action_by_type)

        palette_layout = QVBoxLayout()
        palette_layout.addWidget(QLabel("Действия"))
        palette_layout.addWidget(self.palette)
        palette_w = QWidget()
        palette_w.setLayout(palette_layout)

        # ── Список шагов сценария ─────────────────────────────────────
        self.list = ScenarioList()
        self.list.currentRowChanged.connect(self._on_select)
        self.list.actionDropped.connect(self._add_action_at)
        self.list.stepMoved.connect(self._on_step_moved)
        self.list.contextRequested.connect(self._show_step_menu)

        btn_del = QPushButton("🗑 Удалить")
        btn_up = QPushButton("⬆ Вверх")
        btn_down = QPushButton("⬇ Вниз")
        btn_save = QPushButton("💾 Сохранить")
        btn_save_as = QPushButton("💾 Сохранить как…")
        btn_load = QPushButton("📂 Открыть")

        btn_del.clicked.connect(self._delete_action)
        btn_up.clicked.connect(self._move_up)
        btn_down.clicked.connect(self._move_down)
        btn_save.clicked.connect(self._save_scenario)
        btn_save_as.clicked.connect(self._save_scenario_as)
        btn_load.clicked.connect(self._load_scenario)

        move_row = QHBoxLayout()
        move_row.addWidget(btn_up)
        move_row.addWidget(btn_down)

        left = QVBoxLayout()
        left.addWidget(QLabel("Шаги сценария"))
        left.addWidget(self.list)
        left.addWidget(btn_del)
        left.addLayout(move_row)
        left.addWidget(btn_save)
        left.addWidget(btn_save_as)
        left.addWidget(btn_load)

        left_w = QWidget()
        left_w.setLayout(left)

        # Правая панель — редактор + лог
        self.editor = ActionEditor()

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(200)

        # Кнопки запуска/остановки
        self.btn_run  = QPushButton("▶ Запустить")
        self.btn_stop = QPushButton("⏹ Стоп")
        self.btn_stop.setEnabled(False)

        self.btn_run.clicked.connect(self._run_scenario)
        self.btn_stop.clicked.connect(self._stop_scenario)

        run_row = QHBoxLayout()
        run_row.addWidget(self.btn_run)
        run_row.addWidget(self.btn_stop)

        right = QVBoxLayout()
        right.addWidget(QLabel("Параметры шага"))
        right.addWidget(self.editor, 1)
        right.addWidget(QLabel("Лог выполнения"))
        right.addWidget(self.log)
        right.addLayout(run_row)

        right_w = QWidget()
        right_w.setLayout(right)

        # ── Третья панель: дерево переменных ──────────────────────────
        self.vars_tree = VariablesTree()

        vars_layout = QVBoxLayout()
        vars_layout.addWidget(QLabel("Переменные результатов"))
        vars_layout.addWidget(self.vars_tree)
        vars_w = QWidget()
        vars_w.setLayout(vars_layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(palette_w)
        splitter.addWidget(left_w)
        splitter.addWidget(right_w)
        splitter.addWidget(vars_w)
        splitter.setSizes([200, 240, 480, 200])

        self.setCentralWidget(splitter)

    def _show_step_menu(self, row, global_pos):
        from PyQt5.QtWidgets import QMenu

        if not (0 <= row < len(self.actions)):
            return
        model = self.actions[row]

        menu = QMenu(self)
        act_run_from = menu.addAction("▶ Запустить с этого шага")
        act_run_one = menu.addAction("⏩ Запустить только этот шаг")
        menu.addSeparator()
        if model.enabled:
            act_toggle = menu.addAction("⊘ Отключить шаг")
        else:
            act_toggle = menu.addAction("✓ Включить шаг")
        menu.addSeparator()
        act_delete = menu.addAction("🗑 Удалить")

        chosen = menu.exec_(global_pos)
        if chosen is act_run_from:
            self._run_scenario(start_from=row)
        elif chosen is act_run_one:
            self._run_single_step(row)
        elif chosen is act_toggle:
            self.actions[row].enabled = not self.actions[row].enabled
            self._refresh_list()
        elif chosen is act_delete:
            self.list.setCurrentRow(row)
            self._delete_action()

    def _run_single_step(self, idx):
        self.editor.apply()
        self.log.clear()
        self._clear_highlight()
        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self._runner = ScenarioRunner(
            self.actions, self,
            start_from=idx, single_step=True,
            scenario_name=self._current_scenario_name(),
        )
        self._runner.log_line.connect(self.log.append)
        self._runner.step_started.connect(self._highlight_step)
        self._runner.finished_ok.connect(self._on_runner_done)
        self._runner.finished_error.connect(self._on_runner_error)
        self._runner.start()

    # ── Список шагов ─────────────────────────────────────────────────
    def _refresh_list(self):
        """Полностью перестроить список из self.actions."""
        current_row = self.list.currentRow()
        self.list.blockSignals(True)
        self.list.clear()
        level = 0
        for i, model in enumerate(self.actions):
            t = model.action_type
            # уменьшаем уровень ДО рендера на end_if и else
            if t in ("end_if", "end_for", "end_while"):
                level = max(0, level - 1)
            indent  = "    " * level
            else_outdent = "  " if t == "else" else ""
            prefix = "⊘ " if not model.enabled else ""
            text = f"{i + 1}. {indent}{else_outdent}{prefix}{model.title()}"
            item = QListWidgetItem(text)
            if not model.enabled:
                f = item.font()
                f.setItalic(True)
                item.setFont(f)
                item.setForeground(QColor("#9ca3af"))

            # Цвет фона по типу
            if t == "if_start":
                item.setBackground(QColor("#dbeafe"))
            elif t == "else":
                item.setBackground(QColor("#fed7aa"))
            elif t == "end_if":
                item.setBackground(QColor("#e5e7eb"))
            elif t == "for_each_start":
                item.setBackground(QColor("#e9d5ff"))
            elif t == "end_for":
                item.setBackground(QColor("#ddd6fe"))
            elif t == "while_start":
                item.setBackground(QColor("#fef3c7"))
            elif t == "end_while":
                item.setBackground(QColor("#fde68a"))
            elif t in ("break", "continue"):
                item.setBackground(QColor("#fecaca"))

            self.list.addItem(item)

            if t in ("if_start", "for_each_start", "while_start"):
                level += 1
        self.list.blockSignals(False)

        if 0 <= current_row < len(self.actions):
            self.list.setCurrentRow(current_row)
        elif self.actions:
            self.list.setCurrentRow(len(self.actions) - 1)
        self.vars_tree.rebuild(self.actions)

    def _base_color(self, action_type):
        if action_type == "if_start":       return QColor("#dbeafe")
        if action_type == "else":           return QColor("#fed7aa")
        if action_type == "end_if":         return QColor("#e5e7eb")
        if action_type == "for_each_start": return QColor("#e9d5ff")
        if action_type == "end_for":        return QColor("#ddd6fe")
        if action_type in ("break", "continue"): return QColor("#fecaca")
        if action_type == "while_start":    return QColor("#fef3c7")
        if action_type == "end_while":      return QColor("#fde68a")
        return QColor("white")

    def _highlight_step(self, index):
        """Подсветить текущий выполняемый шаг ярко-зелёным."""
        for i in range(self.list.count()):
            item = self.list.item(i)
            if i == index:
                item.setBackground(QColor("#86efac"))   # яркий зелёный
            else:
                item.setBackground(self._base_color(self.actions[i].action_type))

    def _clear_highlight(self):
        for i in range(self.list.count()):
            self.list.item(i).setBackground(self._base_color(self.actions[i].action_type))

    # ── Выбор шага ───────────────────────────────────────────────────
    def _on_select(self, row):
        # Сохранить изменения предыдущего шага
        if self.current_index is not None and 0 <= self.current_index < len(self.actions):
            self.editor.apply()
            self.list.item(self.current_index).setText(
                f"{self.current_index + 1}. {self.actions[self.current_index].title()}"
            )
            # Если предыдущий шаг был SQL — обновить дерево
            self.vars_tree.rebuild(self.actions)

        if 0 <= row < len(self.actions):
            self.editor.load_action(self.actions[row])
            self.current_index = row
        else:
            self.editor.load_action(None)
            self.current_index = None

    # ── Добавление / удаление ────────────────────────────────────────
    def _add_action_by_type(self, action_type):
        """Добавить шаг — вызывается двойным кликом по палитре.
        Вставка после выделенного шага (или в конец, если ничего не выделено)."""
        row = self.list.currentRow()
        insert_at = row + 1 if row >= 0 else len(self.actions)
        self._add_action_at(action_type, insert_at)

    def _add_action_at(self, action_type, insert_at):
        """Универсальная вставка по индексу — для палитры и drag&drop."""
        if self.current_index is not None and 0 <= self.current_index < len(self.actions):
            self.editor.apply()

        insert_at = max(0, min(insert_at, len(self.actions)))

        params = ACTION_REGISTRY[action_type][1].copy()
        model = ActionModel(action_type, params)
        self.actions.insert(insert_at, model)

        # Парный конец для управляющих блоков
        if action_type == "if_start":
            end_model = ActionModel("end_if", ACTION_REGISTRY["end_if"][1].copy())
            self.actions.insert(insert_at + 1, end_model)
        elif action_type == "for_each_start":
            end_model = ActionModel("end_for", ACTION_REGISTRY["end_for"][1].copy())
            self.actions.insert(insert_at + 1, end_model)
        elif action_type == "while_start":
            end_model = ActionModel("end_while", ACTION_REGISTRY["end_while"][1].copy())
            self.actions.insert(insert_at + 1, end_model)

        self._refresh_list()
        self.list.setCurrentRow(insert_at)

    def _delete_action(self):
        row = self.list.currentRow()
        if row < 0:
            return

        self.editor.apply()
        self.actions.pop(row)
        self.current_index = None
        self._refresh_list()

        if self.actions:
            self.list.setCurrentRow(min(row, len(self.actions) - 1))
        else:
            self.editor.load_action(None)

    # ── Перемещение шагов ────────────────────────────────────────────
    def _move_up(self):
        row = self.list.currentRow()
        if row <= 0:
            return
        self.editor.apply()
        self.actions[row], self.actions[row - 1] = self.actions[row - 1], self.actions[row]
        self.current_index = row - 1
        self._refresh_list()
        self.list.setCurrentRow(row - 1)

    def _move_down(self):
        row = self.list.currentRow()
        if row < 0 or row >= len(self.actions) - 1:
            return
        self.editor.apply()
        self.actions[row], self.actions[row + 1] = self.actions[row + 1], self.actions[row]
        self.current_index = row + 1
        self._refresh_list()
        self.list.setCurrentRow(row + 1)

    def _on_step_moved(self, src, dst):
        """Шаг перетащили мышкой в новое место."""
        if not (0 <= src < len(self.actions)):
            return
        if self.current_index is not None and 0 <= self.current_index < len(self.actions):
            self.editor.apply()

        item = self.actions.pop(src)
        dst = max(0, min(dst, len(self.actions)))
        self.actions.insert(dst, item)
        self.current_index = dst
        self._refresh_list()
        self.list.setCurrentRow(dst)

    # ── Сохранение / загрузка ────────────────────────────────────────
    def _save_scenario(self):
        """Сохранить в текущую папку, если она известна. Иначе — как новое."""
        if not self._scenario_path:
            self._save_scenario_as()
            return

        self.editor.apply()
        scenario_dir   = os.path.dirname(self._scenario_path)
        parent_folder  = os.path.dirname(scenario_dir)
        name           = os.path.basename(scenario_dir)

        try:
            scenario_path = save_scenario(parent_folder, name, self.actions)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка сохранения", str(e))
            return

        self._scenario_path = scenario_path
        self._update_title(name)
        self.log.append(f"💾 Сохранено: {scenario_path}")

    def _save_scenario_as(self):
        """Выбор имени и места: один диалог 'Сохранить как'."""
        self.editor.apply()

        # Стартовое предложение имени — на основе текущего пути
        default_path = self._scenario_path or "scenario.json"
        default_dir  = os.path.dirname(default_path) if self._scenario_path else ""
        default_file = os.path.join(default_dir, os.path.basename(default_path)) \
            if default_dir else "scenario.json"

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить сценарий",
            default_file,
            "Сценарий (*.json)"
        )
        if not path:
            return

        # Имя сценария = имя файла без расширения
        # Папка сценария = берётся имя файла, рядом с выбранным местом
        chosen_dir = os.path.dirname(path)
        name       = os.path.splitext(os.path.basename(path))[0]

        try:
            scenario_path = save_scenario(chosen_dir, name, self.actions)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка сохранения", str(e))
            return

        self._scenario_path = scenario_path
        self._update_title(name)
        self.log.append(f"💾 Сохранено: {scenario_path}")

    def _load_scenario(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Открыть сценарий", "", "Сценарий (*.json)"
        )
        if not path:
            return

        try:
            name, actions = load_scenario(path)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка загрузки", str(e))
            return

        self.actions        = actions
        self.current_index  = None
        self._scenario_path = path
        self._refresh_list()
        self._update_title(name or os.path.splitext(os.path.basename(path))[0])
        self.log.append(f"📂 Загружен: {name}  ({path})")

        if self.actions:
            self.list.setCurrentRow(0)

    def _update_title(self, name):
        self.setWindowTitle(f"Python RPA — {name}")

    # ── Запуск / остановка ───────────────────────────────────────────
    def _run_scenario(self, start_from=0):
        if not self.actions:
            QMessageBox.information(self, "Нет шагов", "Добавьте хотя бы один шаг.")
            return

        self.editor.apply()
        self.log.clear()
        self._clear_highlight()

        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)

        self._runner = ScenarioRunner(
            self.actions, self,
            start_from=start_from,
            scenario_name=self._current_scenario_name(),
        )
        self._runner.log_line.connect(self.log.append)
        self._runner.step_started.connect(self._highlight_step)
        self._runner.finished_ok.connect(self._on_runner_done)
        self._runner.finished_error.connect(self._on_runner_error)
        self._runner.start()

    def _current_scenario_name(self):
        """Имя текущего сценария — из пути к scenario.json или 'unsaved'."""
        if self._scenario_path:
            scenario_dir = os.path.dirname(self._scenario_path)
            return os.path.basename(scenario_dir)
        return "unsaved"

    def _stop_scenario(self):
        if self._runner and self._runner.isRunning():
            self._runner.stop()
            self.log.append("⏹ Запрос на остановку отправлен…")

    def _on_runner_done(self):
        self._clear_highlight()
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def _on_runner_error(self, msg):
        self._clear_highlight()
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)
        if msg != "Остановлено":
            QMessageBox.critical(self, "Ошибка выполнения", msg)

    def closeEvent(self, event):
        if self._runner and self._runner.isRunning():
            self._runner.stop()
            self._runner.wait(2000)
        event.accept()
