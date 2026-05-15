from app.actions.base import Action


class ForEachStartAction(Action):
    name = "ЦИКЛ по списку"
    icon = "🔁"
    param_labels = {
        "loop_name": "Имя цикла",
        "source":    "Имя переменной-списка",
        "columns":   "Колонки текущего элемента (через запятую)",
    }

    def execute(self, context):
        pass  # Обрабатывается в runner

    def output_vars(self):
        loop_name = (self.params.get("loop_name") or "").strip()
        cols_raw  = self.params.get("columns", "")
        cols      = [c.strip() for c in cols_raw.split(",") if c.strip()]
        if not loop_name:
            return None
        current_children = [
            {"label": c, "drag": f"{{{loop_name}.current.{c}}}"} for c in cols
        ]
        return {
            "label": loop_name,
            "children": [
                {"label": "index", "drag": f"{{{loop_name}.index}}"},
                {"label": "count", "drag": f"{{{loop_name}.count}}"},
                {"label": "current", "children": current_children},
            ],
        }


class EndForAction(Action):
    name = "КОНЕЦ ЦИКЛА"
    icon = "🔚"

    def execute(self, context):
        pass


class BreakAction(Action):
    name = "ПРЕРВАТЬ ЦИКЛ"
    icon = "🛑"

    def execute(self, context):
        pass


class ContinueAction(Action):
    name = "СЛЕДУЮЩАЯ ИТЕРАЦИЯ"
    icon = "⏭"

    def execute(self, context):
        pass