import time
from app.actions.base import Action


class WaitAction(Action):
    name = "Пауза"
    param_labels = {"ms": "Время (мс)"}
    icon = "⏱"

    def execute(self, context):
        time.sleep(self.params["ms"] / 1000)
