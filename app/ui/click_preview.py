import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QCheckBox, QHBoxLayout, QPushButton


class ClickPreviewWidget(QWidget):
    """
    Превью области вокруг точки клика: квадратный снимок + галка
    «Показывать точку нажатия» (тонкое перекрестие '+' в центре).
    Снимок берётся из файла image_path (создаётся при выполнении шага).
    value() возвращает состояние галки (для сохранения в show_crosshair).
    """
    BOX = 260   # сторона области отображения, px

    def __init__(self, image_path="", show_crosshair=True):
        super().__init__()
        self._path = image_path or ""
        self._src = None   # исходный QPixmap снимка

        self.image_label = QLabel()
        self.image_label.setFixedSize(self.BOX, self.BOX)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet(
            "border: 1px solid #6b7079; border-radius: 4px; color: #9ca3af;"
        )

        self.chk = QCheckBox("Показывать точку нажатия")
        self.chk.setChecked(bool(show_crosshair))
        self.chk.toggled.connect(self._render)

        btn_reload = QPushButton("🔄")
        btn_reload.setFixedWidth(32)
        btn_reload.setToolTip("Обновить снимок (после выполнения шага)")
        btn_reload.clicked.connect(self.reload)

        bottom = QHBoxLayout()
        bottom.addWidget(self.chk)
        bottom.addStretch(1)
        bottom.addWidget(btn_reload)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.image_label)
        root.addLayout(bottom)

        self.reload()

    def value(self):
        """Состояние галки — пойдёт в параметр show_crosshair."""
        return self.chk.isChecked()

    def reload(self):
        """Перечитать снимок с диска и перерисовать."""
        self._src = None
        if self._path and os.path.isfile(self._path):
            pm = QPixmap(self._path)
            if not pm.isNull():
                self._src = pm
        self._render()

    def _render(self):
        if self._src is None:
            self.image_label.setText(
                "Снимок появится\nпосле выполнения шага\n\n"
                "(сценарий должен быть сохранён)"
            )
            self.image_label.setPixmap(QPixmap())
            return

        # вписываем снимок в квадрат
        scaled = self._src.scaled(
            self.BOX, self.BOX, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )

        if self.chk.isChecked():
            scaled = QPixmap(scaled)   # копия для рисования
            painter = QPainter(scaled)
            w, h = scaled.width(), scaled.height()
            cx, cy = w // 2, h // 2
            # тонкое перекрестие через весь снимок
            pen = QPen(QColor(220, 38, 38, 200))   # полупрозрачный красный
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawLine(cx, 0, cx, h)
            painter.drawLine(0, cy, w, cy)
            # маленький квадрат-маркер в центре
            painter.drawRect(cx - 3, cy - 3, 6, 6)
            painter.end()

        self.image_label.setText("")
        self.image_label.setPixmap(scaled)
