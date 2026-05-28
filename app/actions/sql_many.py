import configparser
import os
from app.actions.base import Action, short_value


class SqlQueryManyAction(Action):
    name = "SQL запрос (много строк)"
    icon = "🗂"
    file_params = ("config",)
    param_labels = {
        "query_name":  "Имя запроса (для переменных)",
        "config":      "Файл конфига (.ini)",
        "query":       "SQL запрос",
        "columns":     "Колонки результата (через запятую)",
        "expect_rows": "Ожидать строки (иначе ошибка)",
    }
    param_widgets = {
        "query": "multiline",
    }

    def execute(self, context):
        import fdb

        config_path = self.params.get("config", "")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Файл конфига не найден: {config_path}")

        cfg = configparser.ConfigParser()
        cfg.read(config_path, encoding="utf-8")
        db = cfg["database"]

        con = fdb.connect(
            host=db["host"],
            port=int(db.get("port", "3050")),
            database=db["database"],
            user=db["user"],
            password=db["password"],
            charset=db.get("charset", "WIN1251"),
        )
        try:
            cur = con.cursor()
            cur.execute(self.params.get("query", "").strip())
            rows = cur.fetchall()

            cur_cols  = [d[0] for d in cur.description] if cur.description else []
            user_cols = [c.strip() for c in self.params.get("columns", "").split(",") if c.strip()]
            col_names = user_cols if user_cols else cur_cols

            result = []
            for row in rows:
                d = {}
                for i, name in enumerate(col_names):
                    d[name] = row[i] if i < len(row) else None
                result.append(d)

            query_name = (self.params.get("query_name") or "").strip() or "sql_rows"
            context[query_name] = result

            log = context.get("_log")
            if log:
                if result:
                    log(f"{query_name}: строк {len(result)}, первая: "
                        f"{short_value(result[0])}")
                else:
                    log(f"{query_name}: 0 строк (результат пуст)")

            if self.params.get("expect_rows", False) and not result:
                raise RuntimeError("Запрос не вернул строк")
        finally:
            con.close()

    def output_vars(self):
        query_name = (self.params.get("query_name") or "").strip()
        cols_raw   = self.params.get("columns", "")
        cols       = [c.strip() for c in cols_raw.split(",") if c.strip()]
        if not query_name:
            return None
        children = [{"label": c} for c in cols] or [{"label": "(укажите колонки)"}]
        return {
            "label": f"{query_name} (список)",
            "children": children,
        }