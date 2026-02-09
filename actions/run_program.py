# actions/run_program.py
import subprocess
from actions.base import Action

class RunProgramAction(Action):
    name = "Run Program"

    def execute(self, context):
        subprocess.Popen(self.params["path"])
