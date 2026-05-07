import pyautogui as pg
from actions.base import Action

KNOWN_KEYS = [
    "enter", "esc", "tab", "space", "backspace", "delete",
    "up", "down", "left", "right",
    "home", "end", "pageup", "pagedown",
    "f1", "f2", "f3", "f4", "f5", "f6",
    "f7", "f8", "f9", "f10", "f11", "f12",
    "ctrl", "alt", "shift", "win",
    "insert", "capslock", "numlock", "scrolllock",
    "printscreen", "pause",
]


class PressKeyAction(Action):
    name = "Нажатие клавиши"
    param_labels = {
        "key":      "Клавиша",
        "combo":    "Комбинация (ctrl+c, alt+f4, …)",
        "times":    "Количество нажатий",
        "delay_ms": "Задержка между нажатиями (мс)",
    }
    param_options = {
        "key": KNOWN_KEYS,
    }
    icon = "🔘"

    def execute(self, context):
        combo    = self.params.get("combo", "").strip()
        key      = self.params.get("key", "").strip()
        times    = int(self.params.get("times", 1))
        delay_ms = float(self.params.get("delay_ms", 0)) / 1000

        if combo:
            keys = [k.strip() for k in combo.lower().split("+")]
            for i in range(times):
                pg.hotkey(*keys)
                if delay_ms and i < times - 1:
                    import time
                    time.sleep(delay_ms)
        elif key:
            pg.press(key.lower(), presses=times, interval=delay_ms)
        else:
            raise ValueError("Задайте клавишу или комбинацию")