import pyautogui as pg
from actions.base import Action

class TypeTextAction(Action):
    name = "Type Text"

    def execute(self, context):
        pg.write(self.params["text"])
        if self.params.get("enter"):
            pg.press("enter")
