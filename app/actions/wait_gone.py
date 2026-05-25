import time
from app.actions.base import Action


class WaitImageGoneAction(Action):
    name = "Ждать исчезновения изображения"
    icon = "👻"
    file_params = ("image",)
    param_labels = {
        "image":      "Путь к изображению",
        "timeout":    "Таймаут (сек)",
        "confidence": "Точность (0.0–1.0)",
    }

    def execute(self, context):
        from app.actions.image_utils import find_image_on_screen

        image   = self.params["image"]
        conf    = float(self.params.get("confidence", 0.8))
        timeout = float(self.params.get("timeout", 30))
        stop    = context.get("stop_event")

        start = time.time()
        while time.time() - start < timeout:
            if stop and stop.is_set():
                return
            if find_image_on_screen(image, confidence=conf) is None:
                return  # изображение исчезло — успех
            time.sleep(0.5)
        raise RuntimeError("Изображение всё ещё на экране (таймаут)")


class WaitWindowGoneAction(Action):
    name = "Ждать закрытия окна"
    icon = "🚪"
    param_labels = {
        "title":   "Заголовок окна (частично)",
        "timeout": "Таймаут (сек)",
    }

    def execute(self, context):
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        EnumWindowsProc = ctypes.WINFUNCTYPE(
            wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.IsWindowVisible.argtypes = [wintypes.HWND]

        title   = (self.params.get("title") or "").strip().lower()
        timeout = float(self.params.get("timeout", 30))
        stop    = context.get("stop_event")

        def exists():
            found = {"v": False}
            def cb(hwnd, lparam):
                if not user32.IsWindowVisible(hwnd):
                    return True
                buf = ctypes.create_unicode_buffer(512)
                user32.GetWindowTextW(hwnd, buf, 512)
                if title in buf.value.lower():
                    found["v"] = True
                    return False
                return True
            user32.EnumWindows(EnumWindowsProc(cb), 0)
            return found["v"]

        start = time.time()
        while time.time() - start < timeout:
            if stop and stop.is_set():
                return
            if not exists():
                return  # окно закрылось
            time.sleep(0.5)
        raise RuntimeError(f"Окно «{title}» всё ещё открыто (таймаут)")