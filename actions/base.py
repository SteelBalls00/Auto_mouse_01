import re


def resolve_vars(text, context):
    """
    Заменяет {query_name.column} и {key} в строке на значения из контекста.
    Контекст может содержать как простые значения, так и dict-ы (от SQL).
    """
    if not isinstance(text, str) or "{" not in text:
        return text

    def repl(match):
        expr = match.group(1).strip()
        if "." in expr:
            ns, field = expr.split(".", 1)
            obj = context.get(ns)
            if isinstance(obj, dict) and field in obj:
                v = obj[field]
                return "" if v is None else str(v)
            return match.group(0)
        else:
            if expr in context:
                v = context[expr]
                if isinstance(v, dict):
                    return match.group(0)  # нельзя вставить dict как строку
                return "" if v is None else str(v)
            return match.group(0)

    return re.sub(r"\{([^{}]+)\}", repl, text)


class Action:
    name = "Base"
    icon = "•"     # Эмодзи / символ для кнопки в палитре
    # { "key": "Человеческое название" }
    param_labels = {}
    # { "key": ["вариант1", "вариант2", ...] } — поле станет комбобоксом
    param_options = {}
    # { "key": "multiline" } — виджет будет QPlainTextEdit вместо QLineEdit
    param_widgets = {}

    def __init__(self, params):
        self.params = params

    def execute(self, context):
        raise NotImplementedError

    def execute_with_resolved(self, context):
        """
        Выполнить execute() с подменой строковых параметров на значения из context.
        Подставляет {var} и {ns.field}. Не модифицирует self.params навсегда.
        """
        original = self.params
        self.params = {
            k: resolve_vars(v, context) if isinstance(v, str) else v
            for k, v in original.items()
        }
        try:
            self.execute(context)
        finally:
            self.params = original

    def output_vars(self):
        """
        Возвращает namespace и список имён колонок, которые этот шаг
        делает доступными следующим шагам. По умолчанию ничего.
        Override в SQL action.
        Returns: (namespace_str, [col1, col2, ...]) или None.
        """
        return None