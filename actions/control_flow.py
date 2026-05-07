from actions.base import Action, resolve_vars


class IfStartAction(Action):
    name = "ЕСЛИ"
    param_labels = {
        "left":     "Значение или {переменная}",
        "operator": "Оператор",
        "right":    "Сравнить с",
    }
    param_options = {
        "operator": ["=", "≠", ">", "<", "≥", "≤", "пусто", "не пусто"],
    }
    icon = "🔀"

    def execute(self, context):
        # Никогда не вызывается напрямую — runner сам обрабатывает условие
        pass

    def evaluate(self, context):
        left  = resolve_vars(self.params.get("left", ""),  context)
        right = resolve_vars(self.params.get("right", ""), context)
        op    = self.params.get("operator", "не пусто")

        if op == "пусто":
            return not (left and str(left).strip())
        if op == "не пусто":
            return bool(left and str(left).strip())
        if op == "=":
            return self._eq(left, right)
        if op == "≠":
            return not self._eq(left, right)

        # Числовое сравнение, fallback на строковое
        try:
            l, r = float(left), float(right)
        except (ValueError, TypeError):
            l, r = str(left), str(right)
        if op == ">":  return l >  r
        if op == "<":  return l <  r
        if op == "≥":  return l >= r
        if op == "≤":  return l <= r
        return False

    @staticmethod
    def _eq(a, b):
        try:
            return float(a) == float(b)
        except (ValueError, TypeError):
            return str(a) == str(b)


class ElseAction(Action):
    name = "ИНАЧЕ"
    icon = "↪"
    def execute(self, context):
        pass


class EndIfAction(Action):
    name = "КОНЕЦ ЕСЛИ"
    icon = "■"
    def execute(self, context):
        pass