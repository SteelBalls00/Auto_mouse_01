from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel
)

from actions.registry import ACTION_REGISTRY


class AddActionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбор действия")
        self.setModal(True)

        self.combo = QComboBox()
        for key, (cls, _) in ACTION_REGISTRY.items():
            self.combo.addItem(cls.name, key)

        btn_ok = QPushButton("OK")
        btn_cancel = QPushButton("Cancel")

        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Тип действия:"))
        layout.addWidget(self.combo)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(btn_ok)
        buttons.addWidget(btn_cancel)

        layout.addLayout(buttons)
        self.setLayout(layout)

    def selected_action(self):
        return self.combo.currentData()
