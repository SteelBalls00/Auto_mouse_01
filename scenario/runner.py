import threading
from PyQt5.QtCore import QThread, pyqtSignal

from actions.registry import ACTION_REGISTRY


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

    def __init__(self, actions, parent=None):
        super().__init__(parent)
        self.actions    = actions
        self.context    = {}
        self._stop_event = threading.Event()
        self.context["stop_event"] = self._stop_event

    def stop(self):
        """Запросить остановку сценария."""
        self._stop_event.set()

    def run(self):
        self._stop_event.clear()

        # Парные индексы IF / ELSE / ENDIF
        try:
            pairs = self._build_pairs()
        except Exception as e:
            self.log_line.emit(f"✖ {e}")
            self.finished_error.emit(str(e))
            return

        else_to_if = {p["else"]: if_i for if_i, p in pairs.items() if p["else"] is not None}

        i = 0
        while i < len(self.actions):
            if self._stop_event.is_set():
                self.log_line.emit("⏹ Остановлено пользователем")
                self.finished_error.emit("Остановлено")
                return

            model = self.actions[i]
            t     = model.action_type

            if t == "if_start":
                action_cls = ACTION_REGISTRY[t][0]
                action     = action_cls(model.params)
                try:
                    cond = action.evaluate(self.context)
                except Exception as e:
                    self.log_line.emit(f"✖ Ошибка условия на шаге {i + 1}: {e}")
                    self.finished_error.emit(str(e))
                    return
                self.step_started.emit(i)
                self.log_line.emit(f"[{i + 1}] ЕСЛИ → {cond}")

                if cond:
                    i += 1                                  # входим в then
                else:
                    p = pairs[i]
                    i = (p["else"] + 1) if p["else"] is not None else (p["end"] + 1)

            elif t == "else":
                # Сюда мы попали выполняя then-блок — пропускаем else-блок
                if_idx = else_to_if.get(i)
                end_idx = pairs[if_idx]["end"]
                self.step_started.emit(i)
                self.log_line.emit(f"[{i + 1}] ИНАЧЕ → пропуск")
                i = end_idx + 1

            elif t == "end_if":
                self.step_started.emit(i)
                self.log_line.emit(f"[{i + 1}] КОНЕЦ ЕСЛИ")
                i += 1

            else:
                action_cls = ACTION_REGISTRY[t][0]
                action     = action_cls(model.params)
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

    def _build_pairs(self):
        """Сопоставляет IF ↔ ELSE ↔ ENDIF, проверяет парность."""
        pairs = {}
        stack = []
        for i, model in enumerate(self.actions):
            t = model.action_type
            if t == "if_start":
                stack.append(i)
                pairs[i] = {"else": None, "end": None}
            elif t == "else":
                if not stack:
                    raise RuntimeError(f"ИНАЧЕ без ЕСЛИ на шаге {i + 1}")
                pairs[stack[-1]]["else"] = i
            elif t == "end_if":
                if not stack:
                    raise RuntimeError(f"КОНЕЦ ЕСЛИ без ЕСЛИ на шаге {i + 1}")
                pairs[stack.pop()]["end"] = i
        if stack:
            raise RuntimeError(f"Незакрытый ЕСЛИ на шаге {stack[-1] + 1}")
        return pairs
