from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from desktop_ui import __version__
from desktop_ui.ui.main_window import MainWindow


def _app_icon_path() -> Path:
    icon_name = "icon.ico" if sys.platform.startswith("win") else "icon.png"
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "desktop_ui" / icon_name
    return Path(__file__).resolve().parent / icon_name


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Cadastro Limpo")
    app.setApplicationVersion(__version__)
    icon_path = _app_icon_path()
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
