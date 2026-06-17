# pyinstaller --noconfirm --clean --onedir --windowed --name AutoMouseBot --icon app/resources/automouse.ico --collect-all pywinauto --collect-submodules comtypes --hidden-import keyboard --hidden-import fdb --hidden-import pyperclip --add-data "app/resources;app/resources" bot_runner.py
"""
Автономный бот-раннер для Auto_mouse_01.

Запуск:  python bot_runner.py
Кладётся рядом с main.py (в корне проекта), использует app/scenario/...

Компактное окно над треем:
  - статус (запущен / пауза / остановлен) и текущая операция
  - лента из 10 последних операций (новые снизу, старые уползают вверх)
  - кнопки: ▶ старт, ⏸ пауза, ⏹ стоп, ⚙ настройки
Путь к сценарию берётся из bot_config.ini.
"""

import os
import sys
import threading
import configparser

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QPropertyAnimation, QPoint
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QSystemTrayIcon, QMenu, QFileDialog,
    QDialog, QLineEdit, QCheckBox, QSpinBox, QFormLayout, QDialogButtonBox, QComboBox
)

# ── Путь к проекту ───────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.scenario.io import load_scenario          # noqa: E402
from app.scenario.runner import ScenarioRunner     # noqa: E402

CONFIG_PATH = os.path.join(PROJECT_ROOT, "bot_config.ini")
MAX_FEED_LINES = 10


# ════════════════════════════════════════════════════════════════════
#  Управляющий объект бота: гоняет сценарии в фоне, шлёт сигналы в UI
# ════════════════════════════════════════════════════════════════════
class BotController(QObject):
    line          = pyqtSignal(str, str)   # (текст, тип: info/ok/err/step)
    state_changed = pyqtSignal(str)        # idle / running / paused / stopped
    current_op    = pyqtSignal(str)        # текущая операция

    def __init__(self, config):
        super().__init__()
        self.config       = config
        self._runner      = None
        self._loop_thread = None
        self._stop_flag   = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()            # set = НЕ на паузе
        self._running     = False

    # ── Управление ───────────────────────────────────────────────────
    def start(self):
        if self._running:
            # снять с паузы, если стояли
            self._pause_event.set()
            self.state_changed.emit("running")
            return

        scenario_path = self.config.get("bot", "scenario_path", fallback="").strip()
        if not scenario_path or not os.path.exists(scenario_path):
            self.line.emit(f"Сценарий не найден: {scenario_path}", "err")
            return

        self._stop_flag.clear()
        self._pause_event.set()
        self._running = True
        self.state_changed.emit("running")

        self._loop_thread = threading.Thread(target=self._run_loop, daemon=True)
        self._loop_thread.start()

    def pause(self):
        if self._running:
            self._pause_event.clear()      # clear = на паузе
            self.state_changed.emit("paused")
            self.line.emit("⏸ Пауза", "info")

    def stop(self):
        self._stop_flag.set()
        self._pause_event.set()            # снять паузу чтобы цикл смог завершиться
        if self._runner:
            self._runner.stop()
        self._running = False
        self.state_changed.emit("stopped")
        self.line.emit("⏹ Остановлено", "info")

    # ── Основной цикл ────────────────────────────────────────────────
    def _run_loop(self):
        loop       = self.config.getint("bot", "loop", fallback=1)
        loop_delay = self.config.getint("bot", "loop_delay", fallback=5)
        scenario_path = self.config.get("bot", "scenario_path").strip()

        while not self._stop_flag.is_set():
            # Уважаем паузу
            self._pause_event.wait()
            if self._stop_flag.is_set():
                break

            try:
                name, actions = load_scenario(scenario_path)
            except Exception as e:
                self.line.emit(f"Ошибка загрузки сценария: {e}", "err")
                break

            self.line.emit(f"▶ Запуск: {name}", "info")
            self._run_one(actions, name)

            if not loop or self._stop_flag.is_set():
                break

            # Пауза между прогонами, но с проверкой стопа
            for _ in range(loop_delay * 10):
                if self._stop_flag.is_set():
                    break
                self._pause_event.wait()
                threading.Event().wait(0.1)

        self._running = False
        self.state_changed.emit("idle")
        self.current_op.emit("")
        self.line.emit("Бот остановлен", "info")

    def run_scenario_file(self, path):
        """Запустить конкретный сценарий по горячей клавише (разовый прогон)."""
        if self._running:
            self.line.emit("⚠ Бот занят, хоткей проигнорирован", "err")
            return
        if not os.path.exists(path):
            self.line.emit(f"Сценарий не найден: {path}", "err")
            return

        self._stop_flag.clear()
        self._pause_event.set()
        self._running = True
        self.state_changed.emit("running")

        def _thread():
            try:
                name, actions = load_scenario(path)
                self.line.emit(f"⌨ Хоткей → {name}", "info")
                self._run_one(actions, name)
            except Exception as e:
                self.line.emit(f"Ошибка: {e}", "err")
            finally:
                self._running = False
                self.state_changed.emit("idle")
                self.current_op.emit("")

        self._loop_thread = threading.Thread(target=_thread, daemon=True)
        self._loop_thread.start()

    def _run_one(self, actions, name):
        """Прогоняет один сценарий синхронно в текущем потоке."""
        self._runner = ScenarioRunner(
            actions, parent=None,
            scenario_name=name,
            project_root=PROJECT_ROOT,
        )
        # Прокидываем pause/stop в контекст
        self._runner.context["stop_event"]  = self._stop_flag
        self._runner.context["pause_event"] = self._pause_event

        done = threading.Event()

        def on_line(text):
            t = "step"
            if "✔" in text:
                t = "ok"
            elif "✖" in text:
                t = "err"
            self.line.emit(text.strip(), t)
            # Текущая операция — строки вида "[n/m] Название действия..."
            stripped = text.strip()
            if stripped.startswith("["):
                # отрезаем счётчик "[n/m] " и хвостовые точки → чистое русское имя
                label = stripped
                close = label.find("]")
                if close != -1:
                    label = label[close + 1:].strip()
                label = label.rstrip(".").strip()
                if label:
                    self.current_op.emit(label)

        self._runner.log_line.connect(on_line)
        self._runner.finished_ok.connect(lambda: done.set())
        self._runner.finished_error.connect(lambda _msg: done.set())

        self._runner.start()
        # Ждём завершения, не блокируя обработку сигналов невозможно тут —
        # поэтому крутимся в этом фоне-потоке, сигналы доходят до UI-потока сами.
        self._runner.wait()
        done.wait(0.1)


