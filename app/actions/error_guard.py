import ctypes
from ctypes import wintypes

from app.actions.base import Action


class ErrorGuardAction(Action):
    """
    Сторож ошибок приложения: ищет видимое окно, чей заголовок содержит один из
    заданных образцов (по одному в строке — «Ошибка», «Внимание» и т.п.).
    Если нашёл — по возможности читает текст окна, пишет в лог и (по умолчанию)
    роняет шаг с ошибкой. Падение автоматически делает снимок экрана и может
    быть поймано через «Попробовать/Обработка ошибки», чтобы пометить задачу
    проблемной и перейти к следующей.

    Это НЕ про исключения бота, а про ошибки самого приложения (Delphi-диалоги),
    которые иначе остаются незамеченными.
    """
    name = "Проверка на ошибку (окно)"
    icon = "⛔"
    param_labels = {
        "titles":    "Заголовки окон-ошибок (по одному в строке)",
        "read_text": "Прочитать текст окна (да/нет)",
        "on_found":  "При обнаружении",
        "out_name":  "Имя переменной результата",
    }
    param_widgets = {"titles": "multiline"}
    param_options = {"on_found": ["ошибка", "только пометить"]}

    def execute(self, context):
        titles_raw = self.params.get("titles", "") or ""
        patterns = [t.strip().lower() for t in titles_raw.splitlines() if t.strip()]
        read_text = str(self.params.get("read_text", "да")).strip().lower() in ("да", "1", "true", "yes")
        on_found = (self.params.get("on_found") or "ошибка").strip()
        out_name = (self.params.get("out_name") or "err").strip() or "err"
        log = context.get("_log")

        if not patterns:
            # нечего искать — считаем, что ошибок нет
            context[out_name] = {"found": "0", "title": "", "text": ""}
            return

        found_title = self._find_error_window(patterns)

        if not found_title:
            context[out_name] = {"found": "0", "title": "", "text": ""}
            return

        text = ""
        if read_text:
            text = self._read_window_text(found_title)

        context[out_name] = {"found": "1", "title": found_title, "text": text}

        msg = f"⛔ Обнаружено окно ошибки: «{found_title}»"
        if text:
            short = text if len(text) <= 300 else text[:300] + "…"
            msg += f" — {short}"
        if log:
            log(msg)

        if on_found == "ошибка":
            raise RuntimeError(msg)

    # ── поиск окна ошибки по заголовку (без OpenCV) ──────────────────
    @staticmethod
    def _find_error_window(patterns):
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.IsWindowVisible.argtypes = [wintypes.HWND]

        result = {"title": ""}

        def cb(hwnd, lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            buf = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, buf, 512)
            title = buf.value
            low = title.lower()
            for p in patterns:
                if p in low:
                    result["title"] = title
                    return False
            return True

        user32.EnumWindows(EnumWindowsProc(cb), 0)
        return result["title"]

    # ── чтение текста окна (best-effort через pywinauto) ─────────────
    @staticmethod
    def _read_window_text(title):
        try:
            from pywinauto import Desktop
            esc = title.replace("\\", r"\\").replace(".", r"\.").replace("(", r"\(").replace(")", r"\)")
            win = Desktop(backend="win32").window(title_re=f".*{esc}.*")
            parts = []
            for child in win.children():
                try:
                    txt = child.window_text()
                    if txt and txt.strip() and txt.strip().lower() not in ("ok", "ок", "отмена", "cancel", "&ok"):
                        parts.append(txt.strip())
                except Exception:
                    continue
            # убираем дубли, сохраняя порядок
            seen = set()
            uniq = [p for p in parts if not (p in seen or seen.add(p))]
            return " | ".join(uniq)
        except Exception:
            return ""

    def output_vars(self):
        name = (self.params.get("out_name") or "err").strip() or "err"
        return {
            "label": name,
            "drag": None,
            "children": [
                {"label": "found", "drag": f"{{{name}.found}}"},
                {"label": "title", "drag": f"{{{name}.title}}"},
                {"label": "text",  "drag": f"{{{name}.text}}"},
            ],
        }
