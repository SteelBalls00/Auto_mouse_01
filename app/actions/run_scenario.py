import os
from app.actions.base import Action


class RunScenarioAction(Action):
    name = "Запустить сценарий"
    icon = "▶"
    file_params = ("scenario_path",)
    wrapped_params = ("scenario_path",)   # копируется в assets/wrapped_scenarios/<имя>/
    param_labels = {
        "task_name":     "Имя задачи (для лога и списка)",
        "scenario_path": "Путь к scenario.json",
        "stop_on_error": "Прервать родительский при ошибке вложенного",
    }

    def execute(self, context):
        # Импортируем поздно — избежать циклов
        from app.scenario.io import load_scenario
        from app.scenario.runner import ScenarioRunner

        task_name = (self.params.get("task_name") or "").strip()
        log = context.get("_log")
        if log and task_name:
            log(f"Задача: {task_name}")

        path = (self.params.get("scenario_path") or "").strip()
        if not path:
            raise ValueError("Путь к сценарию не задан")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Сценарий не найден: {path}")

        name, actions = load_scenario(path)

        # Изолированный контекст — связь только через БД
        runner = ScenarioRunner(
            actions,
            parent=None,
            scenario_name=name or os.path.splitext(os.path.basename(path))[0],
        )

        # Перенаправляем лог под-сценария в родительский лог
        parent_log = context.get("_log_callback")
        if parent_log:
            runner.log_line.connect(parent_log)

        # stop_event прокидываем — чтобы Стоп родителя останавливал и вложенный
        parent_stop = context.get("stop_event")
        if parent_stop:
            runner.context["stop_event"] = parent_stop

        result = {"ok": False, "error": None}

        def _on_ok():
            result["ok"] = True

        def _on_err(msg):
            result["ok"] = False
            result["error"] = msg

        runner.finished_ok.connect(_on_ok)
        runner.finished_error.connect(_on_err)

        # Выполняем синхронно — start+wait чтобы родитель ждал завершения
        runner.start()
        runner.wait()

        # Кладём результат в контекст родителя для последующих ЕСЛИ
        context["last_subscenario_ok"]    = result["ok"]
        context["last_subscenario_error"] = result["error"] or ""

        if not result["ok"] and self.params.get("stop_on_error", True):
            raise RuntimeError(
                f"Вложенный сценарий '{name}' завершился с ошибкой: {result['error']}"
            )

    def output_vars(self):
        return {
            "label": "last_subscenario",
            "children": [
                {"label": "ok",    "drag": "{last_subscenario_ok}"},
                {"label": "error", "drag": "{last_subscenario_error}"},
            ],
        }