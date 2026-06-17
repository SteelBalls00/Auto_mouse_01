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


def _wrapped_param_keys(action_type):
    cls = ACTION_REGISTRY.get(action_type, (None,))[0]
    if cls is None:
        return ()
    return tuple(getattr(cls, "wrapped_params", ()))


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
    wrapped_used   = set()      # имена подпапок assets/wrapped_scenarios/ в работе
    wrapped_root   = os.path.join(assets_dir, "wrapped_scenarios")
    scenario_dir_norm = os.path.normcase(os.path.abspath(scenario_dir))

    for model in actions:
        # Получаем сериализуемое представление с сохранением enabled и т.п.
        step_dict  = model.to_dict()
        new_params = dict(step_dict.get("params", {}))
        wrapped_keys = _wrapped_param_keys(model.action_type)
        # вложенные сценарии обрабатываем отдельно — исключаем из общих файлов
        file_keys  = tuple(
            k for k in _file_param_keys(model.action_type) if k not in wrapped_keys
        )

        # ── Вложенные сценарии → assets/wrapped_scenarios/<имя>/ ──────
        for key in wrapped_keys:
            value = new_params.get(key)
            if not isinstance(value, str) or not value.strip():
                continue
            norm = value.replace("\\", "/")

            # уже относительный внутри wrapped_scenarios — оставляем
            if norm.startswith("assets/wrapped_scenarios/"):
                parts = norm.split("/")
                if len(parts) >= 3:
                    wrapped_used.add(parts[2])
                new_params[key] = norm
                continue

            value_abs = os.path.normcase(os.path.abspath(value))

            # уже лежит внутри assets этого сценария — релятивизируем, сохраняя подпуть
            if value_abs.startswith(assets_dir_norm + os.sep):
                rel = os.path.relpath(os.path.abspath(value), assets_dir).replace("\\", "/")
                p = rel.split("/")
                if len(p) >= 2 and p[0] == "wrapped_scenarios":
                    wrapped_used.add(p[1])
                new_params[key] = "assets/" + rel
                continue

            # путь задан, но файла нет — оставляем как есть (не копируем)
            if not (os.path.isabs(value) and os.path.exists(value) and os.path.isfile(value)):
                continue

            # имя вложенного сценария = имя его папки (или файла без .json)
            nested_dir = os.path.dirname(os.path.abspath(value))
            nested_name = os.path.basename(nested_dir) or \
                os.path.splitext(os.path.basename(value))[0]
            json_name = os.path.basename(value)
            dest_dir = os.path.join(wrapped_root, nested_name)

            # защита от копирования сценария в самого себя
            nested_dir_norm = os.path.normcase(nested_dir)
            if nested_dir_norm == scenario_dir_norm or \
               scenario_dir_norm.startswith(nested_dir_norm + os.sep):
                # вложенный — это сам текущий сценарий или его родитель: не копируем
                new_params[key] = value
                continue

            try:
                os.makedirs(wrapped_root, exist_ok=True)
                # копируем весь пакет вложенного сценария (json + его assets/)
                if os.path.isdir(nested_dir):
                    shutil.copytree(nested_dir, dest_dir, dirs_exist_ok=True)
                else:
                    os.makedirs(dest_dir, exist_ok=True)
                    shutil.copy2(value, os.path.join(dest_dir, json_name))
                wrapped_used.add(nested_name)
                new_params[key] = f"assets/wrapped_scenarios/{nested_name}/{json_name}"
            except Exception:
                # на любой сбой копирования оставляем исходный путь
                new_params[key] = value

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

    # ── Чистка неиспользуемых вложенных сценариев ────────────────────
    try:
        if os.path.isdir(wrapped_root):
            for sub in os.listdir(wrapped_root):
                full = os.path.join(wrapped_root, sub)
                if os.path.isdir(full) and sub not in wrapped_used:
                    shutil.rmtree(full, ignore_errors=True)
            # если папка опустела — убрать её
            if not os.listdir(wrapped_root):
                os.rmdir(wrapped_root)
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