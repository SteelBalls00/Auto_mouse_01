'''
Как пользоваться — два режима
Режим 1 — подстановка через {...} (для простых случаев)
Имя операции: parse_date
Код:
    parts = "{find_case.FULL_NUMBER}".split("/")
    year = parts[1] if len(parts) > 1 else ""
    short = parts[0]
Выходные переменные: year, short

{find_case.FULL_NUMBER} будет заменено на "1-647/2025" ещё до выполнения кода — execute_with_resolved это делает автоматически. В дереве переменных появится:
parse_date
├── year
└── short
Режим 2 — прямое обращение к контексту (для сложных случаев)
Имя операции: process_rows
Код:
    # cases — список dict-ов из шага SQL запрос (много строк)
    active = [c for c in cases if c["STATUS"] == "Активно"]
    count = len(active)
    first_id = active[0]["ID"] if active else None
Выходные переменные: active, count, first_id
Здесь обращаемся к переменной cases напрямую — она уже доступна в local namespace.

Полезные нюансы
1. Внутри кода доступны модули re, os, math, json, datetime — этого хватает для большинства задач обработки строк/дат
2. Если код упадёт (например, KeyError) — сценарий встанет, в логе появится конкретная строка с ошибкой
3. Контракт по выходным переменным жёсткий: если указал outputs: a, b, c, а код не создал c — будет ошибка. Это сделано чтобы дерево переменных всегда было честным и можно было полагаться на то, что {op.c} точно будет
4. Никаких ограничений на код нет — это твоё приложение, не sandbox. Можешь импортировать что угодно через __import__("modulename") или просто import x внутри кода

Пример из жизни — твоя задача
Распарсить «Иванов И.И., 12.03.1985 г.р., паспорт 1234 567890» в отдельные поля:
Имя операции: parsed
Код:
    text = "{accused.raw_text}"
    import re

    fio_m  = re.match(r"^([^,]+),", text)
    date_m = re.search(r"(\d{2}\.\d{2}\.\d{4})", text)
    pass_m = re.search(r"паспорт\s+(\d{4}\s+\d{6})", text, re.IGNORECASE)

    fio      = fio_m.group(1).strip()      if fio_m  else ""
    birth    = date_m.group(1)             if date_m else ""
    passport = pass_m.group(1)             if pass_m else ""

Выходные переменные: fio, birth, passport
Потом в следующем шаге типа «Ввод текста» можно перетащить {parsed.fio}, {parsed.passport} из дерева переменных.
'''

from app.actions.base import Action, short_value


class PythonEvalAction(Action):
    name = "Python код"
    icon = "🐍"
    param_labels = {
        "op_name":     "Имя операции (namespace переменных)",
        "code":        "Код Python (переменные {a} / {a.b} подставляются как есть)",
        "outputs":     "Выходные переменные (через запятую)",
    }
    param_widgets = {
        "code": "multiline",
    }

    def execute(self, context):
        op_name = (self.params.get("op_name") or "").strip()
        if not op_name:
            raise ValueError("Имя операции не задано")

        code = self.params.get("code", "")
        if not code.strip():
            raise ValueError("Код не задан")

        outputs_raw = self.params.get("outputs", "")
        outputs = [o.strip() for o in outputs_raw.split(",") if o.strip()]

        # Локальное пространство, в котором исполняется код.
        # Кладём туда все переменные сценария, чтобы можно было обращаться
        # напрямую: например, sql_result["FIO"], а не только через {...}.
        local_ns = {
            "ctx":     context,
            "context": context,
        }
        for k, v in context.items():
            if k.isidentifier() and not k.startswith("_"):
                local_ns[k] = v

        # Делаем доступными часто нужные модули
        global_ns = {
            "__builtins__": __builtins__,
            "re":   __import__("re"),
            "os":   __import__("os"),
            "math": __import__("math"),
            "json": __import__("json"),
            "datetime": __import__("datetime"),
        }

        try:
            exec(code, global_ns, local_ns)
        except Exception as exc:
            raise RuntimeError(f"Ошибка в Python-коде: {exc}") from exc

        # Собираем выходные переменные
        result = {}
        missing = []
        for name in outputs:
            if name in local_ns:
                result[name] = local_ns[name]
            else:
                missing.append(name)

        if missing:
            raise RuntimeError(
                f"Код не определил переменные: {', '.join(missing)}"
            )

        # Кладём всё под одним namespace
        context[op_name] = result

        log = context.get("_log")
        if log:
            if result:
                log(f"{op_name}: " + ", ".join(
                    f"{k}={short_value(v)}" for k, v in result.items()
                ))
            else:
                log(f"{op_name}: (нет выходных переменных)")

    def output_vars(self):
        op_name = (self.params.get("op_name") or "").strip()
        outputs_raw = self.params.get("outputs", "")
        outputs = [o.strip() for o in outputs_raw.split(",") if o.strip()]
        if not op_name or not outputs:
            return None
        return {
            "label": op_name,
            "children": [
                {"label": o, "drag": f"{{{op_name}.{o}}}"} for o in outputs
            ],
        }