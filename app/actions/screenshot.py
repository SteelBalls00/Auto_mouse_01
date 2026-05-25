import os
from datetime import datetime
from app.actions.base import Action


class ScreenshotAction(Action):
    name = "Скриншот"
    icon = "📸"
    param_labels = {
        "mode":       "Что снимать",
        "title":      "Заголовок окна (для режима «окно»)",
        "x":          "X (для области)",
        "y":          "Y (для области)",
        "width":      "Ширина (для области)",
        "height":     "Высота (для области)",
        "folder":     "Папка сохранения (пусто = logs/screenshots)",
        "result_name": "Имя результата (для переменной с путём)",
    }
    param_options = {
        "mode": ["весь экран", "окно", "область"],
    }

    def execute(self, context):
        import pyautogui as pg

        mode   = self.params.get("mode", "весь экран")
        rname  = (self.params.get("result_name") or "").strip() or "shot"
        folder = (self.params.get("folder") or "").strip()

        if not folder:
            root = os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__))))
            folder = os.path.join(root, "logs", "screenshots")
        os.makedirs(folder, exist_ok=True)

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        path  = os.path.join(folder, f"shot_{stamp}.png")

        if mode == "область":
            region = (
                int(self.params.get("x", 0)),
                int(self.params.get("y", 0)),
                int(self.params.get("width", 100)),
                int(self.params.get("height", 100)),
            )
            img = pg.screenshot(region=region)

        elif mode == "окно":
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            EnumWindowsProc = ctypes.WINFUNCTYPE(
                wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
            user32.IsWindowVisible.argtypes = [wintypes.HWND]

            title  = (self.params.get("title") or "").strip().lower()
            target = {"hwnd": 0}

            def cb(hwnd, lparam):
                if not user32.IsWindowVisible(hwnd):
                    return True
                buf = ctypes.create_unicode_buffer(512)
                user32.GetWindowTextW(hwnd, buf, 512)
                if title in buf.value.lower():
                    target["hwnd"] = hwnd
                    return False
                return True

            user32.EnumWindows(EnumWindowsProc(cb), 0)
            if not target["hwnd"]:
                raise RuntimeError(f"Окно не найдено: {title}")

            rect = wintypes.RECT()
            user32.GetWindowRect(target["hwnd"], ctypes.byref(rect))
            region = (rect.left, rect.top,
                      rect.right - rect.left, rect.bottom - rect.top)
            img = pg.screenshot(region=region)
        else:
            img = pg.screenshot()

        img.save(path)
        context[rname] = {"path": path}

    def output_vars(self):
        rname = (self.params.get("result_name") or "").strip()
        if not rname:
            return None
        return {
            "label": rname,
            "children": [{"label": "path", "drag": f"{{{rname}.path}}"}],
        }