import pyautogui as pg
from actions.base import Action
from actions.image_utils import wait_for_image


class WaitImageAction(Action):
    name = "Ждать изображение"
    param_labels = {
        "image":      "Путь к изображению",
        "timeout":    "Таймаут (сек)",
        "confidence": "Точность (0.0–1.0)",
    }
    icon = "👁"

    def execute(self, context):
        loc = wait_for_image(
            self.params["image"],
            timeout=float(self.params["timeout"]),
            confidence=float(self.params["confidence"]),
            stop_event=context.get("stop_event"),
        )
        if loc is None:
            raise RuntimeError("Изображение не найдено (таймаут)")
        context["last_image"] = loc


class ClickImageAction(Action):
    name = "Клик по изображению"
    param_labels = {
        "image":      "Путь к изображению",
        "timeout":    "Таймаут (сек)",
        "confidence": "Точность (0.0–1.0)",
    }
    icon = "🎯"

    def execute(self, context):
        loc = wait_for_image(
            self.params["image"],
            timeout=float(self.params["timeout"]),
            confidence=float(self.params["confidence"]),
            stop_event=context.get("stop_event"),
        )
        if loc is None:
            raise RuntimeError("Изображение не найдено")
        pg.click(pg.center(loc))
        context["last_image"] = loc
