import os
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QStyleFactory

from package.consts.consts import APP_VERSION, APP_NAME, APP_NAME_LOWER
from package.singleton.config import Config
from package.ui.main_window import MainWindow
from package.utils.utils import get_config_file_content

basedir = os.path.dirname(__file__)


def main():
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create('fusion'))
    app.setWindowIcon(QIcon(os.path.join(basedir, 'icons', 'logo.png')))

    Config().load(get_config_file_content())

    # Set app icon on Windows
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_NAME_LOWER)

    ex = MainWindow()
    ex.setWindowTitle(f'{APP_NAME} - {APP_VERSION}')
    ex.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
