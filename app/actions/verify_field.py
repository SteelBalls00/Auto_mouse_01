import time

import pyautogui as pg

from app.actions.base import Action


class VerifyFieldAction(Action):
    """
    Проверка значения в поле через буфер обмена (для приложений вроде старого
    Delphi, где UIA не видит отдельные поля).

    Выделяет содержимое (по умолчанию Ctrl+A), копирует (Ctrl+C), читает буфер
    и сравнивает с ожидаемым значением. Результат кладётся в переменную
    <out_name>: ok (1/0), actual (что в поле), expected (что ждали).
    При несовпадении может либо предупредить в лог, либо упасть с ошибкой
    (чтобы поймать через «Попытка/Обработка ошибки» и повторить).
    """
    name = "Сверить поле (через буфер)"
    icon = "🔎"
    param_labels = {
        "expected":     "Ожидаемое значение",
        "select_combo": "Клавиши выделения",
        "compare":      "Сравнение",
        "on_mismatch":  "При несовпадении",
        "out_name":     "Имя переменной результата",
        "delay_ms":     "Пауза перед чтением буфера (мс)",
    }
    param_options = {
        "select_combo": ["ctrl+a", "home+shift+end", "(не выделять)"],
        "compare":      ["обрезка пробелов", "точное", "без регистра", "содержит"],
        "on_mismatch":  ["предупредить", "ошибка"],
    }

    def execute(self, context):
        expected = str(self.params.get("expected", "") or "")
        select_combo = str(self.params.get("select_combo", "ctrl+a") or "").strip()
        compare = str(self.params.get("compare", "обрезка пробелов") or "").strip()
        on_mismatch = str(self.params.get("on_mismatch", "предупредить") or "").strip()
        out_name = str(self.params.get("out_name", "check") or "check").strip() or "check"
        delay_ms = self._to_float(self.params.get("delay_ms", 150)) / 1000

        log = context.get("_log")

        # 1) выделяем содержимое поля
        if select_combo and select_combo != "(не выделять)":
            for part in select_combo.split():
                keys = [k.strip() for k in part.lower().split("+") if k.strip()]
                if keys:
                    pg.hotkey(*keys)
                    time.sleep(0.05)

        # 2) копируем в буфер
        pg.hotkey("ctrl", "c")
        if delay_ms > 0:
            time.sleep(delay_ms)

        # 3) читаем буфер
        actual = self._get_clipboard()

        # 4) сравниваем
        ok = self._compare(actual, expected, compare)

        context[out_name] = {
            "ok": "1" if ok else "0",
            "actual": actual,
            "expected": expected,
        }

        if log:
            a = actual if len(actual) <= 200 else actual[:200] + "…"
            e = expected if len(expected) <= 200 else expected[:200] + "…"
            if ok:
                log(f"🔎 Сверка [{out_name}]: совпало — '{a}'")
            else:
                log(f"🔎 Сверка [{out_name}]: НЕ совпало! ждали '{e}', в поле '{a}'")

        if not ok and on_mismatch == "ошибка":
            raise RuntimeError(
                f"Сверка поля не прошла: ждали '{expected}', в поле '{actual}'"
            )

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _compare(actual, expected, mode):
        a = "" if actual is None else str(actual)
        e = "" if expected is None else str(expected)
        if mode == "точное":
            return a == e
        if mode == "без регистра":
            return a.strip().lower() == e.strip().lower()
        if mode == "содержит":
            return e.strip() in a
        # по умолчанию — обрезка пробелов
        return a.strip() == e.strip()

    @classmethod
    def _get_clipboard(cls):
        import win32clipboard
        last_err = None
        for _ in range(10):
            try:
                win32clipboard.OpenClipboard()
                break
            except Exception as e:
                last_err = e
                time.sleep(0.05)
        else:
            if last_err:
                raise last_err
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

    def output_vars(self):
        name = str(self.params.get("out_name", "check") or "check").strip() or "check"
        return {
            "label": name,
            "drag": None,
            "children": [
                {"label": "ok",       "drag": f"{{{name}.ok}}"},
                {"label": "actual",   "drag": f"{{{name}.actual}}"},
                {"label": "expected", "drag": f"{{{name}.expected}}"},
            ],
        }
