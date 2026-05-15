import os
import ctypes
from ctypes import wintypes
from app.actions.base import Action


# ── WinAPI bindings ──────────────────────────────────────────────────
user32 = ctypes.WinDLL("user32", use_last_error=True)

EnumWindowsProc = ctypes.WINFUNCTYPE(
    wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
)

user32.RegisterWindowMessageW.argtypes = [wintypes.LPCWSTR]
user32.RegisterWindowMessageW.restype  = wintypes.UINT

user32.EnumWindows.argtypes  = [EnumWindowsProc, wintypes.LPARAM]
user32.EnumWindows.restype   = wintypes.BOOL

user32.GetClassNameW.argtypes  = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.restype   = ctypes.c_int

user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype  = ctypes.c_int

user32.SendMessageW.argtypes = [
    wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
]
user32.SendMessageW.restype = wintypes.LPARAM


def search_for_window(wndclass, title):
    """
    Аналог SearchForWindow из C#.
    Ищет первое окно, у которого имя класса начинается с wndclass
    и заголовок начинается с title. Пустая строка совпадает с любым.
    """
    found = {"hwnd": 0}

    def enum_proc(hwnd):
        cls_buf = ctypes.create_unicode_buffer(1024)
        user32.GetClassNameW(hwnd, cls_buf, 1024)
        if not cls_buf.value.startswith(wndclass):
            return True

        title_buf = ctypes.create_unicode_buffer(1024)
        user32.GetWindowTextW(hwnd, title_buf, 1024)
        if not title_buf.value.startswith(title):
            return True

        found["hwnd"] = hwnd
        return False  # остановить перебор

    user32.EnumWindows(EnumWindowsProc(enum_proc), 0)
    return found["hwnd"]


def set_uni_filter(filter_text, uni_path, window_titles):
    """
    1. Записывает filter_text в .UNI-файл
    2. Регистрирует сообщение UniStat2003
    3. Шлёт его в каждое окно из window_titles
    Возвращает список заголовков, в которые сообщение было отправлено.
    """
    # UNI-файл пишется в кодировке Windows (cp1251) — программа на Delphi
    # обычно ждёт именно такой формат
    with open(uni_path, "w", encoding="cp1251", errors="replace") as f:
        f.write(filter_text)

    msg_id = user32.RegisterWindowMessageW("UniStat2003")
    if not msg_id:
        raise RuntimeError("Не удалось зарегистрировать сообщение UniStat2003")

    sent_to = []
    for title in window_titles:
        hwnd = search_for_window("", title)
        if hwnd:
            user32.SendMessageW(hwnd, msg_id, 0, 0)
            sent_to.append(title)
    return sent_to


# ── Action ───────────────────────────────────────────────────────────
class UniStat2003Action(Action):
    name = "UniStat2003.UNI (фильтр)"
    param_labels = {
        "filter":         "Содержимое фильтра",
        "uni_path":       "Путь к .UNI файлу",
        "window_titles":  "Заголовки окон (по одному на строку)",
        "require_any":    "Требовать хотя бы одно окно",
    }
    param_widgets = {
        "filter":        "multiline",
        "window_titles": "multiline",
    }
    icon = "⚖"

    def execute(self, context):
        filter_text = self.params.get("filter", "")
        uni_path    = self.params.get("uni_path", "").strip()
        titles_raw  = self.params.get("window_titles", "")
        require_any = bool(self.params.get("require_any", False))

        if not uni_path:
            raise ValueError("Путь к .UNI файлу не задан")

        # Создаём директорию если её нет
        os.makedirs(os.path.dirname(uni_path), exist_ok=True)

        titles = [t.strip() for t in titles_raw.splitlines() if t.strip()]
        if not titles:
            raise ValueError("Не указано ни одного заголовка окна")

        sent_to = set_uni_filter(filter_text, uni_path, titles)

        context["uni_sent_to"]    = sent_to
        context["uni_sent_count"] = len(sent_to)

        if require_any and not sent_to:
            raise RuntimeError("Не найдено ни одного целевого окна UniStat2003")