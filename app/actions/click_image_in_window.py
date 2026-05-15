import time
import pygetwindow as gw
import pyautogui as pg
from app.actions.base import Action
from app.actions.image_utils import find_image_in_region


class ClickImageInWindowAction(Action):
    name = "Клик по изображению в окне"
    icon = "🪟"
    file_params = ("image",)
    param_labels = {
        "window_title": "Заголовок окна",
        "image":        "Путь к изображению",
        "timeout":      "Таймаут (сек)",
        "confidence":   "Точность (0.0–1.0)",
    }

    def execute(self, context):
        title      = self.params["window_title"]
        image      = self.params["image"]
        confidence = float(self.params["confidence"])
        timeout    = float(self.params["timeout"])
        stop_event = context.get("stop_event")

        wins = gw.getWindowsWithTitle(title)
        if not wins:
            raise RuntimeError(f"Окно не найдено: «{title}»")

        win = wins[0]
        region = (win.left, win.top, win.width, win.height)

        start = time.time()
        while time.time() - start < timeout:
            if stop_event and stop_event.is_set():
                return
            pos = find_image_in_region(region, image, confidence)
            if pos:
                pg.click(pos)
                context["last_image_xy"] = pos
                return
            time.sleep(0.5)

        raise RuntimeError(f"Изображение не найдено в окне «{title}»")
