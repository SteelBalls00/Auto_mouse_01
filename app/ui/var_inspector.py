"""
Инспектор переменных: окно со списком переменных слева и содержимым справа,
плюс утилиты форматирования значений (компактно для подсказок, полно для окна).
"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QListWidget, QListWidgetItem, QTextEdit, QSplitter,
    QPushButton, QVBoxLayout, QHBoxLayout, QLabel, QWidget
)

# Служебные ключи контекста, которые не показываем
SKIP_KEYS = {"stop_event", "pause_event"}


def _is_visible_key(k):
    return not k.startswith("_") and k not in SKIP_KEYS


def resolve_path(context, expr):
    """
    Разрешить выражение вида '{ns.field.sub}' или 'ns.field' в значение контекста.
    Возвращает (found, value).
    """
    if expr is None:
        return False, None
    expr = expr.strip()
    if expr.startswith("{") and expr.endswith("}"):
        expr = expr[1:-1].strip()
    if not expr:
        return False, None
    parts = expr.split(".")
    if parts[0] not in context:
        return False, None
    obj = context[parts[0]]
    for p in parts[1:]:
        if isinstance(obj, dict) and p in obj:
            obj = obj[p]
        else:
            return False, None
    return True, obj


def type_tag(value):
    """Короткая пометка типа/размера для списка переменных."""
    if isinstance(value, dict):
        return f"{{словарь, полей: {len(value)}}}"
    if isinstance(value, list):
        return f"[список, строк: {len(value)}]"
    if value is None:
        return "NULL"
    return type(value).__name__


def format_compact(value, maxlen=240):
    """Однострочное компактное представление (для всплывающих подсказок)."""
    if value is None:
        return "NULL"
    if isinstance(value, dict):
        parts = []
        for k, v in value.items():
            parts.append(f"{k}={_compact_scalar(v, 50)}")
        s = "{" + ", ".join(parts) + "}"
    elif isinstance(value, list):
        s = f"[список, строк: {len(value)}]"
        if value:
            s += "  первая: " + _compact_scalar(value[0], 120)
    else:
        s = str(value)
    return s if len(s) <= maxlen else s[:maxlen] + " …"


def _compact_scalar(v, maxlen=50):
    if v is None:
        return "NULL"
    if isinstance(v, dict):
        return f"{{полей: {len(v)}}}"
    if isinstance(v, list):
        return f"[строк: {len(v)}]"
    s = str(v)
    return s if len(s) <= maxlen else s[:maxlen] + "…"


def format_full(value, max_chars=20000):
    """Полное (многострочное) представление для правой панели окна."""
    if value is None:
        text = "NULL"
    elif isinstance(value, dict):
        if not value:
            text = "{пустой словарь}"
        else:
            width = max((len(str(k)) for k in value.keys()), default=0)
            lines = [f"{str(k).ljust(width)} : {_compact_scalar(v, 2000)}"
                     for k, v in value.items()]
            text = "\n".join(lines)
    elif isinstance(value, list):
        if not value:
            text = "[пустой список]"
        else:
            lines = [f"строк всего: {len(value)}", ""]
            for idx, row in enumerate(value):
                if idx >= 500:
                    lines.append(f"… ещё {len(value) - 500} строк")
                    break
                if isinstance(row, dict):
                    inner = ", ".join(f"{k}={_compact_scalar(v, 200)}"
                                      for k, v in row.items())
                    lines.append(f"[{idx}] {{{inner}}}")
                else:
                    lines.append(f"[{idx}] {_compact_scalar(row, 500)}")
            text = "\n".join(lines)
    else:
        text = str(value)

    if len(text) > max_chars:
        shown = text[:max_chars]
        text = f"{shown}\n\n… показано {max_chars} из {len(text)} символов"
    return text


class VariableInspector(QDialog):
    """
    Окно: слева — список переменных, справа — содержимое выбранной.
    context_provider() должен возвращать актуальный словарь контекста.
    """
    def __init__(self, context_provider, parent=None):
        super().__init__(parent)
        self._provider = context_provider
        self.setWindowTitle("Инспектор переменных")
        self.resize(820, 480)

        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._on_select)

        self.viewer = QTextEdit()
        self.viewer.setReadOnly(True)
        self.viewer.setLineWrapMode(QTextEdit.NoWrap)
        font = self.viewer.font()
        font.setFamily("Consolas")
        self.viewer.setFont(font)

        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(0, 0, 0, 0)
        left_l.addWidget(QLabel("Переменные"))
        left_l.addWidget(self.list)

        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(0, 0, 0, 0)
        right_l.addWidget(QLabel("Содержимое"))
        right_l.addWidget(self.viewer)

        split = QSplitter(Qt.Horizontal)
        split.addWidget(left)
        split.addWidget(right)
        split.setSizes([260, 560])

        btn_refresh = QPushButton("🔄 Обновить")
        btn_refresh.clicked.connect(self.reload)
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.close)
        bottom = QHBoxLayout()
        bottom.addWidget(btn_refresh)
        bottom.addStretch(1)
        bottom.addWidget(btn_close)

        root = QVBoxLayout(self)
        root.addWidget(split, 1)
        root.addLayout(bottom)

        self._snapshot = {}
        self.reload()

    def reload(self):
        """Перечитать контекст и обновить список (значения сохраняются для просмотра)."""
        prev = self.list.currentItem().text() if self.list.currentItem() else None
        try:
            ctx = self._provider() or {}
            self._snapshot = dict(ctx)   # поверхностная копия снимка
        except Exception:
            self._snapshot = {}

        self.list.clear()
        keys = [k for k in self._snapshot.keys() if _is_visible_key(k)]
        if not keys:
            self.viewer.setPlainText(
                "Переменных пока нет.\n\n"
                "Они появляются по мере выполнения сценария: запустите сценарий "
                "(в т.ч. в режиме «По шагам») и нажмите «Обновить»."
            )
            return

        restore_row = 0
        for idx, k in enumerate(sorted(keys)):
            item = QListWidgetItem(f"{k}    {type_tag(self._snapshot[k])}")
            item.setData(Qt.UserRole, k)
            self.list.addItem(item)
            if prev and item.text() == prev:
                restore_row = idx
        self.list.setCurrentRow(restore_row)

    def _on_select(self, row):
        item = self.list.item(row)
        if not item:
            self.viewer.clear()
            return
        key = item.data(Qt.UserRole)
        self.viewer.setPlainText(format_full(self._snapshot.get(key)))
