from actions.base import Action
from actions.image_utils import wait_for_image

class WaitImageAction(Action):
    name = "Wait Image"

    def execute(self, context):
        loc = wait_for_image(
            self.params["image"],
            timeout=self.params["timeout"],
            confidence=self.params["confidence"]
        )

        if not loc:
            raise RuntimeError("Image not found (timeout)")

        context["last_image"] = loc
