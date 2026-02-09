from actions.wait import WaitAction
from actions.run_program import RunProgramAction
from actions.click_xy import ClickXYAction
from actions.type_text import TypeTextAction
from actions.wait_image import WaitImageAction
from actions.click_image import ClickImageAction
from actions.click_image_in_window import ClickImageInWindowAction


ACTION_REGISTRY = {
    "wait": (WaitAction, {"ms": 1000}),
    "run_program": (RunProgramAction, {"path": ""}),
    "click_xy": (ClickXYAction, {"x": 0, "y": 0}),
    "type_text": (TypeTextAction, {"text": "", "enter": False}),
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
        {
            "window_title": "",
            "image": "",
            "timeout": 30,
            "confidence": 0.8
        }
    )

}
