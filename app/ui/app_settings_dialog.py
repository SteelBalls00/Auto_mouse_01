import os
import configparser

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFormLayout, QDialogButtonBox, QCheckBox, QComboBox, QApplication,
    QWidget, QTabWidget, QScrollArea, QColorDialog
)

from app.actions.registry import ACTION_REGISTRY
from app.ui.action_palette import ACTION_GROUPS
from app.ui import colors_store


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


class ColorCell(QWidget):
    """Кнопка-образец цвета + крестик сброса. value() = '#hex' или '' (наследовать)."""
    changed = pyqtSignal(str)

    def __init__(self, color="", inherit_color=""):
        super().__init__()
        self._color = (color or "").strip()
        self._inherit = (inherit_color or "").strip()

        self.btn = QPushButton()
        self.btn.setFixedSize(120, 24)
        self.btn.clicked.connect(self._pick)

        self.btn_clear = QPushButton("✕")
        self.btn_clear.setFixedWidth(26)
        self.btn_clear.setToolTip("Сбросить (наследовать цвет группы / без цвета)")
        self.btn_clear.clicked.connect(self._clear)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lay.addWidget(self.btn)
        lay.addWidget(self.btn_clear)
        lay.addStretch(1)
        self._render()

    def value(self):
        return self._color

    def set_inherit(self, color):
        self._inherit = (color or "").strip()
        self._render()

    def _render(self):
        if self._color:
            c = QColor(self._color)
            text = self._color
            fg = "#000000" if c.lightness() > 140 else "#ffffff"
            self.btn.setStyleSheet(
                f"QPushButton {{ background:{c.name()}; color:{fg}; "
                f"border:1px solid #888; border-radius:3px; }}"
            )
            self.btn_clear.setEnabled(True)
        elif self._inherit:
            c = QColor(self._inherit)
            fg = "#000000" if c.lightness() > 140 else "#ffffff"
            self.btn.setText("наследует")
            self.btn.setStyleSheet(
                f"QPushButton {{ background:{c.name()}; color:{fg}; "
                f"border:1px dashed #888; border-radius:3px; }}"
            )
            self.btn_clear.setEnabled(False)
            return
        else:
            self.btn.setStyleSheet(
                "QPushButton { border:1px dashed #888; border-radius:3px; }"
            )
            self.btn_clear.setEnabled(False)
        self.btn.setText(self._color or "—")

    def _pick(self):
        start = QColor(self._color or self._inherit or "#fde68a")
        chosen = QColorDialog.getColor(
            start if start.isValid() else QColor("#fde68a"), self, "Выберите цвет"
        )
        if chosen.isValid():
            self._color = chosen.name()
            self._render()
            self.changed.emit(self._color)

    def _clear(self):
        self._color = ""
        self._render()
        self.changed.emit("")


def _build_colors_tab():
    """Вкладка «Цвета»: группы и действия в порядке палитры с выбором цвета."""
    from PyQt5.QtCore import QSettings
    container = QWidget()
    outer = QVBoxLayout(container)

    hint = QLabel(
        "Цвет группы применяется ко всем её действиям. У действия можно задать "
        "свой цвет — он переопределяет групповой. Крестик сбрасывает к наследованию."
    )
    hint.setWordWrap(True)
    hint.setStyleSheet("color:#64748b; font-size:11px;")
    outer.addWidget(hint)

    cb_depth = QCheckBox("Разводить вложенные блоки оттенками по глубине "
                         "(ЕСЛИ/ЦИКЛ/ПОКА/ПОПРОБОВАТЬ)")
    cb_depth.setChecked(
        QSettings("AutoMouse", "RPA").value("depth_tint", False, type=bool)
    )
    outer.addWidget(cb_depth)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    inner = QWidget()
    form = QVBoxLayout(inner)
    form.setSpacing(2)

    group_cells = {}
    action_cells = {}

    for group_name, types in ACTION_GROUPS:
        gc = colors_store.group_color(group_name)
        group_cell = ColorCell(gc)
        group_cells[group_name] = group_cell

        grow = QHBoxLayout()
        glabel = QLabel(group_name)
        glabel.setStyleSheet("font-weight:bold;")
        glabel.setMinimumWidth(260)
        grow.addWidget(glabel)
        grow.addWidget(group_cell)
        grow.addStretch(1)
        gwrap = QWidget()
        gwrap.setLayout(grow)
        form.addWidget(gwrap)

        cells_in_group = []
        for t in types:
            entry = ACTION_REGISTRY.get(t)
            if not entry:
                continue
            name = getattr(entry[0], "name", t)
            ac = ColorCell(colors_store.action_color(t), inherit_color=gc)
            action_cells[t] = ac
            cells_in_group.append(ac)

            arow = QHBoxLayout()
            alabel = QLabel("    " + name)
            alabel.setMinimumWidth(260)
            arow.addWidget(alabel)
            arow.addWidget(ac)
            arow.addStretch(1)
            awrap = QWidget()
            awrap.setLayout(arow)
            form.addWidget(awrap)

        # при смене цвета группы — обновляем «наследует» у её действий
        group_cell.changed.connect(
            lambda c, cells=cells_in_group: [x.set_inherit(c) for x in cells]
        )

    form.addStretch(1)
    scroll.setWidget(inner)
    outer.addWidget(scroll, 1)

    return container, group_cells, action_cells, cb_depth


class AppSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки приложения")
        self.resize(640, 520)

        self.hotkeys = load_hotkeys()

        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs, 1)

        # ── Вкладка «Горячие клавиши» ─────────────────────────────────
        hk_tab = QWidget()
        hk_layout = QVBoxLayout(hk_tab)
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
            wrap = QWidget()
            wrap.setLayout(row)
            form.addRow(label, wrap)
        hk_layout.addLayout(form)
        info = QLabel(
            "После сохранения хоткеи применятся сразу. "
            "Аварийная остановка глобальная — нужен запуск от администратора."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color:#64748b; font-size:11px;")
        hk_layout.addWidget(info)
        hk_layout.addStretch(1)
        tabs.addTab(hk_tab, "Горячие клавиши")

        # ── Вкладка «Цвета» ───────────────────────────────────────────
        colors_tab, self.group_cells, self.action_cells, self.cb_depth = _build_colors_tab()
        tabs.addTab(colors_tab, "Цвета")

        box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        layout.addWidget(box)

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2,
        )

    def save_to_file(self):
        # хоткеи
        result = {name: row.to_item() for name, row in self.rows.items()}
        save_hotkeys(result)
        # цвета
        colors_store.save({
            "groups":  {g: c.value() for g, c in self.group_cells.items()},
            "actions": {t: c.value() for t, c in self.action_cells.items()},
        })
        # развод вложенных блоков оттенками
        from PyQt5.QtCore import QSettings
        QSettings("AutoMouse", "RPA").setValue("depth_tint", self.cb_depth.isChecked())
        return result