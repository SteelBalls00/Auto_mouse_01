import time

from app.actions.base import Action, resolve_vars


class WaitUntilAction(Action):
    """
    Ждать наступления условия с таймаутом (вместо фиксированной паузы).
    Виды условий:
      • окно появилось / окно исчезло — по заголовку (regex, частично) и/или классу;
      • поле = / содержит — копирует текущее поле (Ctrl+C) и сверяет с ожидаемым.
    Если за timeout условие не наступило — ошибка (можно ловить через try/catch).
    """
    name = "Ждать пока…"
    icon = "⏳"
    param_labels = {
        "kind":       "Условие",
        "backend":    "Бэкенд окна (win32/uia)",
        "title":      "Заголовок окна (частично, regex)",
        "class_name": "Класс окна",
        "expected":   "Ожидаемое значение поля",
        "timeout":    "Таймаут (сек)",
        "interval":   "Интервал проверки (сек)",
    }
    param_options = {
        "kind": [
            "окно появилось",
            "окно исчезло",
            "поле равно",
            "поле содержит",
        ],
        "backend": ["win32", "uia"],
    }

    def execute(self, context):
        kind = (self.params.get("kind") or "окно появилось").strip()
        timeout = self._to_float(self.params.get("timeout", 30))
        interval = self._to_float(self.params.get("interval", 0.5)) or 0.5
        stop_event = context.get("stop_event")
        log = context.get("_log")

        start = time.time()
        attempt = 0
        while True:
            if stop_event is not None and stop_event.is_set():
                raise RuntimeError("Остановлено пользователем во время ожидания")

            attempt += 1
            ok, detail = self._check(kind, context)
            if ok:
                if log:
                    log(f"⏳ дождались ({kind}) за {time.time() - start:.1f} c")
                return

            if time.time() - start >= timeout:
                raise TimeoutError(
                    f"Не дождались условия «{kind}» за {timeout:.0f} c"
                    + (f" — {detail}" if detail else "")
                )
            time.sleep(interval)

    # ── проверка одного условия ──────────────────────────────────────
    def _check(self, kind, context):
        if kind in ("окно появилось", "окно исчезло"):
            exists = self._window_exists(context)
            if kind == "окно появилось":
                return exists, "окно ещё не найдено"
            return (not exists), "окно ещё на экране"

        if kind in ("поле равно", "поле содержит"):
            expected = resolve_vars(str(self.params.get("expected", "") or ""), context)
            actual = self._copy_field()
            if kind == "поле равно":
                return actual.strip() == expected.strip(), f"в поле '{actual}'"
            return expected.strip() in actual, f"в поле '{actual}'"

        return False, "неизвестное условие"

    def _window_exists(self, context):
        from app.actions.window import _find_window_spec
        backend = (self.params.get("backend") or "win32").strip() or "win32"
        title = (self.params.get("title") or "").strip() or None
        class_name = (self.params.get("class_name") or "").strip() or None
        try:
            spec = _find_window_spec(backend, title, class_name, None)
            return bool(spec.exists())
        except Exception:
            return False

    @staticmethod
    def _copy_field():
        import pyautogui as pg
        pg.hotkey("ctrl", "c")
        time.sleep(0.1)
        try:
            import win32clipboard
            for _ in range(10):
                try:
                    win32clipboard.OpenClipboard()
                    break
                except Exception:
                    time.sleep(0.05)
            try:
                try:
                    return win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                except Exception:
                    return ""
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            return ""

    @staticmethod
    def _to_float(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0
