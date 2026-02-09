import pyautogui as pg
from actions.base import Action

class ClickXYAction(Action):
    name = "Click XY"

    def execute(self, context):
        pg.click(self.params["x"], self.params["y"])
