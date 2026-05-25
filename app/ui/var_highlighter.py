import re
from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor


class VarHighlighter(QSyntaxHighlighter):
    """
    Подсвечивает {переменные} в QTextDocument:
      зелёный — переменная существует в known_vars
      красный — не найдена
    Для loop-переменных с .current. и .index/.count проверяет префикс.
    """
    def __init__(self, document):
        super().__init__(document)
        self.known = set()

        self.fmt_ok = QTextCharFormat()
        self.fmt_ok.setForeground(QColor("#16a34a"))
        self.fmt_ok.setFontWeight(75)

        self.fmt_bad = QTextCharFormat()
        self.fmt_bad.setForeground(QColor("#dc2626"))
        self.fmt_bad.setFontWeight(75)

        self.pattern = QRegExp(r"\{[^{}]+\}")

    def set_known(self, known_vars):
        self.known = set(known_vars)
        self.rehighlight()

    def _is_known(self, expr):
        expr = expr.strip()
        if expr in self.known:
            return True
        # Прямое совпадение по полному пути
        # Для случаев {loop.current.X} — проверяем что есть ровно такой drag
        # (output_vars циклов отдают current.X как drag, так что попадёт в known)
        # Доп.проверка: системные поля index/count
        if expr.endswith(".index") or expr.endswith(".count"):
            ns = expr.rsplit(".", 1)[0]
            # есть ли хоть одна переменная с этим namespace
            return any(k == expr or k.startswith(ns + ".") for k in self.known)
        return False

    def highlightBlock(self, text):
        idx = self.pattern.indexIn(text, 0)
        while idx >= 0:
            length = self.pattern.matchedLength()
            token  = text[idx:idx + length]      # '{cases.ID}'
            expr   = token[1:-1]                 # 'cases.ID'
            fmt = self.fmt_ok if self._is_known(expr) else self.fmt_bad
            self.setFormat(idx, length, fmt)
            idx = self.pattern.indexIn(text, idx + length)