# ════════════════════════════════════════════════════════════════════
#  Диалог настроек
# ════════════════════════════════════════════════════════════════════
import json as _json

# Список клавиш для комбобокса горячих клавиш
HOTKEY_KEYS = [
    "F1","F2","F3","F4","F5","F6","F7","F8","F9","F10","F11","F12",
    "F13","F14","F15","F16","F17","F18","F19","F20","F21","F22","F23","F24",
    "A","B","C","D","E","F","G","H","I","J","K","L","M",
    "N","O","P","Q","R","S","T","U","V","W","X","Y","Z",
    "0","1","2","3","4","5","6","7","8","9",
    "Insert","Delete","Home","End","PageUp","PageDown",
    "Up","Down","Left","Right","Space","Enter","Esc","Tab",
    "NumPad0","NumPad1","NumPad2","NumPad3","NumPad4",
    "NumPad5","NumPad6","NumPad7","NumPad8","NumPad9",
]


def hotkey_to_keyboard_str(item):
    """Преобразует объект хоткея в строку для библиотеки keyboard: 'shift+alt+f13'."""
    parts = []
    if item.get("ctrl"):  parts.append("ctrl")
    if item.get("alt"):   parts.append("alt")
    if item.get("shift"): parts.append("shift")
    if item.get("win"):   parts.append("windows")
    key = (item.get("key") or "").strip().lower()
    if key:
        parts.append(key)
    return "+".join(parts)


