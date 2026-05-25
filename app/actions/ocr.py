import os
from app.actions.base import Action


class OcrRegionAction(Action):
    name = "OCR — распознать текст с экрана"
    icon = "🔤"
    file_params = ("image",)
    param_labels = {
        "source":      "Источник",
        "x":           "X (для области экрана)",
        "y":           "Y (для области экрана)",
        "width":       "Ширина",
        "height":      "Высота",
        "image":       "Путь к изображению (для режима «файл»)",
        "lang":        "Язык (rus, eng, rus+eng)",
        "result_name": "Имя результата (для переменной)",
    }
    param_options = {
        "source": ["область экрана", "файл изображения"],
    }

    def execute(self, context):
        import pytesseract
        from PIL import Image

        # Путь к tesseract.exe — настрой если он не в PATH
        tess = os.environ.get("TESSERACT_EXE",
                              r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if os.path.exists(tess):
            pytesseract.pytesseract.tesseract_cmd = tess

        source = self.params.get("source", "область экрана")
        lang   = (self.params.get("lang") or "rus").strip()

        if source == "файл изображения":
            path = (self.params.get("image") or "").strip()
            if not os.path.isfile(path):
                raise FileNotFoundError(f"Изображение не найдено: {path}")
            img = Image.open(path)
        else:
            import pyautogui as pg
            region = (
                int(self.params.get("x", 0)),
                int(self.params.get("y", 0)),
                int(self.params.get("width", 200)),
                int(self.params.get("height", 50)),
            )
            img = pg.screenshot(region=region)

        text = pytesseract.image_to_string(img, lang=lang).strip()

        rname = (self.params.get("result_name") or "").strip() or "ocr"
        context[rname] = {
            "text":  text,
            "empty": 1 if not text else 0,
        }

    def output_vars(self):
        rname = (self.params.get("result_name") or "").strip()
        if not rname:
            return None
        return {
            "label": rname,
            "children": [
                {"label": "text",  "drag": f"{{{rname}.text}}"},
                {"label": "empty", "drag": f"{{{rname}.empty}}"},
            ],
        }