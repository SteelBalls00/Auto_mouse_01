import os
import configparser

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFormLayout, QDialogButtonBox, QCheckBox, QComboBox, QApplication
)


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOTKEYS_INI  = os.path.join(PROJECT_ROOT, "app_hotkeys.ini")

# Те же клавиши, что в боте
HOTKEY_KEYS = [
    "F1","F2","F3","F4","F5","F6","F7","F8","F9","F10","F11","F12",
    "F13","F14","F15","F16","F17","F18","F19","F20","F21","F22","F23","F24",
    "A","B","C","D","E","F","G","H","I","J","K","L","M",
    "N","O","P","Q","R","S","T","U","V","W","X","Y","Z",
    "Insert","Delete","Home","End","PageUp","PageDown",
    "Space","Enter","Esc","Tab","Pause",
]


DEFAULTS = {
    "emergency_stop": {"shift": True,  "ctrl": True,  "alt": False, "win": False, "key": "Q"},
    "step_next":      {"shift": False, "ctrl": False, "alt": False, "win": False, "key": "F8"},
    "step_stop":      {"shift": False, "ctrl": False, "alt": False, "win": False, "key": "F9"},
}


def _parse(value):
    """'ctrl+shift+q' -> {ctrl,shift,alt,win,key}"""
    parts = [p.strip().lower() for p in value.split("+") if p.strip()]
    res = {"shift": False, "ctrl": False, "alt": False, "win": False, "key": ""}
    for p in parts:
        if p == "ctrl":     res["ctrl"] = True
        elif p == "shift":  res["shift"] = True
        elif p == "alt":    res["alt"] = True
        elif p in ("win", "windows"): res["win"] = True
        else:
            res["key"] = p.upper() if len(p) == 1 else p.capitalize()
    return res


def _to_str(d):
    parts = []
    if d.get("ctrl"):  parts.append("ctrl")
    if d.get("alt"):   parts.append("alt")
    if d.get("shift"): parts.append("shift")
    if d.get("win"):   parts.append("windows")
    if d.get("key"):   parts.append(d["key"].lower())
    return "+".join(parts)


def _to_qt(d):
    """Для QKeySequence: 'Ctrl+Shift+Q'"""
    parts = []
    if d.get("ctrl"):  parts.append("Ctrl")
    if d.get("shift"): parts.append("Shift")
    if d.get("alt"):   parts.append("Alt")
    if d.get("win"):   parts.append("Meta")
    if d.get("key"):   parts.append(d["key"])
    return "+".join(parts)


def load_hotkeys():
    cfg = configparser.ConfigParser()
    if os.path.exists(HOTKEYS_INI):
        cfg.read(HOTKEYS_INI, encoding="utf-8")
    result = {}
    for name, default in DEFAULTS.items():
        if cfg.has_option("hotkeys", name):
            result[name] = _parse(cfg.get("hotkeys", name))
        else:
            result[name] = dict(default)
    return result


def save_hotkeys(hotkeys):
    cfg = configparser.ConfigParser()
    cfg.add_section("hotkeys")
    for name, d in hotkeys.items():
        cfg.set("hotkeys", name, _to_str(d))
    with open(HOTKEYS_INI, "w", encoding="utf-8") as f:
        cfg.write(f)


class _HotkeyRow(QHBoxLayout):
    def __init__(self, item):
        super().__init__()
        self.cb_shift = QCheckBox("Shift")
        self.cb_ctrl  = QCheckBox("Ctrl")
        self.cb_alt   = QCheckBox("Alt")
        self.cb_win   = QCheckBox("Win")
        self.cb_shift.setChecked(item.get("shift", False))
        self.cb_ctrl.setChecked(item.get("ctrl", False))
        self.cb_alt.setChecked(item.get("alt", False))
        self.cb_win.setChecked(item.get("win", False))
        for cb in (self.cb_shift, self.cb_ctrl, self.cb_alt, self.cb_win):
            self.addWidget(cb)

        self.key = QComboBox()
        self.key.addItems(HOTKEY_KEYS)
        cur = item.get("key", "F8")
        idx = self.key.findText(cur)
        if idx < 0:
            self.key.addItem(cur)
            idx = self.key.findText(cur)
        self.key.setCurrentIndex(idx)
        self.addWidget(self.key, 1)

    def to_item(self):
        return {
            "shift": self.cb_shift.isChecked(),
            "ctrl":  self.cb_ctrl.isChecked(),
            "alt":   self.cb_alt.isChecked(),
            "win":   self.cb_win.isChecked(),
            "key":   self.key.currentText(),
        }


class AppSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки приложения")
        self.resize(520, 280)

        self.hotkeys = load_hotkeys()

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Горячие клавиши"))

        form = QFormLayout()
        self.rows = {}
        labels = {
            "emergency_stop": "Аварийная остановка (глобальная):",
            "step_next":      "Следующий шаг (пошагово):",
            "step_stop":      "Остановить выполнение:",
        }
        for name, label in labels.items():
            row = _HotkeyRow(self.hotkeys[name])
            self.rows[name] = row
            w = self.parent()  # просто чтобы создать
            from PyQt5.QtWidgets import QWidget
            wrap = QWidget()
            wrap.setLayout(row)
            form.addRow(label, wrap)
        layout.addLayout(form)

        info = QLabel(
            "После сохранения хоткеи применятся сразу. "
            "Аварийная остановка глобальная — нужен запуск от администратора."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color:#64748b; font-size:11px;")
        layout.addWidget(info)

        box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        layout.addWidget(box)

        # Центрируем
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2,
        )

    def save_to_file(self):
        result = {name: row.to_item() for name, row in self.rows.items()}
        save_hotkeys(result)
        return result