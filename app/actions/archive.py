import os
import zipfile
from app.actions.base import Action


class AddToArchiveAction(Action):
    name = "Добавить в архив (zip)"
    icon = "🗜"
    param_labels = {
        "archive":   "Путь к архиву (.zip)",
        "items":     "Файлы/папки (по одному на строку)",
        "mode":      "Режим",
    }
    param_widgets = {
        "items": "multiline",
    }
    param_options = {
        "mode": ["добавить", "перезаписать архив"],
    }

    def execute(self, context):
        archive = (self.params.get("archive") or "").strip()
        if not archive:
            raise ValueError("Путь к архиву не задан")
        if not archive.lower().endswith(".zip"):
            archive += ".zip"

        items_raw = self.params.get("items", "")
        items = [x.strip() for x in items_raw.splitlines() if x.strip()]
        if not items:
            raise ValueError("Не указано ни одного файла/папки")

        mode = self.params.get("mode", "добавить")
        zip_mode = "w" if mode == "перезаписать архив" else "a"

        os.makedirs(os.path.dirname(archive) or ".", exist_ok=True)

        added = 0
        with zipfile.ZipFile(archive, zip_mode, zipfile.ZIP_DEFLATED) as zf:
            for item in items:
                if os.path.isfile(item):
                    zf.write(item, os.path.basename(item))
                    added += 1
                elif os.path.isdir(item):
                    base = os.path.basename(item.rstrip("\\/"))
                    for root, _dirs, files in os.walk(item):
                        for f in files:
                            full = os.path.join(root, f)
                            rel  = os.path.join(base, os.path.relpath(full, item))
                            zf.write(full, rel)
                            added += 1
                else:
                    raise FileNotFoundError(f"Не найдено: {item}")

        context["archive_added"] = added
        context["archive_path"]  = archive


class ExtractArchiveAction(Action):
    name = "Извлечь из архива (zip)"
    icon = "📤"
    file_params = ("archive",)
    param_labels = {
        "archive": "Путь к архиву (.zip)",
        "where":   "Куда извлекать",
        "target":  "Папка назначения (для режима «в другую папку»)",
    }
    param_options = {
        "where": [
            "в папку архива",
            "в подпапку с именем архива",
            "в другую папку",
        ],
    }

    def execute(self, context):
        archive = (self.params.get("archive") or "").strip()
        if not archive or not os.path.isfile(archive):
            raise FileNotFoundError(f"Архив не найден: {archive}")

        where  = self.params.get("where", "в папку архива")
        arc_dir   = os.path.dirname(os.path.abspath(archive))
        arc_stem  = os.path.splitext(os.path.basename(archive))[0]

        if where == "в папку архива":
            dest = arc_dir
        elif where == "в подпапку с именем архива":
            dest = os.path.join(arc_dir, arc_stem)
        else:  # в другую папку
            dest = (self.params.get("target") or "").strip()
            if not dest:
                raise ValueError("Не указана папка назначения")

        os.makedirs(dest, exist_ok=True)

        with zipfile.ZipFile(archive, "r") as zf:
            zf.extractall(dest)
            count = len(zf.namelist())

        context["extract_dir"]   = dest
        context["extract_count"] = count