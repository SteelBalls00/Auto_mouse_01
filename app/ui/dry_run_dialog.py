"""
Окно сухого прогона: сверху — пошаговый лог (что БЫ выполнилось и какие
значения подставились), снизу — итоговые переменные.
"""
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QSplitter, QWidget
)

from app.ui.var_inspector import format_full, type_tag, _is_visible_key


class DryRunDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Сухой прогон — что будет выполнено")
        self.resize(820, 620)

        self.status = QLabel("Выполняется сухой прогон…")
        self.status.setStyleSheet("font-weight:bold;")

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.document().setMaximumBlockCount(20000)
        f = self.log.font()
        f.setFamily("Consolas")
        self.log.setFont(f)

        self.vars = QTextEdit()
        self.vars.setReadOnly(True)
        self.vars.setFont(f)
        self.vars.setPlaceholderText("Итоговые переменные появятся после завершения…")

        top = QWidget()
        tl = QVBoxLayout(top)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.addWidget(QLabel("Пошаговый разбор (🧪 — действие пропущено, показано "
                            "что бы ушло):"))
        tl.addWidget(self.log)

        bot = QWidget()
        bl = QVBoxLayout(bot)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.addWidget(QLabel("Итоговые переменные:"))
        bl.addWidget(self.vars)

        split = QSplitter(Qt.Vertical)
        split.addWidget(top)
        split.addWidget(bot)
        split.setSizes([400, 220])

        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.close)
        row = QHBoxLayout()
        row.addWidget(self.status)
        row.addStretch(1)
        row.addWidget(btn_close)

        root = QVBoxLayout(self)
        root.addWidget(split, 1)
        root.addLayout(row)

    def append_line(self, text):
        self.log.append(text)

    def finish(self, ok, context):
        if ok:
            self.status.setText("✔ Сухой прогон завершён")
            self.status.setStyleSheet("font-weight:bold; color:#15803d;")
        else:
            self.status.setText("✖ Сухой прогон прерван ошибкой (см. лог)")
            self.status.setStyleSheet("font-weight:bold; color:#b91c1c;")
        self._dump_vars(context or {})

    def _dump_vars(self, context):
        keys = [k for k in context.keys() if _is_visible_key(k)]
        if not keys:
            self.vars.setPlainText("Переменных нет.")
            return
        parts = []
        for k in sorted(keys):
            parts.append(f"=== {k}   {type_tag(context[k])} ===\n"
                         f"{format_full(context[k])}")
        self.vars.setPlainText("\n\n".join(parts))