def hotkey_to_label(item):
    """Человекочитаемая строка: 'Shift + Alt + F13'."""
    parts = []
    if item.get("ctrl"):  parts.append("Ctrl")
    if item.get("alt"):   parts.append("Alt")
    if item.get("shift"): parts.append("Shift")
    if item.get("win"):   parts.append("Win")
    if item.get("key"):   parts.append(item["key"])
    return " + ".join(parts) if parts else "—"


class HotkeyRowWidget(QWidget):
    """Одна строка во вкладке хоткеев: вкл + путь + модификаторы + клавиша + удалить."""
    changed = pyqtSignal()
    removed = pyqtSignal(object)

    def __init__(self, item=None):
        super().__init__()
        item = item or {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Верхняя строка: чекбокс вкл + путь + обзор + удалить
        top = QHBoxLayout()
        self.enabled = QCheckBox()
        self.enabled.setChecked(item.get("enabled", True))
        self.enabled.setToolTip("Включить / отключить горячую клавишу")
        self.enabled.stateChanged.connect(lambda: self.changed.emit())
        top.addWidget(self.enabled)

        self.path = QLineEdit(item.get("path", ""))
        self.path.setPlaceholderText("Путь к scenario.json")
        self.path.textChanged.connect(lambda: self.changed.emit())
        top.addWidget(self.path, 1)

        browse = QPushButton("…")
        browse.setFixedWidth(30)
        browse.clicked.connect(self._browse)
        top.addWidget(browse)

        rm = QPushButton("✕")
        rm.setFixedWidth(30)
        rm.setStyleSheet("color:#dc2626;")
        rm.clicked.connect(lambda: self.removed.emit(self))
        top.addWidget(rm)
        layout.addLayout(top)

        # Нижняя строка: модификаторы + клавиша
        bot = QHBoxLayout()
        self.cb_shift = QCheckBox("Shift")
        self.cb_ctrl  = QCheckBox("Ctrl")
        self.cb_alt   = QCheckBox("Alt")
        self.cb_win   = QCheckBox("Win")
        self.cb_shift.setChecked(item.get("shift", False))
        self.cb_ctrl.setChecked(item.get("ctrl", False))
        self.cb_alt.setChecked(item.get("alt", False))
        self.cb_win.setChecked(item.get("win", False))
        for cb in (self.cb_shift, self.cb_ctrl, self.cb_alt, self.cb_win):
            cb.stateChanged.connect(lambda: self.changed.emit())
            bot.addWidget(cb)

        self.key = QComboBox()
        self.key.addItems(HOTKEY_KEYS)
        cur = item.get("key", "F13")
        idx = self.key.findText(cur)
        if idx >= 0:
            self.key.setCurrentIndex(idx)
        self.key.currentTextChanged.connect(lambda: self.changed.emit())
        bot.addWidget(QLabel("Клавиша:"))
        bot.addWidget(self.key, 1)
        layout.addLayout(bot)

        # Разделитель
        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet("background:#e5e7eb;")
        layout.addWidget(line)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выбрать сценарий", "", "Сценарий (*.json)"
        )
        if path:
            self.path.setText(path)

    def to_item(self):
        return {
            "path":    self.path.text().strip(),
            "shift":   self.cb_shift.isChecked(),
            "ctrl":    self.cb_ctrl.isChecked(),
            "alt":     self.cb_alt.isChecked(),
            "win":     self.cb_win.isChecked(),
            "key":     self.key.currentText(),
            "enabled": self.enabled.isChecked(),
        }


