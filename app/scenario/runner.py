import threading
from PyQt5.QtCore import QThread, pyqtSignal

from app.actions.registry import ACTION_REGISTRY


class ScenarioRunner(QThread):
    """
    Выполняет сценарий в отдельном потоке.
    Сигналы:
      log_line(str)         — новая строка лога
      step_started(int)     — индекс текущего шага (0-based)
      finished_ok()         — сценарий завершён успешно
      finished_error(str)   — сценарий завершён с ошибкой
    """
    log_line       = pyqtSignal(str)
    step_started   = pyqtSignal(int)
    finished_ok    = pyqtSignal()
    finished_error = pyqtSignal(str)

    def __init__(self, actions, parent=None, start_from=0, single_step=False):
        super().__init__(parent)
        self.actions    = actions
        self.context    = {}
        self._stop_event = threading.Event()
        self.context["stop_event"] = self._stop_event
        self._start_from  = start_from
        self._single_step = single_step

    def stop(self):
        """Запросить остановку сценария."""
        self._stop_event.set()

    def run(self):
        self._stop_event.clear()

        if self._single_step:
            self._run_single_step(self._start_from)
            return

        try:
            pairs = self._build_pairs()
        except Exception as e:
            self.log_line.emit(f"✖ {e}")
            self.finished_error.emit(str(e))
            return

        else_to_if = {
            info["else"]: start_i
            for start_i, info in pairs.items()
            if info["type"] == "if" and info.get("else") is not None
        }

        loop_stack = []
        i = self._start_from
        while i < len(self.actions):
            if self._stop_event.is_set():
                self.log_line.emit("⏹ Остановлено пользователем")
                self.finished_error.emit("Остановлено")
                return

            model = self.actions[i]
            t = model.action_type

            # Пропускаем отключённые шаги (но не управляющие — они нужны для парности)
            if not model.enabled and t not in (
                    "if_start", "else", "end_if",
                    "for_each_start", "end_for"
            ):
                self.step_started.emit(i)
                self.log_line.emit(f"[{i + 1}] ⊘ Пропущено (отключено)")
                i += 1
                continue

            if t == "if_start":
                action = ACTION_REGISTRY[t][0](model.params)
                try:
                    cond = action.evaluate(self.context)
                except Exception as e:
                    self.log_line.emit(f"✖ Ошибка условия на шаге {i + 1}: {e}")
                    self.finished_error.emit(str(e))
                    return
                self.step_started.emit(i)
                self.log_line.emit(f"[{i + 1}] ЕСЛИ → {cond}")
                if cond:
                    i += 1
                else:
                    p = pairs[i]
                    i = (p["else"] + 1) if p.get("else") is not None else (p["end"] + 1)

            elif t == "else":
                if_idx = else_to_if.get(i)
                end_idx = pairs[if_idx]["end"]
                self.step_started.emit(i)
                self.log_line.emit(f"[{i + 1}] ИНАЧЕ → пропуск")
                i = end_idx + 1

            elif t == "end_if":
                self.step_started.emit(i)
                self.log_line.emit(f"[{i + 1}] КОНЕЦ ЕСЛИ")
                i += 1

            elif t == "for_each_start":
                params      = model.params
                loop_name   = (params.get("loop_name") or "").strip() or f"loop_{i}"
                source_name = (params.get("source") or "").strip()
                items       = self.context.get(source_name)

                if not isinstance(items, list):
                    msg = f"Источник цикла '{source_name}' не является списком"
                    self.log_line.emit(f"✖ {msg}")
                    self.finished_error.emit(msg)
                    return

                end_idx = pairs[i]["end"]
                self.step_started.emit(i)
                self.log_line.emit(
                    f"[{i + 1}] ЦИКЛ '{loop_name}' по '{source_name}' "
                    f"({len(items)} элементов)"
                )

                if not items:
                    self.context[loop_name] = {"index": 0, "count": 0, "current": {}}
                    i = end_idx + 1
                    continue

                loop_stack.append({
                    "start": i,
                    "end":   end_idx,
                    "name":  loop_name,
                    "items": items,
                    "iter":  0,
                })
                first = items[0]
                self.context[loop_name] = {
                    "index":   1,
                    "count":   len(items),
                    "current": first if isinstance(first, dict) else {"value": first},
                }
                i += 1

            elif t == "end_for":
                if not loop_stack:
                    self.log_line.emit(f"✖ КОНЕЦ ЦИКЛА без ЦИКЛА на шаге {i + 1}")
                    self.finished_error.emit("Структурная ошибка")
                    return
                top = loop_stack[-1]
                top["iter"] += 1
                if top["iter"] < len(top["items"]):
                    item = top["items"][top["iter"]]
                    self.context[top["name"]] = {
                        "index":   top["iter"] + 1,
                        "count":   len(top["items"]),
                        "current": item if isinstance(item, dict) else {"value": item},
                    }
                    self.step_started.emit(i)
                    self.log_line.emit(
                        f"[{i + 1}] → итерация {top['iter'] + 1}/{len(top['items'])}"
                    )
                    i = top["start"] + 1
                else:
                    self.step_started.emit(i)
                    self.log_line.emit(f"[{i + 1}] КОНЕЦ ЦИКЛА '{top['name']}'")
                    loop_stack.pop()
                    i += 1

            elif t == "break":
                if not loop_stack:
                    self.log_line.emit(f"✖ ПРЕРВАТЬ вне цикла на шаге {i + 1}")
                    self.finished_error.emit("Структурная ошибка")
                    return
                top = loop_stack.pop()
                self.step_started.emit(i)
                self.log_line.emit(f"[{i + 1}] ПРЕРВАТЬ '{top['name']}'")
                i = top["end"] + 1

            elif t == "continue":
                if not loop_stack:
                    self.log_line.emit(f"✖ СЛЕДУЮЩАЯ вне цикла на шаге {i + 1}")
                    self.finished_error.emit("Структурная ошибка")
                    return
                top = loop_stack[-1]
                self.step_started.emit(i)
                self.log_line.emit(f"[{i + 1}] СЛЕДУЮЩАЯ ИТЕРАЦИЯ")
                i = top["end"]

            else:
                action = ACTION_REGISTRY[t][0](model.params)
                self.step_started.emit(i)
                self.log_line.emit(f"[{i + 1}/{len(self.actions)}] {action.name}...")
                try:
                    action.execute_with_resolved(self.context)
                    self.log_line.emit("  ✔ Готово")
                except Exception as exc:
                    self.log_line.emit(f"  ✖ Ошибка на шаге {i + 1} ({action.name}): {exc}")
                    self.finished_error.emit(str(exc))
                    return
                i += 1

        self.log_line.emit("✔ Сценарий завершён")
        self.finished_ok.emit()

    def _run_single_step(self, idx):
        if not (0 <= idx < len(self.actions)):
            self.finished_error.emit(f"Неверный индекс шага: {idx}")
            return
        model = self.actions[idx]
        if not model.enabled:
            self.log_line.emit(f"[{idx + 1}] ⊘ Шаг отключён")
            self.finished_ok.emit()
            return
        if model.action_type in (
                "if_start", "else", "end_if",
                "for_each_start", "end_for", "break", "continue"
        ):
            self.log_line.emit(
                f"[{idx + 1}] Управляющий шаг — пропускаем в single-step"
            )
            self.finished_ok.emit()
            return

        action = ACTION_REGISTRY[model.action_type][0](model.params)
        self.step_started.emit(idx)
        self.log_line.emit(f"[{idx + 1}] {action.name}...")
        try:
            action.execute_with_resolved(self.context)
            self.log_line.emit("  ✔ Готово")
            self.finished_ok.emit()
        except Exception as exc:
            self.log_line.emit(f"  ✖ Ошибка: {exc}")
            self.finished_error.emit(str(exc))

    def _build_pairs(self):
        """Сопоставляет IF↔ELSE↔END_IF и FOR↔END_FOR. Любая вложенность."""
        pairs = {}
        stack = []
        for i, model in enumerate(self.actions):
            t = model.action_type
            if t == "if_start":
                stack.append((i, "if"))
                pairs[i] = {"type": "if", "else": None, "end": None}
            elif t == "for_each_start":
                stack.append((i, "for"))
                pairs[i] = {"type": "for", "end": None}
            elif t == "else":
                if not stack or stack[-1][1] != "if":
                    raise RuntimeError(f"ИНАЧЕ без ЕСЛИ на шаге {i + 1}")
                pairs[stack[-1][0]]["else"] = i
            elif t == "end_if":
                if not stack or stack[-1][1] != "if":
                    raise RuntimeError(f"КОНЕЦ ЕСЛИ без ЕСЛИ на шаге {i + 1}")
                pairs[stack.pop()[0]]["end"] = i
            elif t == "end_for":
                if not stack or stack[-1][1] != "for":
                    raise RuntimeError(f"КОНЕЦ ЦИКЛА без ЦИКЛА на шаге {i + 1}")
                pairs[stack.pop()[0]]["end"] = i
        if stack:
            idx, kind = stack[-1]
            kind_name = "ЕСЛИ" if kind == "if" else "ЦИКЛ"
            raise RuntimeError(f"Незакрытый {kind_name} на шаге {idx + 1}")
        return pairs