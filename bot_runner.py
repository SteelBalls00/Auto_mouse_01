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
    QDialog, QLineEdit, QCheckBox, QSpinBox, QFormLayout, QDialogButtonBox
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
            # Текущая операция — строки вида "[n/m] ..."
            if text.lstrip().startswith("["):
                self.current_op.emit(text.strip())

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
class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Настройки бота")
        self.setMinimumWidth(420)

        form = QFormLayout()

        self.path_edit = QLineEdit(config.get("bot", "scenario_path", fallback=""))
        browse = QPushButton("Обзор…")
        browse.clicked.connect(self._browse)
        path_row = QHBoxLayout()
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(browse)
        form.addRow("Сценарий:", path_row)

        self.name_edit = QLineEdit(config.get("bot", "bot_name", fallback="Бот"))
        form.addRow("Имя бота:", self.name_edit)

        self.loop_chk = QCheckBox("Зацикливать выполнение")
        self.loop_chk.setChecked(config.getint("bot", "loop", fallback=1) == 1)
        form.addRow("", self.loop_chk)

        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 3600)
        self.delay_spin.setValue(config.getint("bot", "loop_delay", fallback=5))
        self.delay_spin.setSuffix(" сек")
        form.addRow("Пауза между прогонами:", self.delay_spin)

        box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(box)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выбрать сценарий", "", "Сценарий (*.json)"
        )
        if path:
            self.path_edit.setText(path)

    def save_to_config(self):
        if not self.config.has_section("bot"):
            self.config.add_section("bot")
        self.config.set("bot", "scenario_path", self.path_edit.text().strip())
        self.config.set("bot", "bot_name", self.name_edit.text().strip())
        self.config.set("bot", "loop", "1" if self.loop_chk.isChecked() else "0")
        self.config.set("bot", "loop_delay", str(self.delay_spin.value()))
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            self.config.write(f)


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
            self._add_line("Настройки сохранены", "info")

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
        tray.hide()
        app.quit()
    act_quit.triggered.connect(_quit)

    tray.activated.connect(
        lambda reason: win.show() if reason == QSystemTrayIcon.Trigger else None
    )

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