class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Настройки бота")
        self.resize(640, 520)

        from PyQt5.QtWidgets import QTabWidget, QScrollArea
        tabs = QTabWidget()

        # ── Вкладка 1: Общие ──────────────────────────────────────────
        general = QWidget()
        form = QFormLayout(general)

        self.path_edit = QLineEdit(config.get("bot", "scenario_path", fallback=""))
        browse = QPushButton("Обзор…")
        browse.clicked.connect(self._browse_main)
        path_row = QHBoxLayout()
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(browse)
        form.addRow("Основной сценарий:", path_row)

        self.name_edit = QLineEdit(config.get("bot", "bot_name", fallback="Бот"))
        form.addRow("Имя бота:", self.name_edit)

        self.loop_chk = QCheckBox("Зацикливать выполнение основного сценария")
        self.loop_chk.setChecked(config.getint("bot", "loop", fallback=1) == 1)
        form.addRow("", self.loop_chk)

        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 3600)
        self.delay_spin.setValue(config.getint("bot", "loop_delay", fallback=5))
        self.delay_spin.setSuffix(" сек")
        form.addRow("Пауза между прогонами:", self.delay_spin)

        tabs.addTab(general, "Общие")

        # ── Вкладка 2: Горячие клавиши ────────────────────────────────
        hk_tab = QWidget()
        hk_layout = QVBoxLayout(hk_tab)

        info = QLabel(
            "Назначьте горячие клавиши для запуска сценариев. "
            "Работают глобально, даже когда бот свёрнут."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color:#64748b; font-size:11px;")
        hk_layout.addWidget(info)

        self.rows_container = QWidget()
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(0)
        self.rows_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.rows_container)
        hk_layout.addWidget(scroll, 1)

        add_btn = QPushButton("➕ Добавить горячую клавишу")
        add_btn.clicked.connect(lambda: self._add_row())
        hk_layout.addWidget(add_btn)

        tabs.addTab(hk_tab, "Горячие клавиши")

        # Загружаем существующие хоткеи
        self.rows = []
        for item in self._load_hotkeys():
            self._add_row(item)

        # ── Кнопки ────────────────────────────────────────────────────
        box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(tabs, 1)
        layout.addWidget(box)

        # Центрируем относительно экрана
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2,
        )

    def _browse_main(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выбрать сценарий", "", "Сценарий (*.json)"
        )
        if path:
            self.path_edit.setText(path)

    def _add_row(self, item=None):
        row = HotkeyRowWidget(item)
        row.removed.connect(self._remove_row)
        # вставляем перед растяжкой (последний элемент)
        self.rows_layout.insertWidget(self.rows_layout.count() - 1, row)
        self.rows.append(row)

    def _remove_row(self, row):
        if row in self.rows:
            self.rows.remove(row)
        row.setParent(None)
        row.deleteLater()

    def _load_hotkeys(self):
        if not self.config.has_section("hotkeys"):
            return []
        raw = self.config.get("hotkeys", "items", fallback="[]")
        try:
            return _json.loads(raw)
        except Exception:
            return []

    def save_to_config(self):
        if not self.config.has_section("bot"):
            self.config.add_section("bot")
        self.config.set("bot", "scenario_path", self.path_edit.text().strip())
        self.config.set("bot", "bot_name", self.name_edit.text().strip())
        self.config.set("bot", "loop", "1" if self.loop_chk.isChecked() else "0")
        self.config.set("bot", "loop_delay", str(self.delay_spin.value()))

        if not self.config.has_section("hotkeys"):
            self.config.add_section("hotkeys")
        items = [r.to_item() for r in self.rows if r.path.text().strip()]
        self.config.set("hotkeys", "items", _json.dumps(items, ensure_ascii=False))

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            self.config.write(f)


class HotkeyManager:
    """
    Регистрирует глобальные горячие клавиши через библиотеку keyboard.
    При нажатии запускает соответствующий сценарий через переданный колбэк.
    """
    def __init__(self, run_callback):
        self._run_callback = run_callback
        self._registered = []
        self._kb = None
        try:
            import keyboard
            self._kb = keyboard
        except ImportError:
            self._kb = None

    def available(self):
        return self._kb is not None

    def reload(self, config):
        """Перечитать хоткеи из конфига и перерегистрировать."""
        if not self._kb:
            return
        self.clear()

        if not config.has_section("hotkeys"):
            return
        import json
        try:
            items = json.loads(config.get("hotkeys", "items", fallback="[]"))
        except Exception:
            items = []

        for item in items:
            if not item.get("enabled", True):
                continue
            path = (item.get("path") or "").strip()
            if not path:
                continue
            combo = hotkey_to_keyboard_str(item)
            if not combo:
                continue
            try:
                # default args фиксируют значения в замыкании
                handle = self._kb.add_hotkey(
                    combo,
                    lambda p=path: self._run_callback(p)
                )
                self._registered.append(handle)
            except Exception:
                pass

    def clear(self):
        if not self._kb:
            return
        for h in self._registered:
            try:
                self._kb.remove_hotkey(h)
            except Exception:
                pass
        self._registered = []


