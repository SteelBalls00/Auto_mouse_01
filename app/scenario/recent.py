import os
import json

_STORE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "resources", "recent_scenarios.json"
)
MAX_RECENT = 15


def _load():
    if not os.path.exists(_STORE):
        return {"recent": [], "favorites": []}
    try:
        with open(_STORE, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("recent", [])
        data.setdefault("favorites", [])
        return data
    except Exception:
        return {"recent": [], "favorites": []}


def _save(data):
    os.makedirs(os.path.dirname(_STORE), exist_ok=True)
    with open(_STORE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_recent(path):
    """Добавить путь в начало списка недавних (без дублей)."""
    if not path:
        return
    data = _load()
    path = os.path.abspath(path)
    data["recent"] = [p for p in data["recent"] if os.path.abspath(p) != path]
    data["recent"].insert(0, path)
    data["recent"] = data["recent"][:MAX_RECENT]
    _save(data)


def get_recent():
    data = _load()
    # отсеиваем исчезнувшие файлы
    return [p for p in data["recent"] if os.path.exists(p)]


def get_favorites():
    data = _load()
    return [p for p in data["favorites"] if os.path.exists(p)]


def toggle_favorite(path):
    """Добавить/убрать из избранного. Возвращает True если теперь в избранном."""
    data = _load()
    path = os.path.abspath(path)
    favs = [os.path.abspath(p) for p in data["favorites"]]
    if path in favs:
        data["favorites"] = [p for p in data["favorites"]
                             if os.path.abspath(p) != path]
        _save(data)
        return False
    else:
        data["favorites"].insert(0, path)
        _save(data)
        return True


def is_favorite(path):
    data = _load()
    path = os.path.abspath(path)
    return path in [os.path.abspath(p) for p in data["favorites"]]


def remove_recent(path):
    data = _load()
    path = os.path.abspath(path)
    data["recent"] = [p for p in data["recent"] if os.path.abspath(p) != path]
    _save(data)