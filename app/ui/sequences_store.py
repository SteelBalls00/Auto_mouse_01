"""
Последовательности (сниппеты) — сохранённые наборы шагов, которые можно
вставить в сценарий, развернув в обычные отдельные шаги.
Хранятся в app/resources/sequences.json как {имя: [step_dict, ...]}.
"""
import os
import json
import copy

_STORE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "resources", "sequences.json"
)


def _load_raw():
    if not os.path.exists(_STORE):
        return {}
    try:
        with open(_STORE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_raw(data):
    os.makedirs(os.path.dirname(_STORE), exist_ok=True)
    with open(_STORE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def names():
    return sorted(_load_raw().keys())


def get(name):
    """Список шагов (глубокая копия), либо []."""
    return copy.deepcopy(_load_raw().get(name, []))


def exists(name):
    return name in _load_raw()


def add(name, steps):
    """Сохранить/перезаписать последовательность. steps — список dict (to_dict())."""
    data = _load_raw()
    data[name] = copy.deepcopy(steps)
    _save_raw(data)


def delete(name):
    data = _load_raw()
    if name in data:
        del data[name]
        _save_raw(data)


def rename(old, new):
    data = _load_raw()
    if old in data and new and new != old:
        data[new] = data.pop(old)
        _save_raw(data)
