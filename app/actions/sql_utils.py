import re


def parse_select_columns(sql):
    """
    Достаёт имена колонок результата из текста SELECT-запроса.

    Логика выбора имени для каждого элемента списка:
      • есть «AS алиас»            → алиас
      • просто a.b.c / a.b / a     → часть после последней точки
      • «выражение алиас» (без AS) → последний идентификатор
      • выражение без алиаса        → пропускается (имя не определить)

    Корректно обрабатывает запятые внутри скобок и функций, CASE…END,
    подзапросы в списке (их FROM/запятые игнорируются — они внутри скобок),
    а также FIRST/SKIP/DISTINCT в начале.
    """
    if not sql:
        return []

    s = sql
    # убираем комментарии
    s = re.sub(r"--[^\n]*", " ", s)
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)

    m = re.search(r"\bSELECT\b", s, re.I)
    if not m:
        return []
    rest = s[m.end():]

    # срезаем модификаторы в начале списка
    rest = re.sub(r"^\s*(DISTINCT|ALL)\b", " ", rest, flags=re.I)
    rest = re.sub(r"^\s*SKIP\s+\d+", " ", rest, flags=re.I)
    rest = re.sub(r"^\s*FIRST\s+\d+", " ", rest, flags=re.I)
    rest = re.sub(r"^\s*SKIP\s+\d+", " ", rest, flags=re.I)

    # ищем FROM на нулевой глубине вложенности скобок
    upper = rest.upper()
    depth = 0
    end = len(rest)
    i = 0
    while i < len(rest):
        c = rest[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth = max(0, depth - 1)
        elif depth == 0 and upper.startswith("FROM", i):
            before = rest[i - 1] if i > 0 else " "
            after = rest[i + 4] if i + 4 < len(rest) else " "
            if not (before.isalnum() or before == "_") and \
               not (after.isalnum() or after == "_"):
                end = i
                break
        i += 1

    cols_part = rest[:end]

    # разбиваем по запятым на нулевой глубине
    items = []
    depth = 0
    cur = ""
    for c in cols_part:
        if c == "(":
            depth += 1
            cur += c
        elif c == ")":
            depth = max(0, depth - 1)
            cur += c
        elif c == "," and depth == 0:
            items.append(cur)
            cur = ""
        else:
            cur += c
    if cur.strip():
        items.append(cur)

    names = []
    for it in items:
        name = _column_name(it)
        if name:
            names.append(name)
    return names


def _column_name(expr):
    e = expr.strip().rstrip(";").strip()
    if not e:
        return None

    # AS алиас (алиас может быть в двойных кавычках)
    m = re.search(r'\bAS\s+("[^"]+"|\w+)\s*$', e, re.I)
    if m:
        return m.group(1).strip('"')

    # чистый идентификатор / table.column
    if re.match(r"^[\w.]+$", e):
        return e.split(".")[-1]

    # «выражение алиас» без AS — берём последний идентификатор,
    # кроме служебных слов вроде END
    m2 = re.search(r'("[^"]+"|\w+)\s*$', e)
    if m2:
        tail = m2.group(1).strip('"')
        if tail.upper() in ("END",):
            return None
        return tail

    return None
