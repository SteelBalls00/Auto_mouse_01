from app.actions.base import Action


class SeparatorAction(Action):
    """
    Визуальный разделитель этапов сценария.
    Сам по себе ничего не делает — только помечает границу этапа.
    В списке шагов рисуется увеличенной цветной строкой (см. main_window).
    """
    name = "Разделитель / этап"
    icon = "🏷"
    param_labels = {
        "text":  "Подпись этапа",
        "color": "Цвет фона",
    }
    param_widgets = {
        "color": "color",
    }

    def execute(self, context):
        log = context.get("_log")
        text = (self.params.get("text") or "").strip()
        if log and text:
            log(f"━━━━━ {text} ━━━━━")
