from PyQt5.QtCore import QObject, pyqtSignal, Qt, QMetaObject, Q_ARG, pyqtSlot
from PyQt5.QtWidgets import QMessageBox, QApplication
from app.actions.base import Action


class _DialogInvoker(QObject):
    """
    Диалог должен показываться в GUI-потоке, а сценарий крутится в QThread.
    Этот объект живёт в главном потоке и показывает окно по запросу.
    """
    def __init__(self):
        super().__init__()
        self._result = None

    @pyqtSlot(str, str)
    def show_yesno(self, title, text):
        box = QMessageBox()
        box.setWindowTitle(title or "Вопрос")
        box.setIcon(QMessageBox.Question)
        box.setText(text or "")
        yes = box.addButton("Да", QMessageBox.YesRole)
        box.addButton("Нет", QMessageBox.NoRole)
        box.exec_()
        self._result = "yes" if box.clickedButton() is yes else "no"


# Один общий инвокер в главном потоке
_invoker = None


def _get_invoker():
    global _invoker
    if _invoker is None:
        _invoker = _DialogInvoker()
        # переносим в поток главного приложения
        app = QApplication.instance()
        if app is not None:
            _invoker.moveToThread(app.thread())
    return _invoker


class AskYesNoAction(Action):
    name = "Спросить Да/Нет"
    icon = "❓"
    param_labels = {
        "result_name": "Имя результата (для переменных)",
        "title":       "Заголовок окна",
        "text":        "Текст вопроса",
    }
    param_widgets = {
        "text": "multiline",
    }

    def execute(self, context):
        import threading

        rname = (self.params.get("result_name") or "").strip() or "ask"
        title = self.params.get("title", "Вопрос")
        text  = self.params.get("text", "")

        invoker = _get_invoker()
        done = threading.Event()
        invoker._result = None

        # Вызываем show_yesno в главном потоке синхронно через invokeMethod
        # BlockingQueuedConnection ждёт, пока главный поток покажет окно и вернёт.
        # Но если мы УЖЕ в главном потоке — зовём напрямую.
        app = QApplication.instance()
        if app is not None and threading.current_thread() is threading.main_thread():
            invoker.show_yesno(title, text)
        else:
            QMetaObject.invokeMethod(
                invoker, "show_yesno",
                Qt.BlockingQueuedConnection,
                Q_ARG(str, title), Q_ARG(str, text),
            )

        answer = invoker._result or "no"
        context[rname] = {
            "answer": answer,           # 'yes' | 'no'
            "yes": 1 if answer == "yes" else 0,
            "no":  1 if answer == "no" else 0,
        }

    def output_vars(self):
        rname = (self.params.get("result_name") or "").strip()
        if not rname:
            return None
        return {
            "label": rname,
            "children": [
                {"label": "answer", "drag": f"{{{rname}.answer}}"},
                {"label": "yes",    "drag": f"{{{rname}.yes}}"},
                {"label": "no",     "drag": f"{{{rname}.no}}"},
            ],
        }