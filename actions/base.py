# actions/base.py
class Action:
    name = "Base"

    def __init__(self, params):
        self.params = params

    def execute(self, context):
        raise NotImplementedError
