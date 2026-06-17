from app.actions.base import Action


class ExitStepModeAction(Action):
    name = "Выйти из пошагового режима"
    icon = "▶"
    param_labels = {
        "message": "Сообщение в лог (необязательно)",
    }

    def execute(self, context):
        # Снимаем флаг пошагового режима — дальше шаги идут подряд.
        context["_step_mode_active"] = False
        msg = (self.params.get("message") or "").strip()
        log = context.get("_log")
        if log:
            log(msg if msg else "▶ Выход из пошагового режима")
