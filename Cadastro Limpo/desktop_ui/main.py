from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from desktop_ui import __version__
from desktop_ui.ui.main_window import MainWindow


def _app_icon_path() -> Path:
    resource_dir = (
        Path(sys._MEIPASS) / "desktop_ui"
        if getattr(sys, "frozen", False)
        else Path(__file__).resolve().parent
    )
    icon_candidates = ["icon.png", "icon.ico"]
    for icon_name in icon_candidates:
        icon_path = resource_dir / icon_name
        if icon_path.is_file():
            return icon_path
    return resource_dir / "icon.png"


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
