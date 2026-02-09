import time
import pygetwindow as gw
import pyautogui as pg
from actions.base import Action
from actions.image_utils import find_image_in_region

class ClickImageInWindowAction(Action):
    name = "Click Image In Window"

    def execute(self, context):
        title = self.params["window_title"]
        image = self.params["image"]
        confidence = self.params["confidence"]
        timeout = self.params["timeout"]

        wins = gw.getWindowsWithTitle(title)
        if not wins:
            raise RuntimeError("Window not found")

        win = wins[0]
        region = (win.left, win.top, win.width, win.height)

        start = time.time()
        while time.time() - start < timeout:
            pos = find_image_in_region(region, image, confidence)
            if pos:
                pg.click(pos)
                context["last_image_xy"] = pos
                return
            time.sleep(0.5)

        raise RuntimeError("Image not found in window")
