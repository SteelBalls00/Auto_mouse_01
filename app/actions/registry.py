from app.actions.wait import WaitAction
from app.actions.run_program import RunProgramAction
from app.actions.click_xy import ClickXYAction
from app.actions.type_text import TypeTextAction
from app.actions.wait_image import WaitImageAction, ClickImageAction
from app.actions.click_image_in_window import ClickImageInWindowAction
from app.actions.cmd import CmdAction
from app.actions.sql import SqlQueryAction
from app.actions.press_key import PressKeyAction
from app.actions.control_flow import IfStartAction, ElseAction, EndIfAction
from app.actions.uni_stat import UniStat2003Action
from app.actions.sql_many import SqlQueryManyAction
from app.actions.loop import (
    ForEachStartAction, EndForAction, BreakAction, ContinueAction
)
from app.actions.window import (
    FindWindowAction, WindowFocusAction,
    WindowClickXYAction, WindowClickElementAction
)
from app.actions.python_eval import PythonEvalAction
from app.actions.run_scenario import RunScenarioAction
from app.actions.while_loop import WhileStartAction, EndWhileAction
from app.actions.checks import CheckImageAction, CheckProcessAction, CheckWindowAction
from app.actions.process_service import (
    KillProcessAction, StartServiceAction, StopServiceAction
)
from app.actions.files import (
    CopyFileAction, MoveFileAction, DeleteFileAction,
    FindFilesAction, SetFileAttrAction, CheckFileAction
)


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
        {"image": "", "timeout": 30, "confidence": 0.8, "offset_x": 0, "offset_y": 0}
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
    "sql_many": (
        SqlQueryManyAction,
        {
            "query_name":  "",
            "config":      "",
            "query":       "",
            "columns":     "",
            "expect_rows": False,
        }
    ),
    "for_each_start": (
        ForEachStartAction,
        {"loop_name": "", "source": "", "columns": ""}
    ),
    "end_for": (
        EndForAction,
        {}
    ),
    "break": (
        BreakAction,
        {}
    ),
    "continue": (
        ContinueAction,
        {}
    ),
    "find_window": (
        FindWindowAction,
        {
            "var_name":     "",
            "backend":      "win32",
            "title":        "",
            "class_name":   "",
            "process_name": "",
            "timeout":      10,
        }
    ),
    "window_focus": (
        WindowFocusAction,
        {"window_var": ""}
    ),
    "window_click_xy": (
        WindowClickXYAction,
        {"window_var": "", "x": 0, "y": 0, "button": "left"}
    ),
    "window_click_element": (
        WindowClickElementAction,
        {
            "window_var":   "",
            "auto_id":      "",
            "control_type": "",
            "name":         "",
            "class_name":   "",
            "instance":     "",
            "double_click": False,
        }
    ),
    "python_eval": (
        PythonEvalAction,
        {
            "op_name": "",
            "code":    "",
            "outputs": "",
        }
    ),
    "run_scenario": (
        RunScenarioAction,
        {"scenario_path": "", "stop_on_error": True}
    ),
    "while_start": (
        WhileStartAction,
        {"left": "", "operator": "не пусто", "right": "", "max_iter": 10000}
    ),
    "end_while": (
        EndWhileAction,
        {}
    ),
    "check_image": (
        CheckImageAction,
        {"check_name": "", "image": "", "confidence": 0.8}
    ),
    "check_process": (
        CheckProcessAction,
        {"check_name": "", "process_name": ""}
    ),
    "check_window": (
        CheckWindowAction,
        {"check_name": "", "title": ""}
    ),
    "kill_process": (
        KillProcessAction,
        {"by": "process_name", "value": "", "result_name": ""}
    ),
    "start_service": (
        StartServiceAction,
        {"service": ""}
    ),
    "stop_service": (
        StopServiceAction,
        {"service": ""}
    ),
    "copy_file": (
        CopyFileAction,
        {"src": "", "dst": "", "overwrite": True}
    ),
    "move_file": (
        MoveFileAction,
        {"src": "", "dst": "", "overwrite": True}
    ),
    "delete_file": (
        DeleteFileAction,
        {"path": "", "ignore_missing": True}
    ),
    "find_files": (
        FindFilesAction,
        {"result_name": "", "folder": "", "pattern": "*", "recursive": False}
    ),
    "set_file_attr": (
        SetFileAttrAction,
        {"path": "", "attribute": "readonly", "enable": True}
    ),
    "check_file": (
        CheckFileAction,
        {"check_name": "", "path": ""}
    ),
}
