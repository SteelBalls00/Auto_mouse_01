from app.actions.base import Action


class DebugPauseAction(Action):
    name = "Перейти в пошаговый режим"
    icon = "🔍"
    param_labels = {
        "message": "Сообщение в лог (необязательно)",
    }

    def execute(self, context):
        # Устанавливаем флаг пошагового режима в контексте.
        # Runner проверяет его в начале каждого следующего шага.
        context["_step_mode_active"] = True
        msg = self.params.get("message", "").strip()
        log = context.get("_log")
        if log:
            log(msg if msg else "🔍 Переход в пошаговый режим")