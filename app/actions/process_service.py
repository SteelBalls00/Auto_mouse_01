import subprocess
from app.actions.base import Action


class KillProcessAction(Action):
    name = "Завершить процесс"
    icon = "💀"
    param_labels = {
        "by":            "Искать по",
        "value":         "Имя процесса или заголовок окна",
        "result_name":   "Имя результата (для переменных)",
    }
    param_options = {
        "by": ["process_name", "window_title"],
    }

    def execute(self, context):
        import psutil

        by    = self.params.get("by", "process_name")
        value = (self.params.get("value") or "").strip()
        rname = (self.params.get("result_name") or "").strip() or "kill"
        if not value:
            raise ValueError("Не задано имя процесса/заголовок")

        killed = 0

        if by == "process_name":
            target = value.lower()
            for p in psutil.process_iter(["name"]):
                try:
                    pname = (p.info["name"] or "").lower()
                    if pname == target or target in pname:
                        p.kill()
                        killed += 1
                except Exception:
                    continue
        else:
            # По заголовку окна → находим PID окна → убиваем
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.WinDLL("user32", use_last_error=True)
            EnumWindowsProc = ctypes.WINFUNCTYPE(
                wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
            )
            user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
            user32.IsWindowVisible.argtypes = [wintypes.HWND]

            pids = set()

            def cb(hwnd, lparam):
                if not user32.IsWindowVisible(hwnd):
                    return True
                buf = ctypes.create_unicode_buffer(512)
                user32.GetWindowTextW(hwnd, buf, 512)
                if value.lower() in buf.value.lower():
                    pid = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    pids.add(pid.value)
                return True

            user32.EnumWindows(EnumWindowsProc(cb), 0)
            for pid in pids:
                try:
                    psutil.Process(pid).kill()
                    killed += 1
                except Exception:
                    continue

        context[rname] = {"killed": killed}

    def output_vars(self):
        rname = (self.params.get("result_name") or "").strip()
        if not rname:
            return None
        return {
            "label": rname,
            "children": [{"label": "killed", "drag": f"{{{rname}.killed}}"}],
        }


class StartServiceAction(Action):
    name = "Запустить службу"
    icon = "▶"
    param_labels = {"service": "Имя службы (sc-имя)"}

    def execute(self, context):
        service = (self.params.get("service") or "").strip()
        if not service:
            raise ValueError("Имя службы не задано")
        r = subprocess.run(
            ["sc", "start", service],
            capture_output=True, text=True, encoding="cp866", errors="replace"
        )
        # 1056 = уже запущена — не считаем ошибкой
        if r.returncode not in (0, 1056):
            raise RuntimeError(f"Не удалось запустить службу: {r.stdout}{r.stderr}")


class StopServiceAction(Action):
    name = "Остановить службу"
    icon = "⏹"
    param_labels = {"service": "Имя службы (sc-имя)"}

    def execute(self, context):
        service = (self.params.get("service") or "").strip()
        if not service:
            raise ValueError("Имя службы не задано")
        r = subprocess.run(
            ["sc", "stop", service],
            capture_output=True, text=True, encoding="cp866", errors="replace"
        )
        # 1062 = уже остановлена
        if r.returncode not in (0, 1062):
            raise RuntimeError(f"Не удалось остановить службу: {r.stdout}{r.stderr}")