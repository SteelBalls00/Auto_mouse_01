# actions/wait.py
import time
from actions.base import Action

class WaitAction(Action):
    name = "Wait"

    def execute(self, context):
        time.sleep(self.params["ms"] / 1000)
