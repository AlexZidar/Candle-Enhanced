"""Candle Application Entry Point and Initialization."""

import sys
import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon, QFont
from .config import APP_NAME, APP_VERSION
from .ui.main_window import MainWindow


def main() -> int:
    # High-DPI and OpenGL attributes
    QApplication.setApplicationName(APP_NAME)
    QApplication.setApplicationVersion(APP_VERSION)
    QApplication.setOrganizationName("Candle")

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Load stylesheet if available
    styles_dir = os.path.join(os.path.dirname(__file__), "assets", "styles")
    style_path = os.path.join(styles_dir, "theme.qss")
    if os.path.exists(style_path):
        with open(style_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())

    # Set App Icon if available
    images_dir = os.path.join(os.path.dirname(__file__), "assets", "images")
    icon_path = os.path.join(images_dir, "candle_icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()

    # Load file if passed as argument
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        window.loadFile(sys.argv[1])

    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
