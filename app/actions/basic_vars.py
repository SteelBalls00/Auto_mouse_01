from app.actions.base import Action


class SetVariableAction(Action):
    name = "Задать переменную"
    icon = "📌"
    param_labels = {
        "var_name": "Имя переменной",
        "value":    "Значение (можно {другие.переменные})",
    }

    def execute(self, context):
        var_name = (self.params.get("var_name") or "").strip()
        if not var_name:
            raise ValueError("Имя переменной не задано")
        # value уже подставлен через execute_with_resolved
        context[var_name] = {"value": self.params.get("value", "")}

    def output_vars(self):
        var_name = (self.params.get("var_name") or "").strip()
        if not var_name:
            return None
        return {
            "label": var_name,
            "children": [{"label": "value", "drag": f"{{{var_name}.value}}"}],
        }


class RepeatStartAction(Action):
    name = "ПОВТОРИТЬ N раз"
    icon = "🔁"
    param_labels = {
        "loop_name": "Имя цикла",
        "times":     "Сколько раз",
    }

    def execute(self, context):
        pass  # Обрабатывается в runner

    def output_vars(self):
        loop_name = (self.params.get("loop_name") or "").strip()
        if not loop_name:
            return None
        return {
            "label": loop_name,
            "children": [
                {"label": "index", "drag": f"{{{loop_name}.index}}"},
                {"label": "count", "drag": f"{{{loop_name}.count}}"},
            ],
        }


class EndRepeatAction(Action):
    name = "КОНЕЦ ПОВТОРА"
    icon = "🔚"

    def execute(self, context):
        pass