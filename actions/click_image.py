import pyautogui as pg
from actions.base import Action
from actions.image_utils import wait_for_image

class ClickImageAction(Action):
    name = "Click Image"

    def execute(self, context):
        loc = wait_for_image(
            self.params["image"],
            timeout=self.params["timeout"],
            confidence=self.params["confidence"]
        )

        if not loc:
            raise RuntimeError("Image not found")

        pg.click(pg.center(loc))
        context["last_image"] = loc
