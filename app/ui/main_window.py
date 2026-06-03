import os
import copy

from PyQt5.QtCore import Qt, pyqtSlot, QSize, QSettings
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QListWidgetItem,
    QPushButton, QLabel, QTextEdit,
    QVBoxLayout, QHBoxLayout, QMessageBox,
    QFileDialog, QSplitter, QApplication, QDialog
)

from app.actions.registry import ACTION_REGISTRY
from app.models.action_model import ActionModel
from app.scenario.io import save_scenario, load_scenario
from app.scenario.runner import ScenarioRunner
from app.ui.action_editor import ActionEditor
from app.ui.action_palette import ActionPalette
from app.ui.scenario_list import ScenarioList
from app.ui.variables_tree import VariablesTree
from app.ui.var_inspector import VariableInspector
from app.ui.scenario_manager import ScenarioManager
from app.ui.theme import apply_theme
from PyQt5.QtWidgets import QShortcut
from PyQt5.QtGui import QKeySequence
from app.ui.app_settings_dialog import (
    AppSettingsDialog, load_hotkeys, _to_str, _to_qt
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # pyautogui failsafe — увод мыши в левый верхний угол прерывает
        try:
            import pyautogui
            pyautogui.FAILSAFE = True
        except Exception:
            pass

        self.setWindowTitle("Python RPA")
        self.resize(1000, 600)

        self.actions       = []
        self.current_index = None
        self._runner       = None
        self._scenario_path = None
        self._clipboard_steps = []   # скопированные шаги (как dict), переживают смену сценария

        self._build_ui()

        # Локальные хоткеи отладки
        self._sc_next = QShortcut(QKeySequence("F8"), self)
        self._sc_next.activated.connect(self._hotkey_step_next)

        self._sc_stop = QShortcut(QKeySequence("F9"), self)
        self._sc_stop.activated.connect(self._hotkey_stop)

        # Восстановление сохранённой темы
        self._settings = QSettings("AutoMouse", "RPA")
        dark = self._settings.value("dark_theme", False, type=bool)
        self.btn_theme.setChecked(dark)

        self._apply_theme(dark)

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
        # Малиновое выделение: активное — яркое, при потере фокуса — тёмно-малиновое
        self.list.setStyleSheet(
            "QListWidget::item:selected { background: #c2185b; color: #ffffff; }"
            "QListWidget::item:selected:!active { background: #7a0f38; color: #ffffff; }"
        )
        self.list.currentRowChanged.connect(self._on_select)
        self.list.actionDropped.connect(self._add_action_at)
        self.list.stepMoved.connect(self._on_step_moved)
        self.list.contextRequested.connect(self._show_step_menu)

        self.btn_del = QPushButton("🗑 Удалить")
        self.btn_up = QPushButton("⬆ Вверх")
        self.btn_down = QPushButton("⬇ Вниз")
        self.btn_new = QPushButton("📄 Новый")
        self.btn_save = QPushButton("💾 Сохранить")
        self.btn_save_as = QPushButton("💾 Как…")
        self.btn_load = QPushButton("📂 Открыть")
        self.btn_import = QPushButton("📥 Импорт")
        self.btn_migrate = QPushButton("🔄 Обновить шаги")
        self.btn_migrate.setToolTip(
            "Добавить во все шаги недостающие новые параметры "
            "(значения существующих сохраняются)"
        )

        self.btn_del.clicked.connect(self._delete_action)
        self.btn_up.clicked.connect(self._move_up)
        self.btn_down.clicked.connect(self._move_down)
        self.btn_new.clicked.connect(self._new_scenario)
        self.btn_save.clicked.connect(self._save_scenario)
        self.btn_save_as.clicked.connect(self._save_scenario_as)
        self.btn_load.clicked.connect(self._load_scenario)
        self.btn_import.clicked.connect(self._import_actions)
        self.btn_migrate.clicked.connect(self._migrate_steps)

        left = QVBoxLayout()
        left.addWidget(QLabel("Шаги сценария"))
        left.addWidget(self.list)

        left_w = QWidget()
        left_w.setLayout(left)

        # Правая панель — редактор + лог
        self.editor = ActionEditor()

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(200)

        # Кнопки запуска/остановки
        self.btn_run = QPushButton("▶ Запустить")
        self.btn_debug = QPushButton("🐞 По шагам")
        self.btn_slow = QPushButton("🐢 Замедленно")
        self.btn_next = QPushButton("⏭ Дальше")
        self.btn_stop = QPushButton("⏹ Стоп")
        self.btn_stop.setEnabled(False)
        self.btn_next.setEnabled(False)
        self.btn_next.setVisible(False)

        self.btn_theme = QPushButton("🌙 Тёмная тема")
        self.btn_theme.setCheckable(True)
        self.btn_theme.setToolTip("Переключить светлую / тёмную тему")
        self.btn_theme.clicked.connect(self._toggle_theme)

        btn_settings = QPushButton("⚙")
        btn_settings.setToolTip("Настройки приложения")
        btn_settings.clicked.connect(self._open_app_settings)
        btn_settings.setFixedWidth(32)
        # добавь в тот же layout, что и btn_theme

        self.btn_run.clicked.connect(self._run_scenario)
        self.btn_debug.clicked.connect(self._run_debug)
        self.btn_slow.clicked.connect(self._run_slow)
        self.btn_next.clicked.connect(self._step_next)
        self.btn_stop.clicked.connect(self._stop_scenario)

        run_row = QHBoxLayout()
        run_row.addWidget(self.btn_run)
        run_row.addWidget(self.btn_debug)
        run_row.addWidget(self.btn_slow)
        run_row.addWidget(self.btn_next)
        run_row.addWidget(self.btn_stop)
        run_row.addStretch(1)
        run_row.addWidget(self.btn_theme)
        run_row.addWidget(btn_settings)

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
        self.vars_tree.set_context_provider(self._current_context)

        self.btn_inspect = QPushButton("🔍")
        self.btn_inspect.setToolTip("Открыть инспектор переменных")
        self.btn_inspect.setFixedWidth(32)
        self.btn_inspect.clicked.connect(self._open_var_inspector)

        vars_header = QHBoxLayout()
        vars_header.addWidget(QLabel("Переменные результатов"))
        vars_header.addStretch(1)
        vars_header.addWidget(self.btn_inspect)

        vars_layout = QVBoxLayout()
        vars_layout.addLayout(vars_header)
        vars_layout.addWidget(self.vars_tree)
        vars_w = QWidget()
        vars_w.setLayout(vars_layout)

        # Менеджер сценариев — крайняя левая панель
        self.scenario_mgr = ScenarioManager()
        self.scenario_mgr.openRequested.connect(self._open_scenario_path)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.scenario_mgr)
        splitter.addWidget(palette_w)
        splitter.addWidget(left_w)
        splitter.addWidget(right_w)
        splitter.addWidget(vars_w)
        splitter.setSizes([140, 250, 240, 460, 180])

        # ── Верхняя панель кнопок (компактная) ────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(4, 2, 4, 2)
        toolbar.setSpacing(4)
        for b in (self.btn_new, self.btn_load, self.btn_save,
                  self.btn_save_as, self.btn_import):
            toolbar.addWidget(b)
        toolbar.addSpacing(14)
        for b in (self.btn_del, self.btn_up, self.btn_down):
            toolbar.addWidget(b)
        toolbar.addStretch(1)
        toolbar.addWidget(self.btn_migrate)

        toolbar_w = QWidget()
        toolbar_w.setLayout(toolbar)
        toolbar_w.setMaximumHeight(40)

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(toolbar_w)
        root.addWidget(splitter, 1)

        self.setCentralWidget(central)
        self._setup_emergency_stop()

    @pyqtSlot()
    def _hotkey_step_next(self):
        if self.btn_next.isVisible() and self.btn_next.isEnabled():
            self._step_next()

    @pyqtSlot()
    def _hotkey_stop(self):
        if self.btn_stop.isEnabled():
            self._stop_scenario()

    def _migrate_steps(self):
        """Дополнить все шаги недостающими параметрами из актуальных определений
        действий. Значения существующих параметров сохраняются; порядок полей
        приводится к порядку из реестра (новые поля встают на свои места)."""
        from app.actions.registry import ACTION_REGISTRY

        if not self.actions:
            QMessageBox.information(self, "Обновление шагов", "Шагов нет.")
            return

        # зафиксировать правки текущего шага
        if self.current_index is not None and 0 <= self.current_index < len(self.actions):
            self.editor.apply()

        added_total = 0
        affected = 0
        for m in self.actions:
            entry = ACTION_REGISTRY.get(m.action_type)
            if not entry:
                continue
            defaults = entry[1]
            new_params = {}
            added = 0
            # сначала — ключи в порядке дефолтов (существующие значения сохраняем)
            for k, v in defaults.items():
                if k in m.params:
                    new_params[k] = m.params[k]
                else:
                    new_params[k] = copy.deepcopy(v)
                    added += 1
            # затем — «лишние» ключи, которых нет в дефолтах (не теряем их)
            for k, v in m.params.items():
                if k not in new_params:
                    new_params[k] = v
            m.params = new_params
            if added:
                affected += 1
                added_total += added

        self._refresh_list()
        # перезагрузить редактор текущего шага, чтобы новые поля сразу появились
        row = self.list.currentRow()
        if 0 <= row < len(self.actions):
            self.current_index = None   # форсируем повторную загрузку
            self._on_select(row)

        QMessageBox.information(
            self, "Обновление шагов",
            f"Обработано шагов: {len(self.actions)}\n"
            f"Добавлено недостающих параметров: {added_total}\n"
            f"Затронуто шагов: {affected}"
        )

    def _new_scenario(self):
        # Если есть несохранённые шаги — переспрашиваем
        if self.actions:
            reply = QMessageBox.question(
                self, "Новый сценарий",
                "Текущий сценарий будет очищен. Продолжить?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        self.actions = []
        self.current_index = None
        self._scenario_path = None
        self._refresh_list()
        self.editor.load_action(None)
        self.vars_tree.rebuild(self.actions)
        self.log.clear()
        self._update_title("новый")
        self.log.append("📄 Новый сценарий")

    def _setup_emergency_stop(self):
        """Применить хоткеи из конфига."""
        self._apply_hotkeys()

    def _apply_hotkeys(self):
        hk = load_hotkeys()

        # ── 1. Глобальная аварийная — keyboard ───────────────────────
        try:
            import keyboard as kb

            # снять все старые глобальные хоткеи
            for attr in ("_emergency_combo", "_step_next_combo", "_step_stop_combo"):
                combo = getattr(self, attr, None)
                if combo:
                    try:
                        kb.remove_hotkey(combo)
                    except Exception:
                        pass

            # Аварийная остановка
            self._emergency_combo = _to_str(hk["emergency_stop"])
            kb.add_hotkey(
                self._emergency_combo,
                self._emergency_stop_from_thread,
                trigger_on_release=False,
            )

            # Следующий шаг (глобальный)
            self._step_next_combo = _to_str(hk["step_next"])
            kb.add_hotkey(
                self._step_next_combo,
                self._global_step_next_from_thread,
                trigger_on_release=False,
            )

            # Стоп (глобальный)
            self._step_stop_combo = _to_str(hk["step_stop"])
            kb.add_hotkey(
                self._step_stop_combo,
                self._global_stop_from_thread,
                trigger_on_release=False,
            )

            self._hotkey_ok = True

        except ImportError:
            self._hotkey_ok = False
            self._emergency_combo = None
            self._step_next_combo = None
            self._step_stop_combo = None
            # Фолбэк — локальные QShortcut (только при фокусе)
            self._setup_local_shortcuts(hk)

    def _setup_local_shortcuts(self, hk):
        """QShortcut как запасной вариант если keyboard не установлен."""
        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtGui import QKeySequence
        for attr in ("_sc_next", "_sc_stop"):
            old = getattr(self, attr, None)
            if old is not None:
                try:
                    old.setParent(None)
                    old.deleteLater()
                except Exception:
                    pass
        self._sc_next = QShortcut(QKeySequence(_to_qt(hk["step_next"])), self)
        self._sc_next.activated.connect(self._hotkey_step_next)
        self._sc_stop = QShortcut(QKeySequence(_to_qt(hk["step_stop"])), self)
        self._sc_stop.activated.connect(self._hotkey_stop)

    def _open_app_settings(self):
        dlg = AppSettingsDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            dlg.save_to_file()
            self._apply_hotkeys()
            self.log.append("⚙ Настройки обновлены, хоткеи применены")

    def _emergency_stop_from_thread(self):
        # keyboard вызывает из своего потока → пробрасываем в UI-поток
        from PyQt5.QtCore import QMetaObject, Qt
        QMetaObject.invokeMethod(self, "_emergency_stop", Qt.QueuedConnection)

    def _global_step_next_from_thread(self):
        from PyQt5.QtCore import QMetaObject, Qt
        QMetaObject.invokeMethod(self, "_hotkey_step_next", Qt.QueuedConnection)

    def _global_stop_from_thread(self):
        from PyQt5.QtCore import QMetaObject, Qt
        QMetaObject.invokeMethod(self, "_hotkey_stop", Qt.QueuedConnection)

    @staticmethod
    def _noop():
        pass

    def _show_step_menu(self, row, global_pos):
        from PyQt5.QtWidgets import QMenu

        if not (0 <= row < len(self.actions)):
            return
        rows = self._selected_rows()
        # клик правой кнопкой по невыделенному шагу — работаем с ним одним
        if row not in rows:
            rows = [row]
        n = len(rows)

        menu = QMenu(self)
        if n <= 1:
            model = self.actions[row]
            act_run_from = menu.addAction("▶ Запустить с этого шага")
            act_run_one = menu.addAction("⏩ Запустить только этот шаг")
            menu.addSeparator()
            if model.enabled:
                act_toggle = menu.addAction("⊘ Отключить шаг")
            else:
                act_toggle = menu.addAction("✓ Включить шаг")
            menu.addSeparator()
            act_copy = menu.addAction("📋 Копировать")
            act_delete = menu.addAction("🗑 Удалить")
            act_run_selected = None
        else:
            act_run_selected = menu.addAction(f"▶ Запустить выделенные ({n})")
            menu.addSeparator()
            all_enabled = all(self.actions[r].enabled for r in rows)
            act_toggle = menu.addAction(
                f"⊘ Отключить выделенные ({n})" if all_enabled
                else f"✓ Включить выделенные ({n})"
            )
            menu.addSeparator()
            act_copy = menu.addAction(f"📋 Копировать ({n})")
            act_delete = menu.addAction(f"🗑 Удалить выделенные ({n})")
            act_run_from = None
            act_run_one = None

        # Вставка — всегда доступна, если в буфере что-то есть
        act_paste = None
        if self._clipboard_steps:
            menu.addSeparator()
            act_paste = menu.addAction(
                f"📄 Вставить ниже ({len(self._clipboard_steps)})"
            )

        chosen = menu.exec_(global_pos)
        if chosen is None:
            return
        if chosen is act_run_from:
            self._run_scenario(start_from=row)
        elif chosen is act_run_one:
            self._run_single_step(row)
        elif chosen is act_run_selected:
            self._run_selected()
        elif chosen is act_toggle:
            if n <= 1:
                self.actions[row].enabled = not self.actions[row].enabled
                self._refresh_list()
                self.list.setCurrentRow(row)
            else:
                self._toggle_selected()
        elif chosen is act_copy:
            self._copy_steps(rows)
        elif chosen is act_paste:
            self._paste_steps(row)
        elif chosen is act_delete:
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
        for i, model in enumerate(self.actions):
            t = model.action_type
            item = QListWidgetItem(self._step_text(i))

            font = item.font()
            font.setItalic(not model.enabled)
            if t == "separator":
                font.setBold(True)
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                row_h = self.list.fontMetrics().height()
                item.setSizeHint(QSize(0, row_h * 2 + 8))   # ~двойная высота
            item.setFont(font)

            self._style_item(item, model)
            self.list.addItem(item)

        self.list.blockSignals(False)

        if 0 <= current_row < len(self.actions):
            self.list.setCurrentRow(current_row)
        elif self.actions:
            self.list.setCurrentRow(len(self.actions) - 1)
        self.vars_tree.rebuild(self.actions)

    # Светлые подложки управляющих блоков (текст на них всегда тёмный)
    CONTROL_BG = {
        "if_start": "#dbeafe", "else": "#fed7aa", "end_if": "#e5e7eb",
        "for_each_start": "#e9d5ff", "end_for": "#ddd6fe",
        "while_start": "#fef3c7", "end_while": "#fde68a",
        "break": "#fecaca", "continue": "#fecaca",
        "repeat_start": "#e9d5ff", "end_repeat": "#e9d5ff",
        "try_start": "#fce7f3", "catch": "#fbcfe8", "end_try": "#f9a8d4",
    }

    def _style_item(self, item, model, highlighted=False):
        """Единая окраска строки: фон + контрастный текст (для светлой и тёмной темы)."""
        t = model.action_type

        # ── Фон ───────────────────────────────────────────────────────
        if highlighted:
            item.setBackground(QColor("#86efac"))      # выполняемый шаг — зелёный
        elif t == "separator":
            col = QColor(model.params.get("color") or "#fde68a")
            item.setBackground(col if col.isValid() else QColor("#fde68a"))
        else:
            bg = self.CONTROL_BG.get(t)
            item.setBackground(QColor(bg) if bg else QBrush())  # пусто → цвет темы

        # ── Текст ─────────────────────────────────────────────────────
        if not model.enabled:
            item.setForeground(QColor("#9ca3af"))
        elif highlighted:
            item.setForeground(QColor("#1f2937"))
        elif t == "separator":
            col = QColor(model.params.get("color") or "#fde68a")
            light = col.lightness() if col.isValid() else 255
            item.setForeground(QColor("#1f2937") if light > 140 else QColor("#f9fafb"))
        elif self.CONTROL_BG.get(t):
            item.setForeground(QColor("#1f2937"))      # тёмный текст на пастели
        else:
            item.setForeground(QBrush())               # обычный шаг → цвет темы

    def _highlight_step(self, index):
        """Подсветить текущий выполняемый шаг зелёным, остальные — вернуть в норму."""
        for i in range(self.list.count()):
            if 0 <= i < len(self.actions):
                self._style_item(self.list.item(i), self.actions[i],
                                  highlighted=(i == index))

    def _clear_highlight(self):
        for i in range(self.list.count()):
            if 0 <= i < len(self.actions):
                self._style_item(self.list.item(i), self.actions[i])

    # ── Отступы / текст шага ─────────────────────────────────────────
    def _level_at(self, index):
        """Уровень вложенности (кол-во отступов) для шага index —
        той же логикой, что и _refresh_list."""
        level = 0
        for i in range(index):
            t = self.actions[i].action_type
            if t in ("if_start", "for_each_start", "while_start", "repeat_start", "try_start"):
                level += 1
            if t in ("end_if", "end_for", "end_while", "end_repeat", "end_try"):
                level = max(0, level - 1)
        # для самого шага: закрывающие блоки рендерятся на уровень меньше
        t = self.actions[index].action_type
        if t in ("end_if", "end_for", "end_while", "end_repeat", "end_try"):
            level = max(0, level - 1)
        return level

    def _step_text(self, index):
        """Полный текст элемента списка: номер + отступ + префиксы + заголовок."""
        model = self.actions[index]
        t = model.action_type
        # Разделитель — баннер по центру, без номера и отступов
        if t == "separator":
            return model.title()
        indent = "    " * self._level_at(index)
        else_outdent = "  " if t == "else" else ""
        prefix = "⊘ " if not model.enabled else ""
        return f"{index + 1}. {indent}{else_outdent}{prefix}{model.title()}"

    # ── Выбор шага ───────────────────────────────────────────────────
    def _on_select(self, row):
        # Сохранить изменения предыдущего шага
        if self.current_index is not None and 0 <= self.current_index < len(self.actions):
            self.editor.apply()
            self.list.item(self.current_index).setText(
                self._step_text(self.current_index)
            )
            self.vars_tree.rebuild(self.actions)

        if 0 <= row < len(self.actions):
            from app.models.action_model import collect_available_vars
            known = collect_available_vars(self.actions, row)

            self._ensure_preview_path(self.actions[row])
            self.editor.set_actions(self.actions)
            self.editor.load_action(self.actions[row])  # создаём поля
            self.editor.set_known_vars(known)  # потом красим
            self.current_index = row
        else:
            self.editor.load_action(None)
            self.current_index = None

    def _ensure_preview_path(self, model):
        """Для шага клика задать стабильный путь снимка в assets/ и создать
        заглушку, если файла ещё нет (сценарий должен быть сохранён)."""
        if model.action_type != "window_click_xy":
            return
        if not self._scenario_path:
            return  # сценарий ещё не сохранён — снимок негде хранить

        scenario_dir = os.path.dirname(self._scenario_path)
        assets = os.path.join(scenario_dir, "assets")

        preview = model.params.get("preview")
        if not preview:
            import uuid
            preview = os.path.join(assets, f"clickpreview_{uuid.uuid4().hex[:8]}.png")
        elif not os.path.isabs(preview):
            # относительный assets/... → абсолютный для редактора и рантайма
            preview = os.path.join(scenario_dir, preview.replace("/", os.sep))
        model.params["preview"] = preview

        self._make_placeholder_preview(preview)

    def _make_placeholder_preview(self, path):
        """Создать картинку-заглушку, если файла ещё нет."""
        try:
            if not path or os.path.isfile(path):
                return
            os.makedirs(os.path.dirname(path), exist_ok=True)
            from PIL import Image, ImageDraw
            size = 600
            img = Image.new("RGB", (size, size), (38, 40, 46))
            d = ImageDraw.Draw(img)
            lines = ["Снимок ещё не сделан", "выполните этот шаг"]
            y = size // 2 - 24
            for ln in lines:
                d.text((size // 2 - len(ln) * 4, y), ln, fill=(150, 154, 162))
                y += 24
            img.save(path)
        except Exception:
            pass

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
        elif action_type == "repeat_start":
            end_model = ActionModel("end_repeat", ACTION_REGISTRY["end_repeat"][1].copy())
            self.actions.insert(insert_at + 1, end_model)
        elif action_type == "try_start":
            catch_model = ActionModel("catch", ACTION_REGISTRY["catch"][1].copy())
            end_model = ActionModel("end_try", ACTION_REGISTRY["end_try"][1].copy())
            self.actions.insert(insert_at + 1, catch_model)
            self.actions.insert(insert_at + 2, end_model)

        self._refresh_list()
        self.list.setCurrentRow(insert_at)

    def _selected_rows(self):
        """Отсортированный список индексов выделенных шагов."""
        return sorted({i.row() for i in self.list.selectedIndexes()})

    def _reselect_rows(self, rows):
        """Восстановить выделение по списку индексов и поставить курсор на первый."""
        self.list.clearSelection()
        for r in rows:
            if 0 <= r < self.list.count():
                self.list.item(r).setSelected(True)
        if rows:
            self.list.setCurrentRow(rows[0])

    def _delete_action(self):
        rows = self._selected_rows()
        if not rows:
            row = self.list.currentRow()
            if row < 0:
                return
            rows = [row]

        self.editor.apply()
        # Удаляем с конца — индексы оставшихся не сдвигаются
        for r in reversed(rows):
            if 0 <= r < len(self.actions):
                self.actions.pop(r)
        self.current_index = None
        self._refresh_list()

        if self.actions:
            self.list.setCurrentRow(min(rows[0], len(self.actions) - 1))
        else:
            self.editor.load_action(None)

    # ── Перемещение шагов ────────────────────────────────────────────
    def _move_up(self):
        rows = self._selected_rows()
        if not rows or rows[0] <= 0:
            return
        self.editor.apply()
        # Идём по возрастанию — каждый swap двигает свой элемент вверх на 1
        for r in rows:
            self.actions[r - 1], self.actions[r] = self.actions[r], self.actions[r - 1]
        self.current_index = rows[0] - 1
        self._refresh_list()
        self._reselect_rows([r - 1 for r in rows])

    def _move_down(self):
        rows = self._selected_rows()
        if not rows or rows[-1] >= len(self.actions) - 1:
            return
        self.editor.apply()
        # Идём по убыванию — каждый swap двигает свой элемент вниз на 1
        for r in reversed(rows):
            self.actions[r], self.actions[r + 1] = self.actions[r + 1], self.actions[r]
        self.current_index = rows[0] + 1
        self._refresh_list()
        self._reselect_rows([r + 1 for r in rows])

    def _toggle_selected(self):
        """Если все выделенные включены — отключить всех, иначе включить всех."""
        rows = self._selected_rows()
        if not rows:
            return
        new_state = not all(self.actions[r].enabled for r in rows)
        for r in rows:
            self.actions[r].enabled = new_state
        self._refresh_list()
        self._reselect_rows(rows)

    def _run_selected(self):
        """Запустить только выделенный диапазон шагов (от первого до последнего)."""
        rows = self._selected_rows()
        if not rows:
            return
        self._launch(start_from=rows[0], stop_after=rows[-1])

    # ── Копирование / вставка шагов ──────────────────────────────────
    def _copy_steps(self, rows):
        """Скопировать шаги (в порядке следования) в буфер как независимые dict."""
        if not rows:
            return
        self.editor.apply()   # зафиксировать правки текущего шага
        self._clipboard_steps = [
            copy.deepcopy(self.actions[r].to_dict())
            for r in sorted(rows) if 0 <= r < len(self.actions)
        ]
        self.log.append(f"📋 Скопировано шагов: {len(self._clipboard_steps)}")

    def _paste_steps(self, row):
        """Вставить шаги из буфера сразу под шагом row (или в конец, если row<0)."""
        if not self._clipboard_steps:
            return
        if self.current_index is not None and 0 <= self.current_index < len(self.actions):
            self.editor.apply()

        insert_at = (row + 1) if row >= 0 else len(self.actions)
        new_models = [ActionModel.from_dict(copy.deepcopy(d)) for d in self._clipboard_steps]
        for k, m in enumerate(new_models):
            self.actions.insert(insert_at + k, m)

        self._refresh_list()
        # выделяем вставленные
        self._reselect_rows(list(range(insert_at, insert_at + len(new_models))))
        self.log.append(f"📄 Вставлено шагов: {len(new_models)}")

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
        self.scenario_mgr.note_opened(scenario_path)
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
        self.scenario_mgr.note_opened(scenario_path)
        self.log.append(f"💾 Сохранено: {scenario_path}")

    def _load_scenario(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Открыть сценарий", "", "Сценарий (*.json)"
        )
        if path:
            self._open_scenario_path(path)

    def _open_scenario_path(self, path):
        """Открыть сценарий по конкретному пути (из диалога или менеджера)."""
        try:
            name, actions = load_scenario(path)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка загрузки", str(e))
            # битый/удалённый — убираем из недавних
            try:
                from app.scenario import recent
                recent.remove_recent(path)
                self.scenario_mgr.refresh()
            except Exception:
                pass
            return

        self.actions        = actions
        self.current_index  = None
        self._scenario_path = path
        self._refresh_list()
        self._update_title(name or os.path.splitext(os.path.basename(path))[0])
        self.log.append(f"📂 Загружен: {name}  ({path})")

        # Запоминаем в недавних
        self.scenario_mgr.note_opened(path)

        if self.actions:
            self.list.setCurrentRow(0)

    def _toggle_theme(self):
        dark = self.btn_theme.isChecked()
        self._settings.setValue("dark_theme", dark)
        self._apply_theme(dark)

    def _apply_theme(self, dark):
        app = QApplication.instance()
        if app is not None:
            apply_theme(app, dark)
        self.btn_theme.setText("☀ Светлая тема" if dark else "🌙 Тёмная тема")
        # Перекрасить строки списка под новую тему
        self._refresh_list()

    def _update_title(self, name):
        self.setWindowTitle(f"Python RPA — {name}")

    # ── Переменные ───────────────────────────────────────────────────
    def _current_context(self):
        """Живой контекст последнего/текущего прогона (или пусто)."""
        if self._runner is not None:
            return getattr(self._runner, "context", {}) or {}
        return {}

    def _open_var_inspector(self):
        dlg = getattr(self, "_var_inspector", None)
        if dlg is None:
            dlg = VariableInspector(self._current_context, self)
            self._var_inspector = dlg
        dlg.reload()
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _import_actions(self):
        """Импорт всех шагов из другого сценария — вставка после выделенного шага."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Импорт действий из сценария", "", "Сценарий (*.json)"
        )
        if not path:
            return
        try:
            name, imported = load_scenario(path)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка импорта", str(e))
            return
        if not imported:
            QMessageBox.information(self, "Импорт", "В выбранном сценарии нет шагов.")
            return

        if self.current_index is not None and 0 <= self.current_index < len(self.actions):
            self.editor.apply()

        row = self.list.currentRow()
        insert_at = row + 1 if row >= 0 else len(self.actions)
        for k, m in enumerate(imported):
            self.actions.insert(insert_at + k, m)

        self._refresh_list()
        self.list.setCurrentRow(insert_at)
        self.log.append(f"📥 Импортировано шагов: {len(imported)} из «{name or path}»")

    # ── Запуск / остановка ───────────────────────────────────────────
    def _run_scenario(self, start_from=0):
        self._launch(start_from=start_from)

    def _run_debug(self):
        self._launch(step_mode=True)

    def _run_slow(self):
        self._launch(step_delay=1.0)   # 1 сек между шагами

    def _launch(self, start_from=0, step_mode=False, step_delay=0.0, stop_after=None):
        if not self.actions:
            QMessageBox.information(self, "Нет шагов", "Добавьте хотя бы один шаг.")
            return

        self.editor.apply()
        self.log.clear()
        self._clear_highlight()

        self.btn_run.setEnabled(False)
        self.btn_debug.setEnabled(False)
        self.btn_slow.setEnabled(False)
        self.btn_stop.setEnabled(True)

        # Кнопка «Дальше» только в пошаговом режиме
        self.btn_next.setVisible(step_mode)
        self.btn_next.setEnabled(False)

        self._runner = ScenarioRunner(
            self.actions, self,
            start_from=start_from,
            stop_after=stop_after,
            scenario_name=self._current_scenario_name(),
            step_mode=step_mode,
            step_delay=step_delay,
        )
        self._runner.log_line.connect(self.log.append)
        self._runner.step_started.connect(self._highlight_step)
        self._runner.awaiting_step.connect(self._on_awaiting_step)
        self._runner.finished_ok.connect(self._on_runner_done)
        self._runner.finished_error.connect(self._on_runner_error)
        self._runner.start()

    def _on_awaiting_step(self, idx):
        self._highlight_step(idx)
        # Показываем кнопку даже если запустили в обычном режиме
        # (пошаговый мог включиться через действие DebugPause)
        self.btn_next.setVisible(True)
        self.btn_next.setEnabled(True)
        if 0 <= idx < len(self.actions):
            title = self.actions[idx].title()
            self.log.append(f"⏸ Готов выполнить шаг {idx + 1}: {title}  — нажмите «Дальше»")

    def _step_next(self):
        self.btn_next.setEnabled(False)
        if self._runner and self._runner.isRunning():
            self._runner.allow_next_step()

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

    def _reset_run_buttons(self):
        self.btn_run.setEnabled(True)
        self.btn_debug.setEnabled(True)
        self.btn_slow.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_next.setEnabled(False)
        self.btn_next.setVisible(False)

    def _on_runner_done(self):
        self._clear_highlight()
        self._reset_run_buttons()

    def _on_runner_error(self, msg):
        self._clear_highlight()
        self._reset_run_buttons()
        if msg != "Остановлено":
            QMessageBox.critical(self, "Ошибка выполнения", msg)

    def closeEvent(self, event):
        if getattr(self, "_hotkey_ok", False):
            try:
                import keyboard as kb
                for attr in ("_emergency_combo", "_step_next_combo", "_step_stop_combo"):
                    combo = getattr(self, attr, None)
                    if combo:
                        try:
                            kb.remove_hotkey(combo)
                        except Exception:
                            pass
            except ImportError:
                pass

    @pyqtSlot()
    def _emergency_stop(self):
        if self._runner and self._runner.isRunning():
            self._runner.stop()
            try:
                import pyautogui
                pyautogui.moveTo(0, 0, duration=0)
            except Exception:
                pass
            combo = (self._emergency_combo or "").upper().replace("+", "+")
            self.log.append(f"🛑 АВАРИЙНАЯ ОСТАНОВКА ({combo})")