import json
from models.action_model import ActionModel


def save_scenario(path, actions, name="Сценарий"):
    data = {
        "name": name,
        "steps": [a.to_dict() for a in actions],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_scenario(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    actions = [ActionModel.from_dict(step) for step in data.get("steps", [])]
    return data.get("name", ""), actions
