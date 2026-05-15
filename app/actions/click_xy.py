import pyautogui as pg
from app.actions.base import Action


class ClickXYAction(Action):
    name = "Клик по координатам"
    param_labels = {"x": "X", "y": "Y"}
    icon = "🖱"

    def execute(self, context):
        pg.click(self.params["x"], self.params["y"])
