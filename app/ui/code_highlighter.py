from PyQt5.QtCore import QRegExp, Qt
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont


def _fmt(color, bold=False, italic=False):
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold:
        f.setFontWeight(QFont.Bold)
    if italic:
        f.setFontItalic(True)
    return f


SQL_KEYWORDS = [
    "SELECT", "FROM", "WHERE", "AND", "OR", "NOT", "NULL", "IS", "IN", "LIKE",
    "AS", "JOIN", "LEFT", "RIGHT", "INNER", "OUTER", "FULL", "ON", "ORDER", "BY",
    "GROUP", "HAVING", "DISTINCT", "FIRST", "SKIP", "ROWS", "CASE", "WHEN",
    "THEN", "ELSE", "END", "UPDATE", "SET", "INSERT", "INTO", "VALUES", "DELETE",
    "CREATE", "ALTER", "DROP", "TABLE", "INDEX", "VIEW", "PROCEDURE", "TRIGGER",
    "BEGIN", "COMMIT", "ROLLBACK", "EXECUTE", "RETURNING", "COLLATE", "ASC",
    "DESC", "BETWEEN", "EXISTS", "UNION", "ALL", "CONSTRAINT", "PRIMARY", "KEY",
    "FOREIGN", "REFERENCES", "DEFAULT", "CURRENT_TIMESTAMP", "CURRENT_DATE",
    "CURRENT_TIME", "COUNT", "SUM", "AVG", "MIN", "MAX", "UPPER", "LOWER",
    "SUBSTRING", "COALESCE", "CAST", "TRIM",
]

PY_KEYWORDS = [
    "False", "None", "True", "and", "as", "assert", "async", "await", "break",
    "class", "continue", "def", "del", "elif", "else", "except", "finally",
    "for", "from", "global", "if", "import", "in", "is", "lambda", "nonlocal",
    "not", "or", "pass", "raise", "return", "try", "while", "with", "yield",
]

PY_BUILTINS = [
    "print", "len", "range", "int", "str", "float", "bool", "list", "dict",
    "set", "tuple", "abs", "min", "max", "sum", "sorted", "enumerate", "zip",
    "open", "isinstance", "type", "format",
]


