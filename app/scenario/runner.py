import os
import threading
from PyQt5.QtCore import QThread, pyqtSignal

from app.actions.registry import ACTION_REGISTRY
from app.scenario.logger import setup_run_logger, close_logger


class ScenarioRunner(QThread):
    """
    Выполняет сценарий в отдельном потоке.
    Сигналы:
      log_line(str)         — новая строка лога
      step_started(int)     — индекс текущего шага (0-based)
      finished_ok()         — сценарий завершён успешно
      finished_error(str)   — сценарий завершён с ошибкой
    """
    log_line = pyqtSignal(str)
    step_started = pyqtSignal(int)
    finished_ok = pyqtSignal()
    finished_error = pyqtSignal(str)
    awaiting_step = pyqtSignal(int)

    def __init__(self, actions, parent=None, start_from=0, single_step=False,
                 scenario_name="scenario", project_root=None,
                 step_mode=False, step_delay=0.0):
        super().__init__(parent)
        self.actions     = actions
        self.context     = {}
        self._stop_event = threading.Event()
        self.context["stop_event"] = self._stop_event
        self._start_from    = start_from
        self._single_step   = single_step
        self._scenario_name = scenario_name
        self._project_root  = project_root or os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self._logger    = None
        self._log_path  = None
        # Отладка по шагам
        self._step_mode  = step_mode          # ждать разрешения перед каждым шагом
        self._step_delay = step_delay         # задержка (сек) в замедленном режиме
        self._step_gate  = threading.Event()  # разрешение на следующий шаг
        self._step_gate.set()

    def stop(self):
        """Запросить остановку сценария."""
        self._stop_event.set()

    def allow_next_step(self):
        """Разрешить выполнение следующего шага (пошаговый режим)."""
        self._step_gate.set()

    def _log(self, message, level="info"):
        """Лог идёт и в UI, и в файл."""
        self.log_line.emit(message)
        if self._logger:
            getattr(self._logger, level)(message)

    def run(self):
        self._stop_event.clear()

        # Открываем файловый лог
        try:
            self._logger, self._log_path = setup_run_logger(
                self._scenario_name, self._project_root
            )
            mode = "одного шага" if self._single_step else "сценария"
            self._logger.info(
                f"=== Запуск {mode}: {self._scenario_name} "
                f"({len(self.actions)} шаг(ов), старт с шага {self._start_from + 1}) ==="
            )
        except Exception as e:
            self.log_line.emit(f"⚠ Не удалось открыть лог-файл: {e}")
            self._logger = None

        try:
            if self._single_step:
                self._run_single_step(self._start_from)
                return
            self._main_loop()
        finally:
            if self._logger:
                self._logger.info("=== Конец запуска ===")
                if self._log_path:
                    self.log_line.emit(f"📝 Лог: {self._log_path}")
                close_logger(self._logger)
                self._logger = None

    def _main_loop(self):
        try:
            pairs = self._build_pairs()
        except Exception as e:
            self._log(f"✖ {e}", "error")
            self.finished_error.emit(str(e))
            return

        else_to_if = {
            info["else"]: start_i
            for start_i, info in pairs.items()
            if info["type"] == "if" and info.get("else") is not None
        }

        loop_stack = []
        loop_stack = []
        try_stack = []  # активные try-блоки: [{"start","catch","end","name"}]
        i = self._start_from
        while i < len(self.actions):
            # Пауза от бота (если задана) — ждём пока снимут
            pause_event = self.context.get("pause_event")
            if pause_event is not None:
                while not pause_event.is_set():
                    if self._stop_event.is_set():
                        break
                    pause_event.wait(0.2)

            if self._stop_event.is_set():
                self._log("⏹ Остановлено пользователем", "warning")
                self.finished_error.emit("Остановлено")
                return

            # ── Отладка по шагам ─────────────────────────────────────
            if self._step_mode:
                self._step_gate.clear()
                self.awaiting_step.emit(i)
                # ждём, пока UI разрешит (кнопка «Дальше») или остановят
                while not self._step_gate.is_set():
                    if self._stop_event.is_set():
                        self._log("⏹ Остановлено пользователем", "warning")
                        self.finished_error.emit("Остановлено")
                        return
                    self._step_gate.wait(0.1)
            elif self._step_delay > 0:
                # Замедленный режим — просто пауза с проверкой стопа
                slept = 0.0
                while slept < self._step_delay:
                    if self._stop_event.is_set():
                        self._log("⏹ Остановлено пользователем", "warning")
                        self.finished_error.emit("Остановлено")
                        return
                    self.msleep(50)
                    slept += 0.05

            model = self.actions[i]
            t = model.action_type

            if not model.enabled and t not in (
                    "if_start", "else", "end_if",
                    "for_each_start", "end_for",
                    "while_start", "end_while",
                    "repeat_start", "end_repeat",
                    "try_start", "catch", "end_try",
            ):
                self.step_started.emit(i)
                self._log(f"[{i + 1}] ⊘ Пропущено (отключено)")
                i += 1
                continue

            if t == "if_start":
                action = ACTION_REGISTRY[t][0](model.params)
                try:
                    cond = action.evaluate(self.context)
                except Exception as e:
                    self._log(f"✖ Ошибка условия на шаге {i + 1}: {e}", "error")
                    self.finished_error.emit(str(e))
                    return
                self.step_started.emit(i)
                self._log(f"[{i + 1}] ЕСЛИ → {cond}")
                if cond:
                    i += 1
                else:
                    p = pairs[i]
                    i = (p["else"] + 1) if p.get("else") is not None else (p["end"] + 1)

            elif t == "else":
                if_idx = else_to_if.get(i)
                end_idx = pairs[if_idx]["end"]
                self.step_started.emit(i)
                self._log(f"[{i + 1}] ИНАЧЕ → пропуск")
                i = end_idx + 1

            elif t == "try_start":
                self.step_started.emit(i)
                self._log(f"[{i + 1}] 🛡 ПОПРОБОВАТЬ")
                info = pairs[i]
                try_stack.append({
                    "start": i,
                    "catch": info.get("catch"),
                    "end": info["end"],
                    "name": (model.params.get("try_name") or "try").strip() or "try",
                })
                i += 1

            elif t == "catch":
                # Дошли сюда естественным путём (без ошибки) — пропускаем catch-блок
                self.step_started.emit(i)
                self._log(f"[{i + 1}] 🩹 (ошибок не было, пропуск обработчика)")
                # ищем свой try по позиции catch
                end_idx = None
                for ts in reversed(try_stack):
                    if ts.get("catch") == i:
                        end_idx = ts["end"]
                        break
                if end_idx is None:
                    end_idx = pairs.get(i, {}).get("end", i)
                i = end_idx + 1

            elif t == "end_try":
                self.step_started.emit(i)
                self._log(f"[{i + 1}] КОНЕЦ ОБРАБОТКИ")
                # снимаем завершившийся try со стека
                if try_stack and try_stack[-1]["end"] == i:
                    try_stack.pop()
                i += 1

            elif t == "end_if":
                self.step_started.emit(i)
                self._log(f"[{i + 1}] КОНЕЦ ЕСЛИ")
                i += 1

            elif t == "for_each_start":
                params      = model.params
                loop_name   = (params.get("loop_name") or "").strip() or f"loop_{i}"
                source_name = (params.get("source") or "").strip()
                items       = self.context.get(source_name)

                if not isinstance(items, list):
                    msg = f"Источник цикла '{source_name}' не является списком"
                    self._log(f"✖ {msg}", "error")
                    self.finished_error.emit(msg)
                    return

                end_idx = pairs[i]["end"]
                self.step_started.emit(i)
                self._log(
                    f"[{i + 1}] ЦИКЛ '{loop_name}' по '{source_name}' "
                    f"({len(items)} элементов)"
                )

                if not items:
                    self.context[loop_name] = {"index": 0, "count": 0, "current": {}}
                    i = end_idx + 1
                    continue

                loop_stack.append({
                    "start": i, "end": end_idx, "name": loop_name,
                    "items": items, "iter": 0,
                })
                first = items[0]
                self.context[loop_name] = {
                    "index":   1,
                    "count":   len(items),
                    "current": first if isinstance(first, dict) else {"value": first},
                }
                i += 1

            elif t == "repeat_start":
                loop_name = (model.params.get("loop_name") or "").strip() or f"rep_{i}"
                times = int(model.params.get("times", 1) or 1)
                end_idx = pairs[i]["end"]
                self.step_started.emit(i)
                self._log(f"[{i + 1}] ПОВТОРИТЬ {times} раз")

                if times <= 0:
                    i = end_idx + 1
                    continue

                loop_stack.append({
                    "type": "repeat", "start": i, "end": end_idx,
                    "name": loop_name, "items": list(range(times)), "iter": 0,
                })
                self.context[loop_name] = {"index": 1, "count": times}
                i += 1

            elif t == "end_repeat":
                if not loop_stack or loop_stack[-1].get("type") != "repeat":
                    self._log(f"✖ КОНЕЦ ПОВТОРА без ПОВТОРИТЬ на шаге {i + 1}", "error")
                    self.finished_error.emit("Структурная ошибка")
                    return
                top = loop_stack[-1]
                top["iter"] += 1
                if top["iter"] < len(top["items"]):
                    self.context[top["name"]] = {
                        "index": top["iter"] + 1, "count": len(top["items"])}
                    self.step_started.emit(i)
                    self._log(f"[{i + 1}] → повтор {top['iter'] + 1}/{len(top['items'])}")
                    i = top["start"] + 1
                else:
                    self.step_started.emit(i)
                    self._log(f"[{i + 1}] КОНЕЦ ПОВТОРА")
                    loop_stack.pop()
                    i += 1

            elif t == "end_for":
                if not loop_stack:
                    self._log(f"✖ КОНЕЦ ЦИКЛА без ЦИКЛА на шаге {i + 1}", "error")
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
                    self._log(
                        f"[{i + 1}] → итерация {top['iter'] + 1}/{len(top['items'])}"
                    )
                    i = top["start"] + 1
                else:
                    self.step_started.emit(i)
                    self._log(f"[{i + 1}] КОНЕЦ ЦИКЛА '{top['name']}'")
                    loop_stack.pop()
                    i += 1


            elif t == "break":
                if not loop_stack:
                    self._log(f"✖ ПРЕРВАТЬ вне цикла на шаге {i + 1}", "error")
                    self.finished_error.emit("Структурная ошибка")
                    return
                top = loop_stack.pop()
                self.step_started.emit(i)
                name_or_type = top.get("name") or top.get("type", "цикл")
                self._log(f"[{i + 1}] ПРЕРВАТЬ '{name_or_type}'")
                i = top["end"] + 1

            elif t == "continue":
                if not loop_stack:
                    self._log(f"✖ СЛЕДУЮЩАЯ вне цикла на шаге {i + 1}", "error")
                    self.finished_error.emit("Структурная ошибка")
                    return
                top = loop_stack[-1]
                self.step_started.emit(i)
                self._log(f"[{i + 1}] СЛЕДУЮЩАЯ ИТЕРАЦИЯ")
                i = top["end"]

            elif t == "while_start":
                action = ACTION_REGISTRY[t][0](model.params)
                try:
                    cond = action.evaluate(self.context)
                except Exception as e:
                    self._log(f"✖ Ошибка условия ПОКА на шаге {i + 1}: {e}", "error")
                    self.finished_error.emit(str(e))
                    return

                # Управляем счётчиком итераций для защиты от вечного цикла
                w_state = next(
                    (s for s in loop_stack if s.get("type") == "while" and s.get("start") == i),
                    None
                )
                if w_state is None:
                    # первая итерация
                    max_iter = int(model.params.get("max_iter", 10000) or 10000)
                    w_state = {"type": "while", "start": i, "end": pairs[i]["end"],
                               "iter": 0, "max_iter": max_iter}
                    loop_stack.append(w_state)

                self.step_started.emit(i)
                if not cond:
                    self._log(f"[{i + 1}] ПОКА → False, выход")
                    # снимаем со стека и прыгаем за end_while
                    end_idx = w_state["end"]
                    loop_stack.remove(w_state)
                    i = end_idx + 1
                    continue

                w_state["iter"] += 1
                if w_state["iter"] > w_state["max_iter"]:
                    msg = f"ЦИКЛ ПОКА превысил лимит {w_state['max_iter']} итераций"
                    self._log(f"✖ {msg}", "error")
                    self.finished_error.emit(msg)
                    return

                self._log(f"[{i + 1}] ПОКА → True (итерация {w_state['iter']})")
                i += 1

            elif t == "end_while":
                # Прыгаем обратно к while_start — он перепроверит условие
                w_state = next(
                    (s for s in reversed(loop_stack) if s.get("type") == "while"),
                    None
                )
                if w_state is None:
                    self._log(f"✖ КОНЕЦ ЦИКЛА ПОКА без открытого while на шаге {i + 1}", "error")
                    self.finished_error.emit("Структурная ошибка")
                    return
                self.step_started.emit(i)
                self._log(f"[{i + 1}] ← возврат к ПОКА")
                i = w_state["start"]

            else:
                action = ACTION_REGISTRY[t][0](model.params)
                self.step_started.emit(i)
                self._log(f"[{i + 1}/{len(self.actions)}] {action.name}...")

                try:
                    action.execute_with_resolved(self.context)
                    self._log("  ✔ Готово")
                    i += 1

                except Exception as exc:
                    err_text = str(exc)
                    self._log(
                        f"  ✖ Ошибка на шаге {i + 1} ({action.name}): {err_text}",
                        "error"
                    )

                    # Есть ли активный try-блок, у которого мы внутри try-части?
                    handler = None
                    while try_stack:
                        ts = try_stack[-1]
                        # ошибка попала в try-часть (до catch)
                        if ts["catch"] is not None and i < ts["catch"]:
                            handler = ts
                            break
                        elif ts["catch"] is None:
                            # try без catch — просто гасим ошибку, прыгаем за end_try
                            handler = ts
                            break
                        else:
                            # ошибка случилась уже внутри catch-блока этого try —
                            # этот try не может её ловить, снимаем и ищем выше
                            try_stack.pop()
                    if handler is None:
                        # Никто не ловит — обычное падение
                        self.finished_error.emit(err_text)
                        return
                    # Кладём данные об ошибке в переменную блока
                    self.context[handler["name"]] = {
                        "error": err_text,
                        "failed": 1,
                        "step": i + 1,
                    }

                    if handler["catch"] is not None:
                        self._log(f"  🩹 Переход в обработчик ошибки '{handler['name']}'")
                        i = handler["catch"] + 1
                    else:
                        self._log(f"  🩹 Ошибка подавлена (без обработчика)")
                        i = handler["end"] + 1
                        try_stack.pop()

        self._log("✔ Сценарий завершён")
        self.finished_ok.emit()

    def _run_single_step(self, idx):
        if not (0 <= idx < len(self.actions)):
            self.finished_error.emit(f"Неверный индекс шага: {idx}")
            return
        model = self.actions[idx]
        if not model.enabled:
            self._log(f"[{idx + 1}] ⊘ Шаг отключён")
            self.finished_ok.emit()
            return
        if model.action_type in (
                "if_start", "else", "end_if",
                "for_each_start", "end_for", "break", "continue"
        ):
            self._log(f"[{idx + 1}] Управляющий шаг — пропускаем в single-step")
            self.finished_ok.emit()
            return

        action = ACTION_REGISTRY[model.action_type][0](model.params)
        self.step_started.emit(idx)
        self._log(f"[{idx + 1}] {action.name}...")
        try:
            action.execute_with_resolved(self.context)
            self._log("  ✔ Готово")
            self.finished_ok.emit()
        except Exception as exc:
            self._log(f"  ✖ Ошибка: {exc}", "error")
            self.finished_error.emit(str(exc))

    def _build_pairs(self):
        """Сопоставляет IF↔ELSE↔END_IF, FOR↔END_FOR, WHILE↔END_WHILE."""
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
            elif t == "repeat_start":
                stack.append((i, "repeat"))
                pairs[i] = {"type": "repeat", "end": None}
            elif t == "while_start":
                stack.append((i, "while"))
                pairs[i] = {"type": "while", "end": None}
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
            elif t == "end_repeat":
                if not stack or stack[-1][1] != "repeat":
                    raise RuntimeError(f"КОНЕЦ ПОВТОРА без ПОВТОРИТЬ на шаге {i + 1}")
                pairs[stack.pop()[0]]["end"] = i
            elif t == "end_while":
                if not stack or stack[-1][1] != "while":
                    raise RuntimeError(f"КОНЕЦ ЦИКЛА ПОКА без ЦИКЛА ПОКА на шаге {i + 1}")
                pairs[stack.pop()[0]]["end"] = i
            elif t == "try_start":
                stack.append((i, "try"))
                pairs[i] = {"type": "try", "catch": None, "end": None}
            elif t == "catch":
                if not stack or stack[-1][1] != "try":
                    raise RuntimeError(f"ПРИ ОШИБКЕ без ПОПРОБОВАТЬ на шаге {i + 1}")
                pairs[stack[-1][0]]["catch"] = i
            elif t == "end_try":
                if not stack or stack[-1][1] != "try":
                    raise RuntimeError(f"КОНЕЦ ОБРАБОТКИ без ПОПРОБОВАТЬ на шаге {i + 1}")
                pairs[stack.pop()[0]]["end"] = i
        if stack:
            idx, kind = stack[-1]
            names = {"if": "ЕСЛИ", "for": "ЦИКЛ", "while": "ЦИКЛ ПОКА",
                     "repeat": "ПОВТОРИТЬ", "try": "ПОПРОБОВАТЬ"}
            raise RuntimeError(f"Незакрытый {names.get(kind, kind)} на шаге {idx + 1}")
        return pairs