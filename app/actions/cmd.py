import subprocess
from app.actions.base import Action


class CmdAction(Action):
    name = "Команда оболочки"
    param_labels = {
        "command": "Команда",
        "timeout": "Таймаут (сек)",
        "capture": "Сохранить вывод в контекст",
    }
    icon = "⚡"

    def execute(self, context):
        command = self.params.get("command", "")
        if not command:
            raise ValueError("Команда не задана")

        timeout = float(self.params.get("timeout", 30))
        capture = self.params.get("capture", False)

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )

        if capture:
            context["cmd_stdout"] = result.stdout.strip()
            context["cmd_stderr"] = result.stderr.strip()
            context["cmd_returncode"] = result.returncode

        if result.returncode != 0:
            raise RuntimeError(
                f"Команда завершилась с кодом {result.returncode}:\n{result.stderr}"
            )
