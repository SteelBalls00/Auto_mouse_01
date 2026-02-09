from PyQt5.QtWidgets import (
    QWidget, QFormLayout, QLabel,
    QLineEdit, QSpinBox, QComboBox
)

class ActionEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QFormLayout(self)
        self.model = None
        self.editors = {}

    def load_action(self, model):
        self.model = model

        while self.layout.rowCount():
            self.layout.removeRow(0)
        self.editors.clear()

        if not model:
            return

        for key, value in model.params.items():
            if isinstance(value, bool):
                w = QComboBox()
                w.addItems(["False", "True"])
                w.setCurrentIndex(1 if value else 0)
            elif isinstance(value, int):
                w = QSpinBox()
                w.setMaximum(10_000_000)
                w.setValue(value)
            else:
                w = QLineEdit(str(value))

            self.layout.addRow(QLabel(key), w)
            self.editors[key] = w

    def apply(self):
        if not self.model:
            return

        for key, w in self.editors.items():
            if isinstance(w, QSpinBox):
                self.model.params[key] = w.value()
            elif isinstance(w, QComboBox):
                self.model.params[key] = w.currentText() == "True"
            else:
                self.model.params[key] = w.text()
