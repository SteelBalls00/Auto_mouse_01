import ctypes
from ctypes import wintypes
from app.actions.base import Action

user32 = ctypes.WinDLL("user32", use_last_error=True)

# Константы ShowWindow
SW = {
    "hide":          0,   # SW_HIDE
    "normal":        1,   # SW_SHOWNORMAL
    "minimize":      6,   # SW_MINIMIZE
    "maximize":      3,   # SW_MAXIMIZE
    "restore":       9,   # SW_RESTORE
    "show":          5,   # SW_SHOW
    "topmost":      -1,   # спец-обработка ниже
}

# Константы SetWindowPos
HWND_TOP       = 0
HWND_TOPMOST   = -1
HWND_NOTOPMOST = -2
SWP_NOSIZE     = 0x0001
SWP_NOMOVE     = 0x0002
SWP_SHOWWINDOW = 0x0040

EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.GetWindowTextW.argtypes  = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.IsWindowVisible.argtypes = [wintypes.HWND]


def _find_hwnd(title):
    """Первое видимое окно, чей заголовок содержит title (без учёта регистра)."""
    found = {"hwnd": 0}
    needle = (title or "").lower()

    def cb(hwnd, lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, buf, 512)
        if needle in buf.value.lower():
            found["hwnd"] = hwnd
            return False
        return True

    user32.EnumWindows(EnumWindowsProc(cb), 0)
    return found["hwnd"]


def _resolve_hwnd(self, context):
    """Берём окно либо по переменной (из «Найти окно»), либо по заголовку."""
    win_var = (self.params.get("window_var") or "").strip()
    if win_var and win_var in context:
        data = context[win_var]
        if isinstance(data, dict) and data.get("_search", {}).get("title"):
            hwnd = _find_hwnd(data["_search"]["title"])
            if hwnd:
                return hwnd
    title = (self.params.get("title") or "").strip()
    if title:
        hwnd = _find_hwnd(title)
        if hwnd:
            return hwnd
    raise RuntimeError("Окно не найдено (укажите переменную окна или заголовок)")


class WindowStateAction(Action):
    name = "Состояние окна"
    icon = "🗔"
    param_labels = {
        "window_var": "Переменная окна (из «Найти окно»)",
        "title":      "ИЛИ заголовок окна (частично)",
        "state":      "Действие",
    }
    param_options = {
        "state": ["minimize", "maximize", "restore", "normal",
                  "hide", "show", "topmost", "untopmost", "close"],
    }

    def execute(self, context):
        hwnd  = _resolve_hwnd(self, context)
        state = self.params.get("state", "restore")

        if state == "close":
            WM_CLOSE = 0x0010
            user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        elif state == "topmost":
            user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                                SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
        elif state == "untopmost":
            user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0,
                                SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
        else:
            user32.ShowWindow(hwnd, SW.get(state, 9))


class WindowMoveAction(Action):
    name = "Переместить окно"
    icon = "↔"
    param_labels = {
        "window_var": "Переменная окна",
        "title":      "ИЛИ заголовок окна",
        "x":          "X (левый край)",
        "y":          "Y (верхний край)",
    }

    def execute(self, context):
        hwnd = _resolve_hwnd(self, context)
        x = int(self.params.get("x", 0))
        y = int(self.params.get("y", 0))
        # перемещаем без изменения размера
        user32.SetWindowPos(hwnd, HWND_TOP, x, y, 0, 0,
                            SWP_NOSIZE | SWP_SHOWWINDOW)


class WindowResizeAction(Action):
    name = "Изменить размер окна"
    icon = "⤡"
    param_labels = {
        "window_var": "Переменная окна",
        "title":      "ИЛИ заголовок окна",
        "width":      "Ширина",
        "height":     "Высота",
    }

    def execute(self, context):
        hwnd = _resolve_hwnd(self, context)
        w = int(self.params.get("width", 800))
        h = int(self.params.get("height", 600))
        # меняем размер без перемещения
        user32.SetWindowPos(hwnd, HWND_TOP, 0, 0, w, h,
                            SWP_NOMOVE | SWP_SHOWWINDOW)


class WindowMoveResizeAction(Action):
    name = "Окно: позиция и размер"
    icon = "🗗"
    param_labels = {
        "window_var": "Переменная окна",
        "title":      "ИЛИ заголовок окна",
        "x":          "X",
        "y":          "Y",
        "width":      "Ширина",
        "height":     "Высота",
    }

    def execute(self, context):
        hwnd = _resolve_hwnd(self, context)
        x = int(self.params.get("x", 0))
        y = int(self.params.get("y", 0))
        w = int(self.params.get("width", 800))
        h = int(self.params.get("height", 600))
        # bRepaint=True
        user32.MoveWindow(hwnd, x, y, w, h, True)


class WindowSendMessageAction(Action):
    name = "Окну: отправить WinMessage"
    icon = "✉"
    param_labels = {
        "window_var": "Переменная окна",
        "title":      "ИЛИ заголовок окна",
        "msg":        "Сообщение (число или имя)",
        "wparam":     "wParam",
        "lparam":     "lParam",
        "post":       "PostMessage (иначе SendMessage)",
    }
    param_options = {
        "msg": ["WM_CLOSE", "WM_QUIT", "WM_DESTROY", "WM_PAINT",
                "WM_SYSCOMMAND", "произвольное"],
    }

    # Карта частых сообщений
    MSG_MAP = {
        "WM_CLOSE":     0x0010,
        "WM_QUIT":      0x0012,
        "WM_DESTROY":   0x0002,
        "WM_PAINT":     0x000F,
        "WM_SYSCOMMAND": 0x0112,
    }

    def execute(self, context):
        hwnd = _resolve_hwnd(self, context)

        msg_raw = (self.params.get("msg") or "").strip()
        if msg_raw in self.MSG_MAP:
            msg = self.MSG_MAP[msg_raw]
        else:
            # произвольное — берём wparam/lparam, а сам msg ожидаем числом в title? нет.
            # Если выбрано "произвольное" — msg должен быть числом, но в комбобоксе строка.
            # Поддержим: если msg_raw число — используем его.
            try:
                msg = int(msg_raw, 0)
            except (ValueError, TypeError):
                raise ValueError(
                    "Для произвольного сообщения впишите число в поле «Сообщение» "
                    "(например 0x0010 или 16)"
                )

        try:
            wparam = int(str(self.params.get("wparam", 0)), 0)
        except (ValueError, TypeError):
            wparam = 0
        try:
            lparam = int(str(self.params.get("lparam", 0)), 0)
        except (ValueError, TypeError):
            lparam = 0

        if self.params.get("post", True):
            user32.PostMessageW(hwnd, msg, wparam, lparam)
        else:
            user32.SendMessageW(hwnd, msg, wparam, lparam)