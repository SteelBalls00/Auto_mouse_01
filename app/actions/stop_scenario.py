from app.actions.base import Action


class StopScenarioAction(Action):
    """
    Завершить выполнение ВСЕГО сценария немедленно (в отличие от «Прервать»,
    которое выходит лишь из текущего цикла). Полезно для аварийного выхода —
    например, нет связи с БД.
    Режим завершения: «успех» (как нормальное окончание) или «ошибка»
    (зафиксировать как сбой — например для бота, чтобы пометить неуспех).
    """
    name = "Завершить сценарий"
    icon = "🏁"
    param_labels = {
        "reason": "Причина (в лог)",
        "mode":   "Как завершить",
    }
    param_options = {"mode": ["успех", "ошибка"]}

    def execute(self, context):
        reason = (self.params.get("reason") or "").strip()
        mode = (self.params.get("mode") or "успех").strip()
        # Движок проверяет этот флаг в начале каждого шага и завершает сценарий.
        context["_stop_scenario"] = {
            "reason": reason,
            "as_error": (mode == "ошибка"),
        }
        log = context.get("_log")
        if log:
            log(f"🏁 Запрошено завершение сценария"
                + (f": {reason}" if reason else ""))
