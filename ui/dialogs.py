from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel
)
from actions.registry import ACTION_REGISTRY


class AddActionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить действие")
        self.setModal(True)
        self.setMinimumWidth(300)

        self.combo = QComboBox()
        for key, (cls, _) in ACTION_REGISTRY.items():
            self.combo.addItem(cls.name, key)

        btn_ok     = QPushButton("Добавить")
        btn_cancel = QPushButton("Отмена")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Тип действия:"))
        layout.addWidget(self.combo)

        btns = QHBoxLayout()
        btns.addStretch()
        btns.addWidget(btn_ok)
        btns.addWidget(btn_cancel)
        layout.addLayout(btns)
        self.setLayout(layout)

    def selected_action(self):
        return self.combo.currentData()
