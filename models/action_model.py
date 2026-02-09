from actions.registry import ACTION_REGISTRY

class ActionModel:
    def __init__(self, action_type, params):
        self.action_type = action_type
        self.params = params

    def title(self):
        return ACTION_REGISTRY[self.action_type][0].name
