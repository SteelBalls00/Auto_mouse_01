from actions.registry import ACTION_REGISTRY


class ActionModel:
    def __init__(self, action_type, params):
        self.action_type = action_type
        self.params = params

    def title(self):
        cls = ACTION_REGISTRY[self.action_type][0]
        # Спец-форматирование для условий
        if self.action_type == "if_start":
            left  = self.params.get("left", "")  or "?"
            op    = self.params.get("operator", "")
            right = self.params.get("right", "") or ""
            if op in ("пусто", "не пусто"):
                return f"ЕСЛИ {left} {op}"
            return f"ЕСЛИ {left} {op} {right}"
        if self.action_type in ("else", "end_if"):
            return cls.name

        # Краткое описание: имя + первый непустой строковый параметр
        hint = ""
        for v in self.params.values():
            if isinstance(v, str) and v.strip():
                short = v.strip()
                hint = f" — {short[:30]}{'…' if len(short) > 30 else ''}"
                break
        return cls.name + hint

    def to_dict(self):
        return {"type": self.action_type, "params": self.params}

    @staticmethod
    def from_dict(data):
        return ActionModel(data["type"], data.get("params", {}))
