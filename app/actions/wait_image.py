'''
Таймаут (сек) — сколько максимально секунд ждать, пока изображение появится на экране. Программа делает скриншоты примерно раз в полсекунды и сравнивает с твоей картинкой. Если за указанное время не нашла — шаг падает с ошибкой «Изображение не найдено (таймаут)».
Примеры:

5 — короткое ожидание для уже открытого окна
30 — стандарт для запуска программ
120 — если программа долго грузится


Точность (0.0–1.0) — насколько строго сравнивать пиксели картинки на экране с твоей сохранённой картинкой. Это порог совпадения (template matching через OpenCV).
ЗначениеЧто значит1.00Абсолютно точное совпадение — каждый пиксель идентичен0.95Очень строго — почти не прощает изменений0.80Стандарт — терпит небольшие отличия (антиалиасинг, лёгкое затемнение)0.70Мягко — может найти даже при заметных изменениях фона/подсветки0.50 и нижеСлишком мягко — будут ложные срабатывания
Когда какое выбирать:

Иконка кнопки на однотонном фоне → 0.9
Кнопка, которая может быть в состоянии «hover» (подсветилась при наведении) → 0.75–0.8
Текст внутри окна, который может рендериться чуть по-разному на разных DPI → 0.7
Если изображение вообще не находится при 0.8 — сначала проверь, что картинка корректно вырезана (не захватил лишних пикселей вокруг), и только потом снижай точность

Если точность слишком высокая — ничего не найдётся. Если слишком низкая — может «найти» совсем не ту картинку, потому что в OpenCV сходство по TM_CCOEFF_NORMED бывает высоким и для случайных похожих участков экрана.
'''

import pyautogui as pg
from app.actions.base import Action
from app.actions.image_utils import wait_for_image


class WaitImageAction(Action):
    name = "Ждать изображение"
    icon = "👁"
    file_params = ("image",)
    param_labels = {
        "image":      "Путь к изображению",
        "timeout":    "Таймаут (сек)",
        "confidence": "Точность (0.0–1.0)",
    }

    def execute(self, context):
        loc = wait_for_image(
            self.params["image"],
            timeout=float(self.params["timeout"]),
            confidence=float(self.params["confidence"]),
            stop_event=context.get("stop_event"),
        )
        if loc is None:
            raise RuntimeError("Изображение не найдено (таймаут)")
        context["last_image"] = loc


class ClickImageAction(Action):
    name = "Клик по изображению"
    icon = "🎯"
    file_params = ("image",)
    param_labels = {
        "image":      "Путь к изображению",
        "timeout":    "Таймаут (сек)",
        "confidence": "Точность (0.0–1.0)",
        "offset_x":   "Смещение X (px от верх. лев. угла)",
        "offset_y":   "Смещение Y (px от верх. лев. угла)",
    }

    def execute(self, context):
        loc = wait_for_image(
            self.params["image"],
            timeout=float(self.params["timeout"]),
            confidence=float(self.params["confidence"]),
            stop_event=context.get("stop_event"),
        )
        if loc is None:
            raise RuntimeError("Изображение не найдено")

        x, y, w, h = loc
        ox = int(self.params.get("offset_x", w // 2))
        oy = int(self.params.get("offset_y", h // 2))
        pg.click(x + ox, y + oy)
        context["last_image"] = loc