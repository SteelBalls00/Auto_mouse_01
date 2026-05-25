from app.actions.base import Action


class ReadElementAction(Action):
    name = "Прочитать текст элемента"
    icon = "📖"
    param_labels = {
        "window_var":   "Переменная окна (из «Найти окно»)",
        "auto_id":      "AutomationId (uia)",
        "control_type": "Тип контрола (uia)",
        "name":         "Имя элемента",
        "class_name":   "Класс элемента (Delphi: TcxCustomInnerTextEdit …)",
        "instance":     "Номер экземпляра (1, 2, …)",
        "result_name":  "Имя результата (для переменной)",
    }

    def execute(self, context):
        from pywinauto import Desktop

        win_var = (self.params.get("window_var") or "").strip()
        data    = context.get(win_var, {})
        if not isinstance(data, dict) or "_search" not in data:
            raise ValueError(f"Переменная окна '{win_var}' не найдена")

        s       = data["_search"]
        backend = s.get("backend", "win32")

        kwargs = {}
        if s.get("title"):        kwargs["title_re"]     = f".*{s['title']}.*"
        if s.get("class_name"):   kwargs["class_name"]   = s["class_name"]
        if s.get("process_name"): kwargs["process_name"] = s["process_name"]
        win_spec = Desktop(backend=backend).window(**kwargs)

        child = {}
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
            if auto_id:      child["auto_id"]      = auto_id
            if control_type: child["control_type"] = control_type
            if name:         child["title"]        = name
            if class_name:   child["class_name"]   = class_name
        else:
            if name:       child["title"]      = name
            if class_name: child["class_name"] = class_name
        if instance is not None:
            child["found_index"] = instance - 1

        element = win_spec.child_window(**child).wrapper_object()
        text = element.window_text() or ""

        rname = (self.params.get("result_name") or "").strip() or "elem"
        context[rname] = {"text": text, "empty": 1 if not text.strip() else 0}

    def output_vars(self):
        rname = (self.params.get("result_name") or "").strip()
        if not rname:
            return None
        return {
            "label": rname,
            "children": [
                {"label": "text",  "drag": f"{{{rname}.text}}"},
                {"label": "empty", "drag": f"{{{rname}.empty}}"},
            ],
        }