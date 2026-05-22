import pyautogui as pg
from app.actions.base import Action
from app.actions.image_utils import find_image_on_screen


class CheckImageAction(Action):
    name = "Проверить изображение"
    icon = "🔍"
    file_params = ("image",)
    param_labels = {
        "check_name": "Имя проверки (для переменных)",
        "image":      "Путь к изображению",
        "confidence": "Точность (0.0–1.0)",
    }

    def execute(self, context):
        check_name = (self.params.get("check_name") or "").strip() or "img_check"
        loc = find_image_on_screen(
            self.params["image"],
            confidence=float(self.params.get("confidence", 0.8)),
        )
        if loc:
            x, y, w, h = loc
            context[check_name] = {
                "found": 1,
                "x": x + w // 2,
                "y": y + h // 2,
            }
        else:
            context[check_name] = {"found": 0, "x": "", "y": ""}

    def output_vars(self):
        check_name = (self.params.get("check_name") or "").strip()
        if not check_name:
            return None
        return {
            "label": check_name,
            "children": [
                {"label": "found", "drag": f"{{{check_name}.found}}"},
                {"label": "x",     "drag": f"{{{check_name}.x}}"},
                {"label": "y",     "drag": f"{{{check_name}.y}}"},
            ],
        }


class CheckProcessAction(Action):
    name = "Проверить процесс"
    icon = "🔎"
    param_labels = {
        "check_name":   "Имя проверки (для переменных)",
        "process_name": "Имя процесса (например app.exe)",
    }

    def execute(self, context):
        import psutil

        check_name = (self.params.get("check_name") or "").strip() or "proc_check"
        target = (self.params.get("process_name") or "").strip().lower()
        if not target:
            raise ValueError("Имя процесса не задано")

        running = 0
        pid = ""
        for p in psutil.process_iter(["name"]):
            try:
                pname = (p.info["name"] or "").lower()
            except Exception:
                continue
            if pname == target or target in pname:
                running = 1
                pid = p.pid
                break

        context[check_name] = {"running": running, "pid": pid}

    def output_vars(self):
        check_name = (self.params.get("check_name") or "").strip()
        if not check_name:
            return None
        return {
            "label": check_name,
            "children": [
                {"label": "running", "drag": f"{{{check_name}.running}}"},
                {"label": "pid",     "drag": f"{{{check_name}.pid}}"},
            ],
        }


class CheckWindowAction(Action):
    name = "Проверить окно"
    icon = "🪟"
    param_labels = {
        "check_name": "Имя проверки (для переменных)",
        "title":      "Заголовок окна (частично)",
    }

    def execute(self, context):
        import ctypes
        from ctypes import wintypes

        check_name = (self.params.get("check_name") or "").strip() or "win_check"
        title = (self.params.get("title") or "").strip()
        if not title:
            raise ValueError("Заголовок окна не задан")

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        EnumWindowsProc = ctypes.WINFUNCTYPE(
            wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
        )
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.IsWindowVisible.argtypes = [wintypes.HWND]

        found = {"v": 0}

        def cb(hwnd, lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            buf = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, buf, 512)
            if title.lower() in buf.value.lower():
                found["v"] = 1
                return False
            return True

        user32.EnumWindows(EnumWindowsProc(cb), 0)
        context[check_name] = {"exists": found["v"]}

    def output_vars(self):
        check_name = (self.params.get("check_name") or "").strip()
        if not check_name:
            return None
        return {
            "label": check_name,
            "children": [
                {"label": "exists", "drag": f"{{{check_name}.exists}}"},
            ],
        }