class CodeHighlighter(QSyntaxHighlighter):
    """
    Подсветка синтаксиса SQL или Python + подсветка {переменных}.
    Один документ = один highlighter, поэтому всё в одном классе.

    Цвета переменных:
      зелёный фон/текст — переменная есть в known
      красный фон/текст — не найдена
    """
    def __init__(self, document, language="sql"):
        super().__init__(document)
        self.known = set()
        self.language = language

        # форматы переменных (фон, чтобы выделялись даже внутри строк)
        self.fmt_var_ok = _fmt("#15803d", bold=True)
        self.fmt_var_ok.setBackground(QColor("#dcfce7"))
        self.fmt_var_bad = _fmt("#b91c1c", bold=True)
        self.fmt_var_bad.setBackground(QColor("#fee2e2"))
        self.var_pattern = QRegExp(r"\{[^{}]+\}")

        self._build_rules()

    # ── публичный API (совместим с VarHighlighter) ───────────────────
    def set_known(self, known):
        self.known = set(known)
        self.rehighlight()

    def set_language(self, language):
        self.language = language
        self._build_rules()
        self.rehighlight()

    # ── правила ──────────────────────────────────────────────────────
    def _build_rules(self):
        self.rules = []           # [(QRegExp, format)]
        self.fmt_string = _fmt("#b45309")          # строки — коричнево-оранжевый
        self.fmt_comment = _fmt("#6b7280", italic=True)  # комментарии — серый курсив
        self.fmt_number = _fmt("#0e7490")          # числа — бирюзовый

        kw_fmt = _fmt("#2563eb", bold=True)        # ключевые слова — синий

        if self.language == "python":
            for kw in PY_KEYWORDS:
                self.rules.append((QRegExp(r"\b" + kw + r"\b"), kw_fmt))
            blt_fmt = _fmt("#7c3aed")              # builtins — фиолетовый
            for b in PY_BUILTINS:
                self.rules.append((QRegExp(r"\b" + b + r"\b"), blt_fmt))
            self._line_comment = "#"
            self._block_delims = [("'''", "'''"), ('"""', '"""')]
        else:  # sql
            kw_re = QRegExp(r"\b(" + "|".join(SQL_KEYWORDS) + r")\b")
            kw_re.setCaseSensitivity(Qt.CaseInsensitive)
            self.rules.append((kw_re, kw_fmt))
            self._line_comment = "--"
            self._block_delims = [("/*", "*/")]

        # числа
        self.rules.append((QRegExp(r"\b[0-9]+(\.[0-9]+)?\b"), self.fmt_number))
        # строки в одинарных и двойных кавычках (однострочные)
        self.rules.append((QRegExp(r"'[^']*'"), self.fmt_string))
        self.rules.append((QRegExp(r'"[^"]*"'), self.fmt_string))

        self.rehighlight()

    # ── собственно подсветка ─────────────────────────────────────────
    def highlightBlock(self, text):
        # 1) однострочные правила
        for pattern, fmt in self.rules:
            idx = pattern.indexIn(text, 0)
            while idx >= 0:
                length = pattern.matchedLength()
                if length <= 0:
                    break
                self.setFormat(idx, length, fmt)
                idx = pattern.indexIn(text, idx + length)

        # 2) однострочные комментарии (после строк, чтобы '--' внутри строки не ловить — упрощённо)
        lc = self._line_comment
        pos = text.find(lc)
        if pos >= 0:
            self.setFormat(pos, len(text) - pos, self.fmt_comment)

        # 3) многострочные строки/комментарии через состояния блоков
        self._highlight_multiline(text)

        # 4) переменные {var} — поверх всего
        idx = self.var_pattern.indexIn(text, 0)
        while idx >= 0:
            length = self.var_pattern.matchedLength()
            token = text[idx:idx + length]
            expr = token[1:-1].strip()
            fmt = self.fmt_var_ok if self._is_known(expr) else self.fmt_var_bad
            self.setFormat(idx, length, fmt)
            idx = self.var_pattern.indexIn(text, idx + length)

    def _highlight_multiline(self, text):
        """Подсветка блоков, переходящих через строки (/* */ или '''/\"\"\")."""
        delims = self._block_delims
        # состояние = индекс открытого разделителя + 1, иначе 0
        start_state = self.previousBlockState()
        fmt = self.fmt_comment if self.language != "python" else self.fmt_string

        # Если уже внутри блока — ищем закрытие
        if start_state > 0:
            di = start_state - 1
            open_d, close_d = delims[di]
            end = text.find(close_d)
            if end == -1:
                self.setFormat(0, len(text), fmt)
                self.setCurrentBlockState(start_state)
                return
            self.setFormat(0, end + len(close_d), fmt)
            search_from = end + len(close_d)
        else:
            search_from = 0

        # Ищем новые открытия блоков на этой строке
        while True:
            best_idx = -1
            best_di = -1
            for di, (open_d, close_d) in enumerate(delims):
                p = text.find(open_d, search_from)
                if p >= 0 and (best_idx == -1 or p < best_idx):
                    best_idx = p
                    best_di = di
            if best_idx == -1:
                self.setCurrentBlockState(0)
                return
            open_d, close_d = delims[best_di]
            end = text.find(close_d, best_idx + len(open_d))
            if end == -1:
                self.setFormat(best_idx, len(text) - best_idx, fmt)
                self.setCurrentBlockState(best_di + 1)
                return
            self.setFormat(best_idx, end + len(close_d) - best_idx, fmt)
            search_from = end + len(close_d)

    # ── проверка переменных (как в VarHighlighter) ───────────────────
    def _is_known(self, expr):
        if expr in self.known:
            return True
        if expr.endswith(".index") or expr.endswith(".count"):
            ns = expr.rsplit(".", 1)[0]
            return any(k == expr or k.startswith(ns + ".") for k in self.known)
        return False
