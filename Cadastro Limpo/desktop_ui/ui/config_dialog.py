from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from desktop_ui.application.config_validation import (
    parse_json_document,
    validate_layout_payload,
    validate_patterns_payload,
)


def _set_tab_as_spaces(editor: QPlainTextEdit, spaces: int = 4) -> None:
    fm = editor.fontMetrics()
    editor.setTabStopDistance(float(fm.horizontalAdvance(" ") * spaces))


class ConfigDialog(QDialog):
    _TAB_LAYOUT = 0
    _TAB_PATTERNS = 1

    def __init__(
        self,
        patterns_path: Path,
        layout_path: Path,
        parent: Optional[QWidget] = None,
        *,
        initial_tab: int = 0,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configurar expressões, domínios e leiaute")
        self.resize(900, 700)
        self._patterns_path = Path(patterns_path)
        self._layout_path = Path(layout_path)

        root = QVBoxLayout(self)
        root.addWidget(QLabel(f"Leiaute: {self._layout_path}"))
        root.addWidget(QLabel(f"Padrões: {self._patterns_path}"))

        self._tabs = QTabWidget()
        self._layout_edit = QPlainTextEdit()
        self._patterns_edit = QPlainTextEdit()
        _set_tab_as_spaces(self._layout_edit, 4)
        _set_tab_as_spaces(self._patterns_edit, 4)
        self._tabs.addTab(self._layout_edit, "layout.json")
        self._tabs.addTab(self._patterns_edit, "patterns.json")
        root.addWidget(self._tabs)

        button_line = QHBoxLayout()
        self._validate_btn = QPushButton("Validar")
        self._save_btn = QPushButton("Salvar")
        self._cancel_btn = QPushButton("Cancelar")
        button_line.addWidget(self._validate_btn)
        button_line.addStretch(1)
        button_line.addWidget(self._save_btn)
        button_line.addWidget(self._cancel_btn)
        root.addLayout(button_line)

        self._validate_btn.clicked.connect(self._validate_documents)
        self._save_btn.clicked.connect(self._save_and_close)
        self._cancel_btn.clicked.connect(self.reject)

        self._load_documents()
        if initial_tab in (self._TAB_LAYOUT, self._TAB_PATTERNS):
            self._tabs.setCurrentIndex(initial_tab)

    def _load_documents(self) -> None:
        try:
            layout_text = self._layout_path.read_text(encoding="utf-8")
            patterns_text = self._patterns_path.read_text(encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Erro de leitura",
                f"Não foi possível carregar os arquivos de configuração.\n{exc}",
            )
            self.reject()
            return
        self._layout_edit.setPlainText(layout_text)
        self._patterns_edit.setPlainText(patterns_text)

    def _validate_documents(self) -> None:
        try:
            self._validate_current_text()
        except ValueError as exc:
            QMessageBox.critical(self, "Erro de validação", str(exc))
            return
        QMessageBox.information(self, "Validação", "Configurações válidas.")

    def _validate_current_text(self) -> tuple[dict, dict]:
        patterns_payload = parse_json_document(self._patterns_edit.toPlainText(), "patterns")
        layout_payload = parse_json_document(self._layout_edit.toPlainText(), "layout")
        validate_patterns_payload(patterns_payload)
        validate_layout_payload(layout_payload)
        return patterns_payload, layout_payload

    def _save_and_close(self) -> None:
        try:
            patterns_payload, layout_payload = self._validate_current_text()
        except ValueError as exc:
            QMessageBox.critical(self, "Erro de validação", str(exc))
            return

        self._patterns_path.write_text(
            json.dumps(patterns_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self._layout_path.write_text(
            json.dumps(layout_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self.accept()
