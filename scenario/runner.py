from actions.registry import ACTION_REGISTRY
from PyQt5.QtWidgets import QApplication

class ScenarioRunner:
    def __init__(self, actions, log):
        self.actions = actions
        self.context = {}
        self.log = log

    def run(self):
        for i, model in enumerate(self.actions, 1):
            action_cls = ACTION_REGISTRY[model.action_type][0]
            action = action_cls(model.params)

            self.log.append(f"[{i}] {action.name}")
            QApplication.processEvents()

            action.execute(self.context)
