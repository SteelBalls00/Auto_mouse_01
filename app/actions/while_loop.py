from app.actions.base import Action, resolve_vars


class WhileStartAction(Action):
    name = "ЦИКЛ ПОКА"
    icon = "🔄"
    param_labels = {
        "desc":      "Описание (комментарий к блоку)",
        "left":     "Значение или {переменная}",
        "operator": "Оператор",
        "right":    "Сравнить с",
        "max_iter": "Макс. итераций (защита от вечного цикла)",
    }
    param_options = {
        "operator": ["=", "≠", ">", "<", "≥", "≤", "пусто", "не пусто"],
    }

    def execute(self, context):
        pass  # Обрабатывается в runner

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


class EndWhileAction(Action):
    name = "КОНЕЦ ЦИКЛА ПОКА"
    icon = "🔚"

    def execute(self, context):
        pass