# ════════════════════════════════════════════════════════════════════
#  Главное окно бота (компактное, над треем)
# ════════════════════════════════════════════════════════════════════
class BotWindow(QWidget):
    COLORS = {
        "info": "#94a3b8",
        "step": "#e2e8f0",
        "ok":   "#4ade80",
        "err":  "#f87171",
    }

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.ctrl   = BotController(config)

        self._build_ui()
        self._wire()

        # Глобальные горячие клавиши
        self.hotkeys = HotkeyManager(self._run_by_hotkey)
        if self.hotkeys.available():
            self.hotkeys.reload(self.config)
        else:
            self._add_line("⚠ Модуль 'keyboard' не установлен — хоткеи выключены", "err")

        self._position_above_tray()

    # ── UI ────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setFixedSize(340, 300)
        self.setStyleSheet("""
            QWidget#root {
                background: #0f172a;
                border: 1px solid #334155;
                border-radius: 10px;
            }
            QLabel { color: #e2e8f0; }
            QPushButton {
                background: #1e293b; color: #e2e8f0;
                border: 1px solid #334155; border-radius: 6px;
                padding: 6px; font-size: 13px;
            }
            QPushButton:hover { background: #334155; }
            QListWidget {
                background: #0b1220; border: none; color: #e2e8f0;
                font-family: 'Consolas','Courier New',monospace; font-size: 11px;
            }
            QListWidget::item { padding: 2px 4px; }
        """)

        root = QWidget(self)
        root.setObjectName("root")
        root.setGeometry(0, 0, 340, 300)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Заголовок: имя бота + статус-точка
        head = QHBoxLayout()
        self.dot = QLabel("●")
        self.dot.setStyleSheet("color:#64748b; font-size:14px;")
        bot_name = self.config.get("bot", "bot_name", fallback="Бот")
        self.title = QLabel(bot_name)
        self.title.setStyleSheet("font-weight:700; font-size:13px;")
        self.state_lbl = QLabel("Остановлен")
        self.state_lbl.setStyleSheet("color:#94a3b8; font-size:11px;")
        head.addWidget(self.dot)
        head.addWidget(self.title)
        head.addStretch()
        head.addWidget(self.state_lbl)
        layout.addLayout(head)

        # Текущая операция
        self.op_lbl = QLabel("—")
        self.op_lbl.setWordWrap(True)
        self.op_lbl.setStyleSheet(
            "color:#38bdf8; font-size:11px; background:#1e293b;"
            "border-radius:5px; padding:5px 7px;"
        )
        layout.addWidget(self.op_lbl)

        # Лента операций
        self.feed = QListWidget()
        self.feed.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.feed.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.feed.setSelectionMode(QListWidget.NoSelection)
        self.feed.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(self.feed, 1)

        # Кнопки
        btns = QHBoxLayout()
        btns.setSpacing(6)
        self.btn_start = QPushButton("▶")
        self.btn_pause = QPushButton("⏸")
        self.btn_stop  = QPushButton("⏹")
        self.btn_set   = QPushButton("⚙")
        self.btn_min   = QPushButton("—")
        for b in (self.btn_start, self.btn_pause, self.btn_stop, self.btn_set, self.btn_min):
            b.setFixedHeight(30)
            btns.addWidget(b)
        self.btn_start.setToolTip("Старт / снять с паузы")
        self.btn_pause.setToolTip("Пауза")
        self.btn_stop.setToolTip("Стоп")
        self.btn_set.setToolTip("Настройки")
        self.btn_min.setToolTip("Свернуть в трей")
        layout.addLayout(btns)

        # Перетаскивание окна за заголовок
        self._drag_pos = None

    def _wire(self):
        self.btn_start.clicked.connect(self.ctrl.start)
        self.btn_pause.clicked.connect(self.ctrl.pause)
        self.btn_stop.clicked.connect(self.ctrl.stop)
        self.btn_set.clicked.connect(self._open_settings)
        self.btn_min.clicked.connect(self.hide)

        self.ctrl.line.connect(self._add_line)
        self.ctrl.state_changed.connect(self._on_state)
        self.ctrl.current_op.connect(self._on_op)

    # ── Лента ──────────────────────────────────────────────────────────
    def _add_line(self, text, kind):
        item = QListWidgetItem(text)
        item.setForeground(QColor(self.COLORS.get(kind, "#e2e8f0")))
        self.feed.addItem(item)

        # держим не больше MAX_FEED_LINES — старые уезжают вверх и исчезают
        while self.feed.count() > MAX_FEED_LINES:
            self.feed.takeItem(0)

        self.feed.scrollToBottom()

    def _on_state(self, state):
        colors = {
            "running": ("#22c55e", "Работает"),
            "paused":  ("#f59e0b", "Пауза"),
            "stopped": ("#ef4444", "Остановлен"),
            "idle":    ("#64748b", "Ожидание"),
        }
        color, label = colors.get(state, ("#64748b", state))
        self.dot.setStyleSheet(f"color:{color}; font-size:14px;")
        self.state_lbl.setText(label)

    def _on_op(self, text):
        self.op_lbl.setText(text or "—")

    # ── Настройки ──────────────────────────────────────────────────────
    def _open_settings(self):
        dlg = SettingsDialog(self.config, self)
        if dlg.exec_() == QDialog.Accepted:
            dlg.save_to_config()
            self.title.setText(self.config.get("bot", "bot_name", fallback="Бот"))
            # Перерегистрируем хоткеи
            if hasattr(self, "hotkeys") and self.hotkeys.available():
                self.hotkeys.reload(self.config)
            self._add_line("Настройки сохранены, хоткеи обновлены", "info")

    # ── Позиция над треем ──────────────────────────────────────────────
    def _position_above_tray(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.right() - self.width() - 12
        y = screen.bottom() - self.height() - 12
        self.move(x, y)

    # ── Перетаскивание окна ────────────────────────────────────────────
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.LeftButton:
            self.move(e.globalPos() - self._drag_pos)
            e.accept()

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    def _run_by_hotkey(self, path):
        # keyboard вызывает из своего потока — пробрасываем в контроллер
        self.ctrl.run_scenario_file(path)

# ════════════════════════════════════════════════════════════════════
#  Точка входа + трей
# ════════════════════════════════════════════════════════════════════
def main():
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_PATH):
        config.read(CONFIG_PATH, encoding="utf-8")
    else:
        config.add_section("bot")
        config.set("bot", "scenario_path", "")
        config.set("bot", "loop", "1")
        config.set("bot", "loop_delay", "5")
        config.set("bot", "bot_name", "Бот")

    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("AutoMouse.Bot.1")
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)   # чтобы при сворачивании в трей не закрывалось

    icon_path = os.path.join(PROJECT_ROOT, "app", "resources", "automouse.ico")
    icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
    app.setWindowIcon(icon)

    win = BotWindow(config)
    win.show()

    # Трей
    tray = QSystemTrayIcon(icon, app)
    tray.setToolTip(config.get("bot", "bot_name", fallback="Бот"))
    menu = QMenu()
    act_show  = menu.addAction("Показать")
    act_start = menu.addAction("Старт")
    act_stop  = menu.addAction("Стоп")
    menu.addSeparator()
    act_quit  = menu.addAction("Выход")
    tray.setContextMenu(menu)
    tray.show()

    act_show.triggered.connect(lambda: (win.show(), win._position_above_tray()))
    act_start.triggered.connect(win.ctrl.start)
    act_stop.triggered.connect(win.ctrl.stop)

    def _quit():
        win.ctrl.stop()
        if hasattr(win, "hotkeys"):
            win.hotkeys.clear()
        tray.hide()
        app.quit()
    act_quit.triggered.connect(_quit)

    tray.activated.connect(
        lambda reason: win.show() if reason == QSystemTrayIcon.Trigger else None
    )

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
