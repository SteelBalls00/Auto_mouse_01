import time
import pyautogui as pg
import cv2
import numpy as np


def wait_for_image(path, timeout=30, confidence=0.8, interval=0.5, stop_event=None):
    """
    Ждёт появления изображения на экране.
    stop_event — threading.Event для прерывания ожидания из другого потока.
    """
    start = time.time()
    while time.time() - start < timeout:
        if stop_event and stop_event.is_set():
            return None
        loc = pg.locateOnScreen(path, confidence=confidence)
        if loc:
            return loc
        time.sleep(interval)
    return None


def find_image_in_region(region, image_path, confidence=0.8):
    """Ищет изображение в регионе экрана через OpenCV."""
    needle = cv2.imread(image_path)
    if needle is None:
        raise FileNotFoundError(f"Файл изображения не найден: {image_path}")

    needle_h, needle_w = needle.shape[:2]

    screenshot = pg.screenshot(region=region)
    haystack = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    result = cv2.matchTemplate(haystack, needle, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val < confidence:
        return None

    x = region[0] + max_loc[0] + needle_w // 2
    y = region[1] + max_loc[1] + needle_h // 2
    return x, y
