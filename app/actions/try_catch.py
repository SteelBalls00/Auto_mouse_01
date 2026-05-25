from app.actions.base import Action


class TryStartAction(Action):
    name = "ПОПРОБОВАТЬ"
    icon = "🛡"
    param_labels = {
        "try_name": "Имя блока (для переменной ошибки)",
    }

    def execute(self, context):
        pass  # Обрабатывается в runner

    def output_vars(self):
        try_name = (self.params.get("try_name") or "").strip()
        if not try_name:
            return None
        return {
            "label": try_name,
            "children": [
                {"label": "error",  "drag": f"{{{try_name}.error}}"},
                {"label": "failed", "drag": f"{{{try_name}.failed}}"},
                {"label": "step",   "drag": f"{{{try_name}.step}}"},
            ],
        }


class CatchAction(Action):
    name = "ПРИ ОШИБКЕ"
    icon = "🩹"

    def execute(self, context):
        pass


class EndTryAction(Action):
    name = "КОНЕЦ ОБРАБОТКИ"
    icon = "🔚"

    def execute(self, context):
        pass