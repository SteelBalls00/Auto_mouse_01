import os

from app.actions.base import Action


def _make_kwargs(title=None, class_name=None, process_name=None):
    kwargs = {}
    if title:
        kwargs["title_re"] = f".*{title}.*"
    if class_name:
        kwargs["class_name"] = class_name
    if process_name:
        kwargs["process_name"] = process_name
    if not kwargs:
        raise ValueError("Не задан ни один критерий поиска окна")
    return kwargs


def _find_window_spec(backend, title=None, class_name=None, process_name=None):
    from pywinauto import Desktop
    return Desktop(backend=backend).window(**_make_kwargs(title, class_name, process_name))


class FindWindowAction(Action):
    name = "Найти окно"
    icon = "🪟"
    param_labels = {
        "var_name":     "Имя переменной",
        "backend":      "Бэкенд (win32 для Delphi, uia для современных)",
        "title":        "Заголовок (частично, regex)",
        "class_name":   "Класс окна",
        "process_name": "Имя процесса (например app.exe)",
        "timeout":      "Таймаут (сек)",
        "on_missing":   "Если окно не найдено",
        "desc":         "Описание (в лог)",
    }
    param_options = {
        "backend": ["win32", "uia"],
        "on_missing": ["ошибка", "предупреждение"],
    }

    def execute(self, context):
        var_name = (self.params.get("var_name") or "").strip()
        if not var_name:
            raise ValueError("Имя переменной не задано")

        backend      = self.params.get("backend", "win32").strip() or "win32"
        title        = self.params.get("title", "").strip() or None
        class_name   = self.params.get("class_name", "").strip() or None
        process_name = self.params.get("process_name", "").strip() or None
        timeout      = float(self.params.get("timeout", 10))
        on_missing   = (self.params.get("on_missing") or "ошибка").strip()
        log          = context.get("_log")

        spec = _find_window_spec(backend, title, class_name, process_name)
        try:
            spec.wait("exists ready", timeout=timeout)
        except Exception:
            # окно не появилось за таймаут
            crit = "; ".join(p for p in [
                f"заголовок~'{title}'" if title else "",
                f"класс='{class_name}'" if class_name else "",
                f"процесс='{process_name}'" if process_name else "",
            ] if p)
            context[var_name] = {"found": "0"}
            if on_missing == "предупреждение":
                if log:
                    log(f"⚠ Окно не найдено ({crit}) — продолжаю, "
                        f"{{{var_name}.found}} = 0")
                return
            raise RuntimeError(f"Окно не найдено за {timeout:.0f} c ({crit})")

        wrapper = spec.wrapper_object()
        rect    = wrapper.rectangle()
        if log:
            log(f"🪟 Найдено окно «{wrapper.window_text()}» "
                f"[{rect.left},{rect.top} {rect.width()}×{rect.height()}]")

        context[var_name] = {
            "found":  "1",
            "title":  wrapper.window_text(),
            "class":  wrapper.class_name(),
            "left":   rect.left,
            "top":    rect.top,
            "right":  rect.right,
            "bottom": rect.bottom,
            "width":  rect.width(),
            "height": rect.height(),
            "_search": {
                "backend":      backend,
                "title":        title,
                "class_name":   class_name,
                "process_name": process_name,
            },
        }

    def output_vars(self):
        var_name = (self.params.get("var_name") or "").strip()
        if not var_name:
            return None
        fields = ["found", "title", "class", "left", "top", "right", "bottom", "width", "height"]
        return {
            "label": var_name,
            "children": [
                {"label": f, "drag": f"{{{var_name}.{f}}}"} for f in fields
            ],
        }


def _reattach_window(context, window_var):
    data = context.get(window_var)
    if not isinstance(data, dict) or "_search" not in data:
        raise ValueError(f"Переменная окна '{window_var}' не найдена")
    s = data["_search"]
    spec = _find_window_spec(
        s.get("backend", "win32"),
        s.get("title"),
        s.get("class_name"),
        s.get("process_name"),
    )
    return spec.wrapper_object()


class WindowFocusAction(Action):
    name = "Активировать окно"
    icon = "🎯"
    param_labels = {"window_var": "Переменная окна"}

    def execute(self, context):
        wnd = _reattach_window(context, (self.params.get("window_var") or "").strip())
        wnd.set_focus()


