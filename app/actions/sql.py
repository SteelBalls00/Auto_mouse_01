import configparser
import os
from app.actions.base import Action


class SqlQueryAction(Action):
    name = "SQL запрос (Firebird)"
    icon = "🗄"
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
            query = self.params.get("query", "").strip()
            cur.execute(query)

            is_select = query.upper().lstrip().startswith("SELECT")
            query_name = (self.params.get("query_name") or "").strip() or "sql_result"

            if is_select:
                rows = cur.fetchall()
                # Имена колонок: либо из cur.description, либо из настроек
                cur_cols = [d[0] for d in cur.description] if cur.description else []
                user_cols = [
                    c.strip() for c in self.params.get("columns", "").split(",")
                    if c.strip()
                ]
                col_names = user_cols if user_cols else cur_cols

                # Сохраняем первую строку как dict в context[query_name]
                if rows:
                    first = rows[0]
                    row_dict = {}
                    for i, name in enumerate(col_names):
                        row_dict[name] = first[i] if i < len(first) else None
                    context[query_name] = row_dict
                else:
                    context[query_name] = {}

                # Список всех строк под отдельным ключом
                context[f"{query_name}_rows"] = rows

                if self.params.get("expect_rows", False) and not rows:
                    raise RuntimeError("Запрос не вернул строк")
            else:
                con.commit()
                context["sql_rowcount"] = cur.rowcount

        finally:
            con.close()

    def output_vars(self):
        query_name = (self.params.get("query_name") or "").strip()
        cols_raw   = self.params.get("columns", "")
        cols       = [c.strip() for c in cols_raw.split(",") if c.strip()]
        if not query_name or not cols:
            return None
        return {
            "label": query_name,
            "children": [
                {"label": c, "drag": f"{{{query_name}.{c}}}"} for c in cols
            ]
        }