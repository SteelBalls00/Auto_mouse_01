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

        if self.action_type == "for_each_start":
            loop_name = self.params.get("loop_name", "") or "?"
            source    = self.params.get("source", "")    or "?"
            return f"ЦИКЛ {loop_name} по {source}"

        if self.action_type == "run_scenario":
            path = self.params.get("scenario_path", "") or "?"
            short = os.path.basename(os.path.dirname(path)) if path else "?"
            return f"Запустить сценарий: {short}"

        if self.action_type == "while_start":
            left = self.params.get("left", "") or "?"
            op = self.params.get("operator", "")
            right = self.params.get("right", "") or ""
            if op in ("пусто", "не пусто"):
                return f"ПОКА {left} {op}"
            return f"ПОКА {left} {op} {right}"

        if self.action_type in (
                "else", "end_if", "end_for", "end_while",
                "break", "continue"
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