import time
import ctypes

from app.actions.base import Action


# Виртуальные коды клавиш
VK_CONTROL = 0x11
VK_V = 0x56
KEYEVENTF_KEYUP = 0x0002

_keybd_event = ctypes.WinDLL("user32").keybd_event


class PasteTextAction(Action):
    name = "Вставка из буфера (Win32)"
    param_labels = {
        "text":     "Текст",
        "delay_ms": "Задержка после вставки (мс)",
        "restore":  "Вернуть старый буфер",
    }
    param_options = {
        "restore": ["", "да"],
    }
    icon = "📋"

    def execute(self, context):
        text = self.params.get("text", "")
        if text is None:
            text = ""
        text = str(text)

        delay_ms = self._to_float(self.params.get("delay_ms", 300)) / 1000
        restore = str(self.params.get("restore", "")).strip().lower() in ("да", "1", "true")

        # ── Подробный лог: что и откуда вставляем ─────────────────────
        log = context.get("_log")
        if log:
            raw = ""
            if isinstance(getattr(self, "_raw_params", None), dict):
                raw = str(self._raw_params.get("text", "") or "")
            src = f"{raw} → " if (raw and raw != text) else ""
            preview = text if len(text) <= 200 else text[:200] + "…"
            log(f"📋 Вставка: {src}'{preview}' ({len(text)} симв.)")
            # Предупреждения о подозрительных случаях
            if text == "":
                log("   ⚠ значение ПУСТОЕ — в буфер уйдёт пустая строка")
            elif "{" in text and "}" in text:
                log("   ⚠ остался неподставленный плейсхолдер — переменная не "
                    "найдена/пуста, вставляется как есть")

        old_clipboard = self._get_clipboard() if restore else None

        # кладём текст в буфер
        self._set_clipboard(text)

        # проверяем, что буфер действительно принял наш текст
        if log:
            try:
                got = self._get_clipboard()
                if got != text:
                    g = got if len(str(got)) <= 200 else str(got)[:200] + "…"
                    log(f"   ⚠ буфер обмена НЕ совпал с ожидаемым! в буфере: '{g}'")
            except Exception as e:
                log(f"   ⚠ не удалось перечитать буфер: {e}")

        # нажимаем Ctrl+V через низкоуровневый keybd_event
        _keybd_event(VK_CONTROL, 0, 0, 0)            # Ctrl down
        _keybd_event(VK_V, 0, 0, 0)                  # V down
        _keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)    # V up
        _keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)  # Ctrl up

        # ждём, пока приложение успеет прочитать буфер и обработать вставку
        if delay_ms > 0:
            time.sleep(delay_ms)

        # при необходимости возвращаем прежнее содержимое буфера
        if restore and old_clipboard is not None:
            self._set_clipboard(old_clipboard)

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _open_clipboard():
        """OpenClipboard с парой повторов — буфер может быть занят другим процессом."""
        import win32clipboard
        last_err = None
        for _ in range(10):
            try:
                win32clipboard.OpenClipboard()
                return
            except Exception as e:
                last_err = e
                time.sleep(0.05)
        if last_err:
            raise last_err

    @classmethod
    def _set_clipboard(cls, text):
        import win32clipboard
        cls._open_clipboard()
        try:
            win32clipboard.EmptyClipboard()
            # CF_UNICODETEXT обязателен для корректной кириллицы
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
        finally:
            win32clipboard.CloseClipboard()

    @classmethod
    def _get_clipboard(cls):
        import win32clipboard
        cls._open_clipboard()
        try:
            try:
                return win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            except Exception:
                return ""
        finally:
            win32clipboard.CloseClipboard()

    @staticmethod
    def _to_float(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0
