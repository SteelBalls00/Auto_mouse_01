import time
import numpy as np
import cv2
import pyautogui as pg


def _imread_unicode(path):
    """cv2.imread не понимает не-ASCII пути — читаем через numpy."""
    with open(path, "rb") as f:
        data = f.read()
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(
            f"Не удалось прочитать изображение: {path}"
        )
    return img


def _screenshot_bgr(region=None):
    """Скриншот в BGR-формате (как ждёт OpenCV)."""
    shot = pg.screenshot(region=region)
    return cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)


def find_image_on_screen(image_path, confidence=0.8, region=None):
    """
    Ищет изображение на экране (или в регионе).
    Возвращает (x, y, w, h) центра-кандидата или None.
    """
    needle = _imread_unicode(image_path)
    h, w = needle.shape[:2]

    haystack = _screenshot_bgr(region=region)
    result = cv2.matchTemplate(haystack, needle, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val < confidence:
        return None

    x0 = max_loc[0] + (region[0] if region else 0)
    y0 = max_loc[1] + (region[1] if region else 0)
    return (x0, y0, w, h)


def wait_for_image(path, timeout=30, confidence=0.8, interval=0.5,
                   stop_event=None, region=None):
    start = time.time()
    while time.time() - start < timeout:
        if stop_event and stop_event.is_set():
            return None
        loc = find_image_on_screen(path, confidence=confidence, region=region)
        if loc:
            return loc
        time.sleep(interval)
    return None


def find_image_in_region(region, image_path, confidence=0.8):
    """
    Совместимость со старым API — возвращает центр (x, y) или None.
    """
    loc = find_image_on_screen(image_path, confidence=confidence, region=region)
    if not loc:
        return None
    x, y, w, h = loc
    return x + w // 2, y + h // 2