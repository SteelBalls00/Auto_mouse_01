import logging
import os
import re
from datetime import datetime


def _safe_filename(name):
    """Убрать недопустимые в имени файла символы."""
    name = re.sub(r'[\\/:*?"<>|]+', "_", name)
    name = name.strip().strip(".") or "scenario"
    return name[:80]


def setup_run_logger(scenario_name, project_root):
    """
    Создаёт logger для одного запуска сценария.
    Файл: <project_root>/logs/YYYY-MM-DD_HH-MM-SS__<scenario>.log
    Возвращает (logger, log_path).
    """
    logs_dir = os.path.join(project_root, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    fname     = f"{timestamp}__{_safe_filename(scenario_name)}.log"
    log_path  = os.path.join(logs_dir, fname)

    # Уникальное имя logger'а — чтобы параллельные запуски не путались
    logger = logging.getLogger(f"scenario.{timestamp}.{id(scenario_name)}")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # не дублировать в корневой логгер

    # Очищаем хендлеры если logger по какой-то причине переиспользовался
    for h in list(logger.handlers):
        logger.removeHandler(h)

    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S"
    ))
    logger.addHandler(handler)
    return logger, log_path


def close_logger(logger):
    """Закрыть файловые хендлеры — освободить файл."""
    for h in list(logger.handlers):
        try:
            h.close()
        except Exception:
            pass
        logger.removeHandler(h)