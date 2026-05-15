import pyautogui as pg
import pyperclip
from app.actions.base import Action


class TypeTextAction(Action):
    name = "Ввод текста"
    param_labels = {
        "text":  "Текст",
        "enter": "Нажать Enter",
        "delay": "Задержка между сим. (мс)",
    }
    icon = "⌨"

    def execute(self, context):
        text = self.params.get("text", "")

        # Проверяем есть ли не-ASCII символы (кириллица и т.д.)
        if any(ord(c) > 127 for c in text):
            # Вставляем через буфер обмена — единственный надёжный способ
            old_clipboard = pyperclip.paste()
            pyperclip.copy(text)
            pg.hotkey("ctrl", "v")
            pyperclip.copy(old_clipboard)  # восстанавливаем буфер
        else:
            delay = self.params.get("delay", 0) / 1000
            pg.write(text, interval=delay)

        if self.params.get("enter"):
            pg.press("enter")
