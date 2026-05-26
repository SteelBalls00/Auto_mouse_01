from app.actions.base import Action


class LogMessageAction(Action):
    name = "Записать в лог"
    icon = "📝"
    param_labels = {
        "message": "Сообщение (можно {переменные})",
    }
    param_widgets = {
        "message": "multiline",
    }

    def execute(self, context):
        msg = self.params.get("message", "")
        log = context.get("_log")
        if log:
            log(msg)