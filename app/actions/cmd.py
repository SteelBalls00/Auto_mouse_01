import subprocess

from app.actions.base import Action


def _decode(data):
    """Декодировать вывод консоли Windows. cmd.exe обычно отдаёт OEM-кодировку
    (cp866 на русской Windows), а не utf-8 — пробуем по очереди."""
    if data is None:
        return ""
    if isinstance(data, str):
        return data
    for enc in ("utf-8", "oem", "cp866", "cp1251"):
        try:
            return data.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return data.decode("utf-8", errors="replace")


class CmdAction(Action):
    name = "Команда оболочки"
    icon = "⚡"
    param_labels = {
        "command":       "Команда",
        "op_name":       "Имя операции (namespace переменных)",
        "timeout":       "Таймаут (сек)",
        "fail_on_error": "Ошибка при коде возврата ≠ 0",
    }

    def execute(self, context):
        command = self.params.get("command", "")
        if not command:
            raise ValueError("Команда не задана")

        op_name = (self.params.get("op_name") or "cmd").strip() or "cmd"
        timeout = float(self.params.get("timeout", 30))
        fail_on_error = str(self.params.get("fail_on_error", "да")).strip().lower() \
            in ("да", "1", "true", "yes", "")

        # Захватываем БАЙТЫ и декодируем сами (правильная кодировка консоли)
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            timeout=timeout,
        )
        stdout = _decode(result.stdout).strip()
        stderr = _decode(result.stderr).strip()

        context[op_name] = {
            "stdout": stdout,
            "stderr": stderr,
            "returncode": result.returncode,
        }

        log = context.get("_log")
        if log:
            log(f"⚡ [{op_name}] код возврата {result.returncode}")
            if stdout:
                short = stdout if len(stdout) <= 300 else stdout[:300] + "…"
                log(f"    stdout: {short}")
            if stderr:
                short = stderr if len(stderr) <= 300 else stderr[:300] + "…"
                log(f"    stderr: {short}")

        if fail_on_error and result.returncode != 0:
            raise RuntimeError(
                f"Команда завершилась с кодом {result.returncode}:\n{stderr or stdout}"
            )

    def output_vars(self):
        name = (self.params.get("op_name") or "cmd").strip() or "cmd"
        return {
            "label": name,
            "drag": None,
            "children": [
                {"label": "stdout",     "drag": f"{{{name}.stdout}}"},
                {"label": "stderr",     "drag": f"{{{name}.stderr}}"},
                {"label": "returncode", "drag": f"{{{name}.returncode}}"},
            ],
        }
