"""
Цвета групп и действий для подсветки шагов сценария.
Действие наследует цвет группы, если у него не задан собственный.
Хранится в app/resources/action_colors.json.
"""
import os
import json

from app.ui.action_palette import ACTION_GROUPS

_STORE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "resources", "action_colors.json"
)

# action_type -> имя группы
_GROUP_OF = {}
for _gname, _types in ACTION_GROUPS:
    for _t in _types:
        _GROUP_OF[_t] = _gname

_cache = None   # {"groups": {...}, "actions": {...}}

# Встроенные дефолтные цвета управляющих блоков (если пользователь не задал свой)
CONTROL_DEFAULTS = {
    "if_start": "#dbeafe", "else": "#fed7aa", "end_if": "#e5e7eb",
    "for_each_start": "#e9d5ff", "end_for": "#ddd6fe",
    "while_start": "#fef3c7", "end_while": "#fde68a",
    "break": "#fecaca", "continue": "#fecaca",
    "repeat_start": "#e9d5ff", "end_repeat": "#e9d5ff",
    "try_start": "#fce7f3", "catch": "#fbcfe8", "end_try": "#f9a8d4",
}


def group_of(action_type):
    return _GROUP_OF.get(action_type)


def _load_raw():
    if not os.path.exists(_STORE):
        return {"groups": {}, "actions": {}}
    try:
        with open(_STORE, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("groups", {})
        data.setdefault("actions", {})
        return data
    except Exception:
        return {"groups": {}, "actions": {}}


def _data():
    global _cache
    if _cache is None:
        _cache = _load_raw()
    return _cache


def reload():
    """Сбросить кэш — вызывать после сохранения цветов."""
    global _cache
    _cache = None


def save(data):
    """data = {'groups': {имя: '#hex'}, 'actions': {type: '#hex'}}."""
    os.makedirs(os.path.dirname(_STORE), exist_ok=True)
    clean = {
        "groups":  {k: v for k, v in (data.get("groups") or {}).items() if v},
        "actions": {k: v for k, v in (data.get("actions") or {}).items() if v},
    }
    with open(_STORE, "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2, ensure_ascii=False)
    reload()


def group_color(group_name):
    return _data()["groups"].get(group_name) or ""


def action_color(action_type):
    """Только собственный цвет действия (без наследования)."""
    return _data()["actions"].get(action_type) or ""


def resolve(action_type):
    """Эффективный цвет: собственный → цвет группы → встроенный дефолт → None."""
    d = _data()
    own = d["actions"].get(action_type)
    if own:
        return own
    g = _GROUP_OF.get(action_type)
    if g:
        gc = d["groups"].get(g)
        if gc:
            return gc
    return CONTROL_DEFAULTS.get(action_type)
