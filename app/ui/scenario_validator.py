"""
Статическая проверка сценария перед запуском: структура блоков, ссылки на окна,
плейсхолдеры на несуществующие переменные. Возвращает список замечаний.
"""
import re

from app.actions.registry import ACTION_REGISTRY

# открывающий → закрывающий тип
_BLOCK_PAIRS = {
    "if_start": "end_if",
    "for_each_start": "end_for",
    "while_start": "end_while",
    "repeat_start": "end_repeat",
    "try_start": "end_try",
}
_CLOSERS = set(_BLOCK_PAIRS.values())


def _action_field(action_type, key):
    entry = ACTION_REGISTRY.get(action_type)
    if not entry:
        return None
    return entry[1].get(key)


def validate(actions):
    """Вернуть список замечаний: [(severity, step_no|None, text)], severity = 'err'|'warn'."""
    issues = []

    # ── 1) Структура блоков ──────────────────────────────────────────
    stack = []  # [(тип, № шага)]
    for i, m in enumerate(actions):
        t = m.action_type
        if t in _BLOCK_PAIRS:
            stack.append((t, i + 1))
        elif t in _CLOSERS:
            if not stack:
                issues.append(("err", i + 1, f"«{m.title()}» без открывающего блока"))
            else:
                open_t, _ = stack.pop()
                expected = _BLOCK_PAIRS[open_t]
                if t != expected:
                    issues.append(("err", i + 1,
                                   f"«{m.title()}» не соответствует открытому блоку "
                                   f"(ожидался {expected})"))
        elif t == "else":
            if not any(s[0] == "if_start" for s in stack):
                issues.append(("err", i + 1, "ИНАЧЕ вне блока ЕСЛИ"))
        elif t == "catch":
            if not any(s[0] == "try_start" for s in stack):
                issues.append(("err", i + 1, "Обработчик ошибки (catch) вне блока ПОПРОБОВАТЬ"))
        elif t in ("break", "continue"):
            if not any(s[0] in ("for_each_start", "while_start", "repeat_start")
                       for s in stack):
                issues.append(("warn", i + 1, f"«{m.title()}» вне цикла"))
    for open_t, sno in stack:
        issues.append(("err", sno, f"Блок «{open_t}» (шаг {sno}) не закрыт"))

    # ── 2) Ссылки на окна без «Найти окно» ───────────────────────────
    declared_windows = set()
    for m in actions:
        if m.action_type == "find_window":
            v = (m.params.get("var_name") or "").strip()
            if v:
                declared_windows.add(v)
    for i, m in enumerate(actions):
        if _action_field(m.action_type, "window_var") is not None:
            wv = (m.params.get("window_var") or "").strip()
            if wv and wv not in declared_windows:
                issues.append(("warn", i + 1,
                               f"Окно «{wv}» используется, но нет шага «Найти окно» "
                               f"с такой переменной"))

    # ── 3) Плейсхолдеры на неизвестные переменные ────────────────────
    # Простая модель: накапливаем пространства имён, создаваемые действиями
    # (op_name у python_eval, query_name у sql, имя цикла и т.п.), и проверяем,
    # что ссылки {ns....} ссылаются на уже встреченное или будущее пространство.
    produced = set()
    for m in actions:
        for key in ("op_name", "query_name", "var_name", "out_name", "loop_name",
                    "try_name"):
            v = m.params.get(key)
            if isinstance(v, str) and v.strip():
                produced.add(v.strip())
        # set_variable создаёт переменную с именем "name"
        if m.action_type == "set_variable":
            nm = m.params.get("name")
            if isinstance(nm, str) and nm.strip():
                produced.add(nm.strip())

    # Шаблон настоящей ссылки на переменную: ns.field(.sub) из словесных символов.
    # Это исключает словарные литералы Python ({"ключ": "знач"}) и JSON.
    var_ref = re.compile(r"^\w+(?:\.\w+)+$", re.UNICODE)

    for i, m in enumerate(actions):
        for key, val in m.params.items():
            if not isinstance(val, str) or "{" not in val:
                continue
            for mt in re.finditer(r"\{([^{}]+)\}", val):
                inner = mt.group(1).strip()
                if not var_ref.match(inner):
                    continue   # не похоже на переменную — пропускаем
                ns = inner.split(".")[0]
                if ns in produced:
                    continue
                issues.append(("warn", i + 1,
                               f"Плейсхолдер {mt.group(0)} ссылается на «{ns}», "
                               f"которого не создаёт ни одно действие"))

    return issues
