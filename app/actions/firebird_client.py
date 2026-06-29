"""
Поиск клиента Firebird (fbclient.dll) в собранном приложении.

Когда программа запущена из .exe (PyInstaller), fbclient.dll лежит внутри папки
сборки (_internal), а драйвер fdb по умолчанию её там не ищет — отсюда ошибка
«The location of Firebird Client Library could not be determined».
Здесь мы один раз находим fbclient.dll рядом с .exe или в _internal, добавляем
эту папку в путь поиска DLL (чтобы подтянулась зависимость icudt30.dll) и явно
сообщаем драйверу путь к клиенту.
"""
import os
import sys

_done = False


def ensure_loaded():
    global _done
    if _done:
        return
    _done = True

    # Из исходников (не собранный) fdb сам находит клиент — ничего не делаем.
    if not getattr(sys, "frozen", False):
        return

    # Каталоги, где может лежать fbclient.dll: _internal и папка рядом с .exe
    candidates = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(meipass)
    candidates.append(os.path.dirname(sys.executable))

    for d in candidates:
        dll = os.path.join(d, "fbclient.dll")
        if not os.path.exists(dll):
            continue
        # чтобы зависимость fbclient (icudt30.dll) тоже нашлась
        try:
            os.add_dll_directory(d)
        except Exception:
            pass
        os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
        # явно указываем драйверу путь к клиенту (только если ещё не загружен)
        import fdb
        if getattr(fdb, "api", None) is None:
            fdb.load_api(dll)
        return
    # fbclient.dll не нашли — пусть fdb попробует сам (и выдаст свою ошибку)
