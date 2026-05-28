import os

from app.actions.registry import ACTION_REGISTRY


class ActionModel:
    def __init__(self, action_type, params, enabled=True):
        self.action_type = action_type
        self.params      = params
        self.enabled     = bool(enabled)

    def title(self):
        cls = ACTION_REGISTRY[self.action_type][0]

        if self.action_type == "if_start":
            left  = self.params.get("left", "")  or "?"
            op    = self.params.get("operator", "")
            right = self.params.get("right", "") or ""
            if op in ("пусто", "не пусто"):
                return f"ЕСЛИ {left} {op}"
            return f"ЕСЛИ {left} {op} {right}"

        if self.action_type == "try_start":
            return f"ПОПРОБОВАТЬ ({self.params.get('try_name', 'try')})"

        if self.action_type == "for_each_start":
            loop_name = self.params.get("loop_name", "") or "?"
            source    = self.params.get("source", "")    or "?"
            return f"ЦИКЛ {loop_name} по {source}"

        if self.action_type == "run_scenario":
            task = (self.params.get("task_name") or "").strip()
            path = self.params.get("scenario_path", "") or "?"
            short = os.path.basename(os.path.dirname(path)) if path else "?"
            if task:
                return f"Запустить: {task} ({short})"
            return f"Запустить сценарий: {short}"

        if self.action_type == "separator":
            return (self.params.get("text") or "").strip() or "— этап —"

        if self.action_type == "while_start":
            left = self.params.get("left", "") or "?"
            op = self.params.get("operator", "")
            right = self.params.get("right", "") or ""
            if op in ("пусто", "не пусто"):
                return f"ПОКА {left} {op}"
            return f"ПОКА {left} {op} {right}"

        if self.action_type == "repeat_start":
            return f"ПОВТОРИТЬ {self.params.get('times', '?')} раз"

        if self.action_type in (
                "else", "end_if", "end_for", "end_while",
                "break", "continue", "end_repeat", "catch", "end_try",
        ):
            return cls.name

        hint = ""
        for v in self.params.values():
            if isinstance(v, str) and v.strip():
                short = v.strip()
                hint = f" — {short[:30]}{'…' if len(short) > 30 else ''}"
                break
        return cls.name + hint

    def to_dict(self):
        d = {"type": self.action_type, "params": self.params}
        if not self.enabled:
            d["enabled"] = False
        return d

    @staticmethod
    def from_dict(data):
        return ActionModel(
            data["type"],
            data.get("params", {}),
            data.get("enabled", True),
        )


def collect_available_vars(actions, before_index):
    """
    Собирает все имена переменных (drag-строки вида '{ns.field}'),
    которые экспортируют шаги ДО before_index.
    Возвращает set строк без скобок: {'cases.current.ID', 'task.FIO', ...}
    """
    from app.actions.registry import ACTION_REGISTRY

    names = set()

    def walk(node):
        drag = node.get("drag")
        if drag:
            # '{cases.ID}' → 'cases.ID'
            inner = drag.strip()
            if inner.startswith("{") and inner.endswith("}"):
                names.add(inner[1:-1])
        for child in node.get("children", []) or []:
            walk(child)

    for idx, model in enumerate(actions):
        if idx >= before_index:
            break
        cls = ACTION_REGISTRY.get(model.action_type, (None,))[0]
        if cls is None:
            continue
        try:
            action = cls(model.params)
            node = action.output_vars()
        except Exception:
            node = None
        if node:
            walk(node)

    return names