import time
from app.actions.base import Action


class WaitAction(Action):
    name = "Пауза"
    param_labels = {"ms": "Время (мс)"}
    icon = "⏱"

    def execute(self, context):
        ms = int(self.params.get("ms", 1000))
        log = context.get("_log")
        if log:
            if ms >= 1000 and ms % 1000 == 0:
                log(f"⏱ Пауза {ms // 1000} c")
            elif ms >= 1000:
                log(f"⏱ Пауза {ms / 1000:.1f} c ({ms} мс)")
            else:
                log(f"⏱ Пауза {ms} мс")
        stop = context.get("stop_event")
        # ждём кусочками по 50 мс, проверяя стоп
        slept = 0
        while slept < ms:
            if stop is not None and stop.is_set():
                return  # выходим из шага, runner увидит stop и завершится
            step = min(50, ms - slept)
            time.sleep(step / 1000.0)
            slept += step