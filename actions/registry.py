from actions.wait import WaitAction
from actions.run_program import RunProgramAction
from actions.click_xy import ClickXYAction
from actions.type_text import TypeTextAction
from actions.wait_image import WaitImageAction, ClickImageAction
from actions.click_image_in_window import ClickImageInWindowAction
from actions.cmd import CmdAction
from actions.sql import SqlQueryAction
from actions.press_key import PressKeyAction
from actions.control_flow import IfStartAction, ElseAction, EndIfAction
from actions.uni_stat import UniStat2003Action

# Формат: "ключ": (Класс, params_по_умолчанию)
ACTION_REGISTRY = {
    "wait": (
        WaitAction,
        {"ms": 1000}
    ),
    "run_program": (
        RunProgramAction,
        {"path": ""}
    ),
    "click_xy": (
        ClickXYAction,
        {"x": 0, "y": 0}
    ),
    "type_text": (
        TypeTextAction,
        {"text": "", "enter": False, "delay": 0}
    ),
    "wait_image": (
        WaitImageAction,
        {"image": "", "timeout": 30, "confidence": 0.8}
    ),
    "click_image": (
        ClickImageAction,
        {"image": "", "timeout": 30, "confidence": 0.8}
    ),
    "click_image_in_window": (
        ClickImageInWindowAction,
        {"window_title": "", "image": "", "timeout": 30, "confidence": 0.8}
    ),
    "cmd": (
        CmdAction,
        {"command": "", "timeout": 30, "capture": False}
    ),
    "sql": (
        SqlQueryAction,
        {
            "query_name":  "",
            "config":      "",
            "query":       "",
            "columns":     "",
            "expect_rows": False,
        }
    ),
    "press_key": (
        PressKeyAction,
        {"key": "enter", "combo": "", "times": 1, "delay_ms": 0}
    ),
    "if_start": (
        IfStartAction,
        {"left": "", "operator": "не пусто", "right": ""}
    ),
    "else": (
        ElseAction,
        {}
    ),
    "end_if": (
        EndIfAction,
        {}
    ),
    "uni_stat_2003": (
        UniStat2003Action,
        {
            "filter":        "",
            "uni_path":      r"C:\AGORA-SOFT\Justice\Client\UniStat2003.UNI",
            "window_titles":
                "Гражданские, Административные дела. 1-я инстанция. Апелляция р.с.\n"
                "Материалы (пользователь\n"
                "Дела об АП. 1-я инстанция\n"
                "Дела об АП. 1-й пересмотр\n"
                "Уголовные дела. 1-я инстанция. Апелляция р.с.",
            "require_any":   False,
        }
    ),
}