class WindowClickXYAction(Action):
    name = "Клик в окне (по координатам)"
    icon = "🖱"
    param_labels = {
        "window_var":   "Переменная окна",
        "description":  "Описание",
        "x":            "X относительно окна",
        "y":            "Y относительно окна",
        "button":       "Кнопка",
        "double_click": "Двойной клик",
        "preview":         "Последняя видимая область",
        "show_crosshair":  "Показывать точку нажатия",
    }
    param_options = {"button": ["left", "right", "middle"]}
    param_widgets = {"preview": "click_preview", "show_crosshair": "hidden"}
    file_params = ("preview",)

    # радиус захватываемой области вокруг точки клика (px)
    PREVIEW_RADIUS = 300

    def execute(self, context):
        wnd = _reattach_window(context, (self.params.get("window_var") or "").strip())
        x = int(self.params.get("x", 0))
        y = int(self.params.get("y", 0))
        btn = self.params.get("button", "left")
        wnd.set_focus()
        if self.params.get("double_click", False):
            wnd.double_click_input(button=btn, coords=(x, y))
        else:
            wnd.click_input(button=btn, coords=(x, y))

        # Снимок области вокруг клика — строго best-effort, не должен ломать клик
        try:
            self._capture_preview(wnd, x, y, context)
        except Exception as e:
            log = context.get("_log")
            if log:
                log(f"превью не снято: {e}")

    def _capture_preview(self, wnd, x, y, context):
        preview = (self.params.get("preview") or "").strip()
        if not preview:
            return  # путь не задан (сценарий не сохранён) — снимок некуда класть

        # Абсолютные экранные координаты точки клика
        rect = wnd.rectangle()
        sx = int(rect.left) + x
        sy = int(rect.top) + y
        r = self.PREVIEW_RADIUS

        from PIL import ImageGrab, Image
        try:
            shot = ImageGrab.grab(all_screens=True)
        except TypeError:
            shot = ImageGrab.grab()   # старый Pillow без all_screens

        # Начало координат полного снимка = левый/верхний край виртуального экрана.
        # Для нескольких мониторов он может быть отрицательным.
        origin_x, origin_y = 0, 0
        try:
            import ctypes
            user32 = ctypes.windll.user32
            origin_x = user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
            origin_y = user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
        except Exception:
            pass

        # Холст фиксированного размера, точка клика — точно в центре
        size = r * 2
        canvas = Image.new("RGB", (size, size), (32, 34, 40))
        px = sx - origin_x          # координаты точки внутри полного снимка
        py = sy - origin_y
        left = px - r
        top = py - r
        sw, sh = shot.size
        src_l = max(0, left)
        src_t = max(0, top)
        src_r = min(sw, left + size)
        src_b = min(sh, top + size)
        if src_r > src_l and src_b > src_t:
            crop = shot.crop((src_l, src_t, src_r, src_b))
            canvas.paste(crop, (src_l - left, src_t - top))

        os.makedirs(os.path.dirname(preview), exist_ok=True)
        canvas.save(preview)
        log = context.get("_log")
        if log:
            log(f"снимок области сохранён ({size}×{size})")


class WindowClickElementAction(Action):
    name = "Клик по элементу окна"
    icon = "🔘"
    param_labels = {
        "desc":       "Описание (в лог)",
        "window_var":   "Переменная окна",
        "auto_id":      "AutomationId (только uia)",
        "control_type": "Тип контрола (uia: Button; win32: оставить пустым)",
        "name":         "Имя элемента (заголовок/Text)",
        "class_name":   "Класс элемента (Delphi: TcxButton, TButton, ...)",
        "instance":     "Номер экземпляра, если класс не уникален (1, 2, …)",
        "double_click": "Двойной клик",
    }

    def execute(self, context):
        win_var = (self.params.get("window_var") or "").strip()
        wnd     = _reattach_window(context, win_var)

        # Backend этого окна
        data    = context.get(win_var, {})
        backend = data.get("_search", {}).get("backend", "win32")

        wnd.set_focus()

        kwargs = {}
        auto_id      = self.params.get("auto_id", "").strip()
        control_type = self.params.get("control_type", "").strip()
        name         = self.params.get("name", "").strip()
        class_name   = self.params.get("class_name", "").strip()
        instance     = self.params.get("instance", "")
        try:
            instance = int(instance) if str(instance).strip() else None
        except (TypeError, ValueError):
            instance = None

        if backend == "uia":
            if auto_id:      kwargs["auto_id"]      = auto_id
            if control_type: kwargs["control_type"] = control_type
            if name:         kwargs["title"]        = name
            if class_name:   kwargs["class_name"]   = class_name
        else:
            # win32 — auto_id и control_type не работают
            if name:       kwargs["title"]      = name
            if class_name: kwargs["class_name"] = class_name

        if instance is not None:
            kwargs["found_index"] = instance - 1   # AutoIt считает с 1, pywinauto с 0

        if not kwargs:
            raise ValueError("Не задан ни один критерий поиска элемента")

        # pywinauto: для дочернего элемента — child_window у спецификации, не у обёртки
        from pywinauto import Desktop
        s = data.get("_search", {})
        win_spec = Desktop(backend=backend).window(
            **_make_kwargs(s.get("title"), s.get("class_name"), s.get("process_name"))
        )
        element = win_spec.child_window(**kwargs).wrapper_object()

        if self.params.get("double_click", False):
            element.double_click_input()
        else:
            element.click_input()