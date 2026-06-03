import json
import os
import shutil

from app.models.action_model import ActionModel
from app.actions.registry import ACTION_REGISTRY


def _file_param_keys(action_type):
    cls = ACTION_REGISTRY.get(action_type, (None,))[0]
    if cls is None:
        return ()
    return tuple(getattr(cls, "file_params", ()))


def _is_external_path(value):
    return (
        isinstance(value, str)
        and value.strip()
        and os.path.isabs(value)
        and os.path.exists(value)
        and os.path.isfile(value)
    )


def save_scenario(parent_folder, name, actions):
    """
    Сохраняет сценарий как папку-пакет.
    Файлы-параметры копируются в assets/. Уже лежащие в assets не дублируются.
    После сохранения из assets удаляются файлы, не используемые ни одним шагом.
    """
    scenario_dir = os.path.join(parent_folder, name)
    assets_dir   = os.path.join(scenario_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    assets_dir_norm = os.path.normcase(os.path.abspath(assets_dir))

    steps_out      = []
    used_names     = set()      # имена файлов в assets/ после сохранения
    src_to_name    = {}         # абс. путь источника → имя в assets/

    for model in actions:
        # Получаем сериализуемое представление с сохранением enabled и т.п.
        step_dict  = model.to_dict()
        new_params = dict(step_dict.get("params", {}))
        file_keys  = _file_param_keys(model.action_type)

        for key in file_keys:
            value = new_params.get(key)
            if not isinstance(value, str) or not value.strip():
                continue

            # 0) Уже относительный assets/... — оставляем как есть
            norm = value.replace("\\", "/")
            if norm.startswith("assets/"):
                used_names.add(os.path.basename(norm))
                new_params[key] = norm
                continue

            value_abs = os.path.normcase(os.path.abspath(value))

            # 1) Абсолютный путь внутри assets этого сценария — делаем
            #    относительным ВСЕГДА, даже если файла пока нет (напр. превью
            #    ещё не снято). Это держит сценарий переносимым.
            if value_abs.startswith(assets_dir_norm + os.sep):
                fname = os.path.basename(value)
                used_names.add(fname)
                new_params[key] = f"assets/{fname}"
                continue

            # 2) Внешний файл — копируем только если он реально существует
            if not _is_external_path(value):
                continue

            # 3) Этот же исходный файл уже обработан в этом сохранении
            if value_abs in src_to_name:
                new_params[key] = f"assets/{src_to_name[value_abs]}"
                continue

            # 4) Новый внешний файл — копируем, подбираем уникальное имя
            base = os.path.basename(value)
            target_name = base
            i = 1
            while target_name in used_names or os.path.exists(
                os.path.join(assets_dir, target_name)
            ):
                stem, ext = os.path.splitext(base)
                target_name = f"{stem}_{i}{ext}"
                i += 1

            used_names.add(target_name)
            src_to_name[value_abs] = target_name
            shutil.copy2(value, os.path.join(assets_dir, target_name))
            new_params[key] = f"assets/{target_name}"

        step_dict["params"] = new_params
        steps_out.append(step_dict)

    # ── Чистка assets от файлов, на которые никто не ссылается ────────
    try:
        for existing in os.listdir(assets_dir):
            full = os.path.join(assets_dir, existing)
            if os.path.isfile(full) and existing not in used_names:
                try:
                    os.remove(full)
                except OSError:
                    pass
    except OSError:
        pass

    data = {"name": name, "steps": steps_out}
    scenario_file = f"{name}.json"
    scenario_path = os.path.join(scenario_dir, scenario_file)
    with open(scenario_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Миграция: если рядом лежит старый scenario.json (от прежнего формата),
    # а новый файл называется иначе — удаляем, чтобы не было двух источников правды.
    if scenario_file != "scenario.json":
        legacy = os.path.join(scenario_dir, "scenario.json")
        if os.path.isfile(legacy):
            try:
                os.remove(legacy)
            except OSError:
                pass

    return scenario_path


def load_scenario(scenario_json_path):
    with open(scenario_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    scenario_dir = os.path.dirname(os.path.abspath(scenario_json_path))

    actions = []
    for step in data.get("steps", []):
        params    = dict(step.get("params", {}))
        file_keys = _file_param_keys(step["type"])

        for key in file_keys:
            value = params.get(key)
            if isinstance(value, str) and value.startswith("assets/"):
                params[key] = os.path.join(scenario_dir, value.replace("/", os.sep))

        step_copy = dict(step)
        step_copy["params"] = params
        actions.append(ActionModel.from_dict(step_copy))

    return data.get("name", ""), actions