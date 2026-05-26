import time

import pyautogui as pg
import pyperclip
from app.actions.base import Action


class TypeTextAction(Action):
    name = "Ввод текста"
    param_labels = {
        "text":            "Текст",
        "enter":           "Нажать Enter",
        "delay":           "Задержка между сим. (мс)",
        "force_clipboard": "Всегда через буфер",
        "paste_wait_ms":   "Пауза после вставки (мс)",
    }
    param_options = {
        "force_clipboard": ["", "да"],
    }
    icon = "⌨"

    def execute(self, context):
        text = self.params.get("text", "")

        force_clip = str(self.params.get("force_clipboard", "")).strip().lower() in ("да", "1", "true")
        has_unicode = any(ord(c) > 127 for c in text)

        if has_unicode or force_clip:
            self._paste_via_clipboard(text)
        else:
            delay = self._to_float(self.params.get("delay", 0)) / 1000
            pg.write(text, interval=delay)

        if self.params.get("enter"):
            # небольшая пауза, чтобы поле успело принять вставленный текст
            time.sleep(0.10)
            pg.press("enter")

    # ------------------------------------------------------------------ helpers

    def _paste_via_clipboard(self, text):
        """
        Надёжная вставка кириллицы через буфер.

        Ключевой момент: pg.hotkey('ctrl','v') только отправляет нажатия в
        очередь сообщений и сразу возвращается. Само WM_PASTE приложение
        (особенно Delphi) обрабатывает асинхронно, ПОЗЖE. Поэтому буфер
        нельзя восстанавливать сразу — иначе приложение прочитает уже
        затёртое (старое/пустое) значение и вставка «не происходит».
        """
        paste_wait = self._to_float(self.params.get("paste_wait_ms", 250)) / 1000
        if paste_wait <= 0:
            paste_wait = 0.25

        try:
            old_clipboard = pyperclip.paste()
        except Exception:
            old_clipboard = ""

        pyperclip.copy(text)
        time.sleep(0.05)  # даём буферу «осесть» перед вставкой

        # сбрасываем возможно зажатые модификаторы — частая причина,
        # когда Ctrl+V приходит как Ctrl+Ctrl+V и игнорируется
        for k in ("ctrl", "shift", "alt"):
            pg.keyUp(k)

        pg.hotkey("ctrl", "v")

        # КРИТИЧНО: ждём, пока приложение реально прочитает буфер,
        # и только потом восстанавливаем старое содержимое
        time.sleep(paste_wait)

        try:
            pyperclip.copy(old_clipboard)
        except Exception:
            pass

    @staticmethod
    def _to_float(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0
