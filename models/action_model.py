from actions.registry import ACTION_REGISTRY


class ActionModel:
    def __init__(self, action_type, params):
        self.action_type = action_type
        self.params = params

    def title(self):
        return ACTION_REGISTRY[self.action_type][0].name

    def to_dict(self):
        return {
            "type": self.action_type,
            "params": self.params
        }

    @staticmethod
    def from_dict(data):
        return ActionModel(
            data["type"],
            data.get("params", {})
        )
