import subprocess
from app.actions.base import Action


class RunProgramAction(Action):
    name = "Запустить программу"
    param_labels = {"path": "Путь к программе"}
    icon = "🚀"

    def execute(self, context):
        path = self.params["path"]
        if not path:
            raise ValueError("Путь к программе не задан")
        subprocess.Popen(path, shell=True)
