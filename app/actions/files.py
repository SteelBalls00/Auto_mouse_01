import os
import shutil
import glob
import stat
from app.actions.base import Action


class CopyFileAction(Action):
    name = "Скопировать файл"
    icon = "📋"
    file_params = ("src",)
    param_labels = {
        "src":       "Источник (файл)",
        "dst":       "Назначение (файл или папка)",
        "overwrite": "Перезаписывать если существует",
    }

    def execute(self, context):
        src = (self.params.get("src") or "").strip()
        dst = (self.params.get("dst") or "").strip()
        if not src or not os.path.isfile(src):
            raise FileNotFoundError(f"Источник не найден: {src}")

        # Если dst — папка, добавляем имя файла
        if os.path.isdir(dst):
            dst = os.path.join(dst, os.path.basename(src))

        if os.path.exists(dst) and not self.params.get("overwrite", True):
            raise FileExistsError(f"Файл уже существует: {dst}")

        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        shutil.copy2(src, dst)


class MoveFileAction(Action):
    name = "Переместить / вставить файл"
    icon = "📥"
    file_params = ("src",)
    param_labels = {
        "src":       "Источник (файл)",
        "dst":       "Назначение (файл или папка)",
        "overwrite": "Перезаписывать если существует",
    }

    def execute(self, context):
        src = (self.params.get("src") or "").strip()
        dst = (self.params.get("dst") or "").strip()
        if not src or not os.path.isfile(src):
            raise FileNotFoundError(f"Источник не найден: {src}")

        if os.path.isdir(dst):
            dst = os.path.join(dst, os.path.basename(src))

        if os.path.exists(dst):
            if self.params.get("overwrite", True):
                os.remove(dst)
            else:
                raise FileExistsError(f"Файл уже существует: {dst}")

        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
        shutil.move(src, dst)


class DeleteFileAction(Action):
    name = "Удалить файл"
    icon = "🗑"
    param_labels = {
        "path":          "Путь к файлу",
        "ignore_missing": "Не падать если файла нет",
    }

    def execute(self, context):
        path = (self.params.get("path") or "").strip()
        if not path:
            raise ValueError("Путь не задан")
        if not os.path.exists(path):
            if self.params.get("ignore_missing", True):
                return
            raise FileNotFoundError(f"Файл не найден: {path}")
        # снимаем read-only если стоит, иначе remove упадёт
        try:
            os.chmod(path, stat.S_IWRITE)
        except Exception:
            pass
        os.remove(path)


class FindFilesAction(Action):
    name = "Искать файлы в папке"
    icon = "🔎"
    param_labels = {
        "result_name": "Имя результата (для переменных)",
        "folder":      "Папка для поиска",
        "pattern":     "Маска (например *.pdf или dело_*.docx)",
        "recursive":   "Искать во вложенных папках",
    }

    def execute(self, context):
        rname   = (self.params.get("result_name") or "").strip() or "found"
        folder  = (self.params.get("folder") or "").strip()
        pattern = (self.params.get("pattern") or "*").strip() or "*"
        if not folder or not os.path.isdir(folder):
            raise NotADirectoryError(f"Папка не найдена: {folder}")

        if self.params.get("recursive", False):
            paths = glob.glob(os.path.join(folder, "**", pattern), recursive=True)
        else:
            paths = glob.glob(os.path.join(folder, pattern))

        paths = [p for p in paths if os.path.isfile(p)]
        paths.sort()

        # Список dict-ов — можно перебирать в ЦИКЛ по списку
        items = [
            {"path": p, "name": os.path.basename(p)}
            for p in paths
        ]
        context[rname] = items
        context[f"{rname}_count"] = len(items)
        context[f"{rname}_first"] = paths[0] if paths else ""

    def output_vars(self):
        rname = (self.params.get("result_name") or "").strip()
        if not rname:
            return None
        return {
            "label": f"{rname} (список)",
            "children": [
                {"label": "path"},
                {"label": "name"},
            ],
        }


class SetFileAttrAction(Action):
    name = "Установить атрибут файла"
    icon = "🔧"
    param_labels = {
        "path":      "Путь к файлу",
        "attribute": "Атрибут",
        "enable":    "Включить (иначе снять)",
    }
    param_options = {
        "attribute": ["readonly", "hidden", "system", "archive"],
    }

    def execute(self, context):
        path = (self.params.get("path") or "").strip()
        if not path or not os.path.exists(path):
            raise FileNotFoundError(f"Файл не найден: {path}")

        attr   = self.params.get("attribute", "readonly")
        enable = bool(self.params.get("enable", True))

        if attr == "readonly":
            # через chmod — кроссплатформенно
            os.chmod(path, stat.S_IREAD if enable else stat.S_IWRITE)
            return

        # hidden/system/archive — через attrib (Windows)
        import subprocess
        flag_map = {"hidden": "H", "system": "S", "archive": "A"}
        flag = flag_map[attr]
        sign = "+" if enable else "-"
        r = subprocess.run(
            ["attrib", f"{sign}{flag}", path],
            capture_output=True, text=True, encoding="cp866", errors="replace"
        )
        if r.returncode != 0:
            raise RuntimeError(f"attrib вернул ошибку: {r.stdout}{r.stderr}")


class CheckFileAction(Action):
    name = "Проверить наличие файла"
    icon = "📄"
    param_labels = {
        "check_name": "Имя проверки (для переменных)",
        "path":       "Путь к файлу",
    }

    def execute(self, context):
        cname = (self.params.get("check_name") or "").strip() or "file_check"
        path  = (self.params.get("path") or "").strip()
        exists = os.path.isfile(path)
        size   = os.path.getsize(path) if exists else ""
        context[cname] = {"exists": 1 if exists else 0, "size": size}

    def output_vars(self):
        cname = (self.params.get("check_name") or "").strip()
        if not cname:
            return None
        return {
            "label": cname,
            "children": [
                {"label": "exists", "drag": f"{{{cname}.exists}}"},
                {"label": "size",   "drag": f"{{{cname}.size}}"},
            ],
        }