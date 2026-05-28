import re


def resolve_vars(text, context):
    """
    Заменяет {a}, {a.b}, {a.b.c} в строке на значения из контекста.
    Поддерживает любую глубину вложенности dict.
    Значение-list/dict не подставляется (оставляется как есть).
    """
    if not isinstance(text, str) or "{" not in text:
        return text

    def repl(match):
        expr = match.group(1).strip()
        parts = expr.split(".")
        obj = context.get(parts[0])
        for p in parts[1:]:
            if isinstance(obj, dict) and p in obj:
                obj = obj[p]
            else:
                return match.group(0)
        if isinstance(obj, (dict, list)):
            return match.group(0)
        return "" if obj is None else str(obj)

    return re.sub(r"\{([^{}]+)\}", repl, text)


def short_value(v, maxlen=120):
    """Компактное строковое представление значения для лога."""
    if v is None:
        return "NULL"
    if isinstance(v, dict):
        inner = ", ".join(f"{k}={short_value(val, 60)}" for k, val in v.items())
        return "{" + inner + "}"
    if isinstance(v, list):
        return f"[{len(v)} строк]"
    s = str(v)
    if s == "":
        return "'' (пусто)"
    return s if len(s) <= maxlen else s[:maxlen] + "…"


class Action:
    name = "Base"
    icon = "•"
    file_params = ()
    param_labels = {}
    param_options = {}
    param_widgets = {}

    def __init__(self, params):
        self.params = params

    def execute(self, context):
        raise NotImplementedError

    def execute_with_resolved(self, context):
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
        Возвращает узел дерева переменных или None.
        Узел: { "label": str, "drag": Optional[str], "children": [узел, ...] }
        """
        return None