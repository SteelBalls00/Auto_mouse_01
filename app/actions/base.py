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


def collect_substitutions(params, context):
    """
    Возвращает [(param_name, '{placeholder}', resolved_value), ...] для всех
    плейсхолдеров вида {ns} / {ns.field}, где ns реально есть в контексте.
    `{...}`-выражения, чьего пространства имён в контексте нет (например, обычные
    словарные литералы в Python-коде), пропускаются — это не настоящие подстановки.
    """
    subs = []
    seen = set()
    for key, val in params.items():
        if not isinstance(val, str) or "{" not in val:
            continue
        for m in re.finditer(r"\{([^{}]+)\}", val):
            ph = m.group(0)
            if (key, ph) in seen:
                continue
            seen.add((key, ph))
            expr = m.group(1).strip()
            parts = expr.split(".")
            ns = parts[0]
            if ns not in context:
                continue
            obj = context.get(ns)
            ok = True
            for p in parts[1:]:
                if isinstance(obj, dict) and p in obj:
                    obj = obj[p]
                else:
                    ok = False
                    break
            if not ok:
                subs.append((key, ph, "<поле не найдено>"))
                continue
            if isinstance(obj, (dict, list)):
                continue  # объекты целиком в текст не подставляются
            subs.append((key, ph, "NULL" if obj is None else str(obj)))
    return subs


def log_substitutions(params, context):
    """Если в контексте есть _log — пишет подстановки одной строкой на каждую."""
    log = context.get("_log") if isinstance(context, dict) else None
    if not log:
        return
    for key, ph, val in collect_substitutions(params, context):
        log(f"· {key}: {ph} = {short_value(val)}")


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
        log_substitutions(self.params, context)
        original = self.params
        self._raw_params = original          # до подстановки — для логов действия
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