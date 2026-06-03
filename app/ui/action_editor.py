from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QWidget, QFormLayout, QLabel,
    QLineEdit, QSpinBox, QDoubleSpinBox,
    QCheckBox, QComboBox, QPlainTextEdit, QPushButton, QColorDialog
)
from app.actions.registry import ACTION_REGISTRY
from app.actions.sql_utils import parse_select_columns
from app.ui.var_highlighter import VarHighlighter
from app.ui.code_highlighter import CodeHighlighter
from app.ui.click_preview import ClickPreviewWidget


class ColorPickerButton(QPushButton):
    """Кнопка с превью текущего цвета; по клику открывает палитру."""
    def __init__(self, value=""):
        super().__init__()
        self._color = (value or "").strip() or "#fde68a"
        self.clicked.connect(self._pick)
        self._refresh()

    def _refresh(self):
        c = QColor(self._color)
        if not c.isValid():
            c = QColor("#fde68a")
            self._color = c.name()
        # контрастный текст поверх фона
        text_color = "#000000" if c.lightness() > 140 else "#ffffff"
        self.setText(self._color)
        self.setStyleSheet(
            f"QPushButton {{ background:{c.name()}; color:{text_color}; "
            f"padding:5px; border:1px solid #9ca3af; border-radius:3px; }}"
        )

    def _pick(self):
        start = QColor(self._color)
        chosen = QColorDialog.getColor(
            start if start.isValid() else QColor("#fde68a"),
            self, "Выберите цвет фона"
        )
        if chosen.isValid():
            self._color = chosen.name()
            self._refresh()

    def value(self):
        return self._color


class ActionEditor(QWidget):
    def __init__(self):
        super().__init__()
        self._layout = QFormLayout(self)
        self.model   = None
        self.editors = {}
        self._actions = []   # ссылка на все шаги сценария (для автозаполнения)

    def set_actions(self, actions):
        """Передать ссылку на список всех шагов — нужно автозаполнению колонок цикла."""
        self._actions = actions or []

    @staticmethod
    def _highlight_language(action_type, key):
        """Язык подсветки для многострочного поля или None (только переменные)."""
        if action_type in ("sql", "sql_many") and key == "query":
            return "sql"
        if action_type == "python_eval" and key == "code":
            return "python"
        return None

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

            if widgets.get(key) == "hidden":
                # параметр редактируется через другой виджет (см. click_preview)
                continue

            if widgets.get(key) == "click_preview":
                # ── Превью области клика + галка перекрестия ───────────
                w = ClickPreviewWidget(
                    image_path=str(value or ""),
                    show_crosshair=bool(model.params.get("show_crosshair", True)),
                )
                self._layout.addRow(QLabel(label_text), w)
                # галка внутри виджета сохраняется в show_crosshair
                self.editors["show_crosshair"] = (w, bool)
                continue

            if widgets.get(key) == "color":
                # ── Выбор цвета через палитру ─────────────────────────
                w = ColorPickerButton(str(value))

            elif widgets.get(key) == "multiline":
                # ── Многострочное текстовое поле ──────────────────────
                w = QPlainTextEdit()
                w.setPlainText(str(value))
                w.setMinimumHeight(80)
                w.setAcceptDrops(True)
                # Подсветка: SQL / Python — иначе только переменные
                lang = self._highlight_language(model.action_type, key)
                if lang:
                    hl = CodeHighlighter(w.document(), language=lang)
                else:
                    hl = VarHighlighter(w.document())
                hl.set_known(getattr(self, "_known_vars", set()))
                w._var_highlighter = hl

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
                w.textChanged.connect(
                    lambda _t, ww=w: self._check_lineedit_vars(ww)
                )

            self._layout.addRow(QLabel(label_text), w)
            self.editors[key] = (w, type(value))

            # начальная проверка для QLineEdit
            if isinstance(w, QLineEdit):
                self._check_lineedit_vars(w)

        # ── Кнопки автозаполнения колонок ─────────────────────────────
        if model.action_type in ("sql", "sql_many") and \
                "query" in self.editors and "columns" in self.editors:
            btn = QPushButton("↻ Заполнить колонки из SELECT")
            btn.clicked.connect(self._autofill_columns_from_select)
            self._layout.addRow(btn)

        if model.action_type == "for_each_start" and \
                "source" in self.editors and "columns" in self.editors:
            btn = QPushButton("↻ Колонки из источника (SQL)")
            btn.clicked.connect(self._autofill_loop_columns)
            self._layout.addRow(btn)

    # ── Автозаполнение колонок ────────────────────────────────────────
    def _autofill_columns_from_select(self):
        qw = self.editors.get("query")
        cw = self.editors.get("columns")
        if not qw or not cw:
            return
        query_text = qw[0].toPlainText() if isinstance(qw[0], QPlainTextEdit) else qw[0].text()
        cols = parse_select_columns(query_text)
        if cols:
            cw[0].setText(", ".join(cols))
            self._check_lineedit_vars(cw[0])

    def _autofill_loop_columns(self):
        sw = self.editors.get("source")
        cw = self.editors.get("columns")
        if not sw or not cw:
            return
        source = sw[0].text().strip()
        cols = self._columns_for_query_name(source)
        if cols:
            cw[0].setText(", ".join(cols))
            self._check_lineedit_vars(cw[0])

    def _columns_for_query_name(self, query_name):
        """Найти SQL-шаг с таким query_name и вернуть его колонки
        (явно заданные или разобранные из SELECT)."""
        if not query_name:
            return []
        for m in self._actions:
            if m.action_type not in ("sql", "sql_many"):
                continue
            if (m.params.get("query_name") or "").strip() != query_name:
                continue
            explicit = (m.params.get("columns") or "").strip()
            if explicit:
                return [c.strip() for c in explicit.split(",") if c.strip()]
            return parse_select_columns(m.params.get("query", ""))
        return []

    def _check_lineedit_vars(self, line_edit):
        import re
        text = line_edit.text()
        tokens = re.findall(r"\{([^{}]+)\}", text)
        if not tokens:
            line_edit.setStyleSheet("")  # нет переменных — обычный вид
            return

        known = getattr(self, "_known_vars", set())
        all_ok = True
        for expr in tokens:
            expr = expr.strip()
            ok = expr in known
            if not ok and (expr.endswith(".index") or expr.endswith(".count")):
                ns = expr.rsplit(".", 1)[0]
                ok = any(k == expr or k.startswith(ns + ".") for k in known)
            if not ok:
                all_ok = False
                break

        if all_ok:
            line_edit.setStyleSheet("QLineEdit { border: 1px solid #16a34a; }")
        else:
            line_edit.setStyleSheet("QLineEdit { border: 1px solid #dc2626; }")

    def set_known_vars(self, known_vars):
        """Передать список доступных переменных (для подсветки)."""
        self._known_vars = set(known_vars)
        for key, (w, _t) in self.editors.items():
            hl = getattr(w, "_var_highlighter", None)
            if hl is not None:
                hl.set_known(self._known_vars)
            from PyQt5.QtWidgets import QLineEdit
            if isinstance(w, QLineEdit):
                self._check_lineedit_vars(w)

    def apply(self):
        if not self.model:
            return

        for key, (w, orig_type) in self.editors.items():
            if isinstance(w, ClickPreviewWidget):
                self.model.params[key] = w.value()
            elif isinstance(w, ColorPickerButton):
                self.model.params[key] = w.value()
            elif isinstance(w, QPlainTextEdit):
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