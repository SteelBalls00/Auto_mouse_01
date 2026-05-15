from PyQt5.QtWidgets import (
    QWidget, QFormLayout, QLabel,
    QLineEdit, QSpinBox, QDoubleSpinBox,
    QCheckBox, QComboBox, QPlainTextEdit
)
from app.actions.registry import ACTION_REGISTRY


class ActionEditor(QWidget):
    def __init__(self):
        super().__init__()
        self._layout = QFormLayout(self)
        self.model   = None
        self.editors = {}

    def load_action(self, model):
        self.model = model

        while self._layout.rowCount():
            self._layout.removeRow(0)
        self.editors.clear()

        if not model:
            return

        cls     = ACTION_REGISTRY[model.action_type][0]
        labels  = getattr(cls, "param_labels", {})
        options = getattr(cls, "param_options", {})
        widgets = getattr(cls, "param_widgets", {})

        for key, value in model.params.items():
            label_text = labels.get(key, key)

            if widgets.get(key) == "multiline":
                # ── Многострочное текстовое поле ──────────────────────
                w = QPlainTextEdit()
                w.setPlainText(str(value))
                w.setMinimumHeight(80)
                w.setAcceptDrops(True)

            elif key in options:
                # ── Комбобокс ─────────────────────────────────────────
                w = QComboBox()
                for opt in options[key]:
                    w.addItem(opt)
                current = str(value)
                idx = w.findText(current)
                if idx >= 0:
                    w.setCurrentIndex(idx)
                else:
                    w.insertItem(0, current)
                    w.setCurrentIndex(0)

            elif isinstance(value, bool):
                w = QCheckBox()
                w.setChecked(value)

            elif isinstance(value, float):
                w = QDoubleSpinBox()
                w.setDecimals(2)
                w.setSingleStep(0.05)
                w.setRange(0.0, 9999.0)
                w.setValue(value)

            elif isinstance(value, int):
                w = QSpinBox()
                w.setMaximum(10_000_000)
                w.setValue(value)

            else:
                w = QLineEdit(str(value))

            self._layout.addRow(QLabel(label_text), w)
            self.editors[key] = (w, type(value))

    def apply(self):
        if not self.model:
            return

        for key, (w, orig_type) in self.editors.items():
            if isinstance(w, QPlainTextEdit):
                self.model.params[key] = w.toPlainText()
            elif isinstance(w, QComboBox):
                self.model.params[key] = w.currentText()
            elif isinstance(w, QCheckBox):
                self.model.params[key] = w.isChecked()
            elif isinstance(w, QDoubleSpinBox):
                self.model.params[key] = round(w.value(), 4)
            elif isinstance(w, QSpinBox):
                self.model.params[key] = w.value()
            else:
                raw = w.text()
                if orig_type == float:
                    try:
                        self.model.params[key] = float(raw)
                    except ValueError:
                        pass
                elif orig_type == int:
                    try:
                        self.model.params[key] = int(raw)
                    except ValueError:
                        pass
                else:
                    self.model.params[key] = raw