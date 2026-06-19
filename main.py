# pyinstaller --noconfirm --clean --onedir --windowed --name AutoMouse_scenarios --icon app/resources/automouse.ico --collect-all pywinauto --collect-submodules comtypes --hidden-import keyboard --hidden-import fdb --hidden-import pyperclip --add-data "app/resources;app/resources" main.py
# pyinstaller --noconfirm --clean --onedir --windowed --name AutoMouse --icon app/resources/automouse.ico --collect-all cv2 --collect-all numpy --collect-all pywinauto --collect-submodules comtypes --hidden-import keyboard --hidden-import fdb --hidden-import pyperclip --hidden-import PIL --exclude-module pkg_resources --exclude-module setuptools --add-data "app/resources;app/resources" main.py
import os
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from app.ui.main_window import MainWindow

if __name__ == "__main__":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("AutoMouse.RPA.1")
    except Exception:
        pass

    app = QApplication(sys.argv)

    icon_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "app", "resources", "automouse.ico"
    )
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    win = MainWindow()
    win.showMaximized()
    sys.exit(app.exec_())