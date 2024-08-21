import os
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from package.ui.main_window import MainWindow

basedir = os.path.dirname(__file__)


def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(os.path.join(basedir, 'icons', 'logo.png')))

    # Set app icon on Windows
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('yadas')

    ex = MainWindow()
    ex.setWindowTitle('YADAS')
    ex.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
