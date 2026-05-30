from __future__ import annotations

import threading
import time
import traceback
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QThread, Qt, QSize, Signal, QTimer
from PySide6.QtGui import QCloseEvent, QFont, QIcon
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QSizePolicy,
    QStyle,
    QStyleFactory,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from desktop_ui import __author__, __author_email__, __description__, __version__
from desktop_ui.application.artifact_service import export_artifacts_bundle
from desktop_ui.application.log_diff_service import render_diff_summary_text
from desktop_ui.application.pipeline_service import PipelineCancelled, PipelineService
from desktop_ui.models.run_artifacts import RunArtifacts
from desktop_ui.ui.config_dialog import ConfigDialog

# Pesos do progresso global: char entrada = 1, sanitise = 38,
# validação da saída + Excel com erros destacados = 2 (uma etapa só).
_PIPELINE_PROGRESS_WEIGHTS: tuple[int, int, int] = (1, 38, 2)
_PIPELINE_PROGRESS_WEIGHT_SUM = sum(_PIPELINE_PROGRESS_WEIGHTS)
_TAB_LAYOUT = 0
_TAB_PATTERNS = 1

_PIPELINE_PHASE_TITLES: tuple[str, str, str] = (
    "Análise do arquivo de entrada",
    "Sanitização do arquivo",
    "Análise do arquivo de saída",
)
_PIPELINE_CHECK_PENDING_COLOR = "#9e9e9e"
_PIPELINE_CHECK_IN_PROGRESS_COLOR = "#e65100"
_PIPELINE_CHECK_DONE_COLOR = "#2e7d32"
_PIPELINE_CHECK_PENDING_SYM = "○"
_PIPELINE_CHECK_IN_PROGRESS_SYM = "◉"
_PIPELINE_CHECK_DONE_SYM = "✓"


def _html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _phase_checklist_marker_html(
    phase_row: int,
    phase_idx: int,
    label_done: int,
    label_total: int,
) -> str:
    lt = max(label_total, 1)
    completed = phase_row < phase_idx or (
        phase_row == phase_idx and label_done >= lt
    )
    if completed:
        return (
            f'<span style="color:{_PIPELINE_CHECK_DONE_COLOR};">'
            f"{_PIPELINE_CHECK_DONE_SYM}</span>"
        )
    if phase_row == phase_idx:
        return (
            f'<span style="color:{_PIPELINE_CHECK_IN_PROGRESS_COLOR};">'
            f"{_PIPELINE_CHECK_IN_PROGRESS_SYM}</span>"
        )
    return (
        f'<span style="color:{_PIPELINE_CHECK_PENDING_COLOR};">'
        f"{_PIPELINE_CHECK_PENDING_SYM}</span>"
    )


def _format_pipeline_status_html(
    *,
    phase_idx: int | None,
    row_line: str,
    rows_caption: str,
    label_done: int,
    label_total: int,
    step_pct: int,
) -> str:
    """Monta o HTML do checklist de fases + bloco de detalhe do progresso."""
    checklist_lines: list[str] = []
    for i, title in enumerate(_PIPELINE_PHASE_TITLES):
        if phase_idx is None:
            marker = (
                f'<span style="color:{_PIPELINE_CHECK_PENDING_COLOR};">'
                f"{_PIPELINE_CHECK_PENDING_SYM}</span>"
            )
        else:
            marker = _phase_checklist_marker_html(i, phase_idx, label_done, label_total)
        checklist_lines.append(f"{marker} {_html_escape(title)}")
    checklist_block = '<div style="margin:0 0 8px 0;">' + "<br/>".join(checklist_lines) + "</div>"

    if phase_idx is None:
        detail = (
            "<div style=\"margin:0;\">"
            f"{_html_escape('A primeira atualização de linhas pode demorar enquanto a planilha é carregada.')}"
            "</div>"
        )
        return checklist_block + detail

    detail_parts: list[str] = []
    if row_line:
        detail_parts.append(_html_escape(row_line.rstrip("\n")))
    detail_parts.append(
        _html_escape(
            f"{rows_caption}: {label_done} / {label_total}  ({step_pct}% desta etapa)"
        )
    )
    detail = '<div style="margin:0;">' + "<br/>".join(detail_parts) + "</div>"
    return checklist_block + detail


def _format_pipeline_status_html_all_complete() -> str:
    lines: list[str] = []
    for title in _PIPELINE_PHASE_TITLES:
        marker = (
            f'<span style="color:{_PIPELINE_CHECK_DONE_COLOR};">'
            f"{_PIPELINE_CHECK_DONE_SYM}</span>"
        )
        lines.append(f"{marker} {_html_escape(title)}")
    checklist_block = '<div style="margin:0 0 8px 0;">' + "<br/>".join(lines) + "</div>"
    footer = f'<div style="margin:0;">{_html_escape("Concluído.")}</div>'
    return checklist_block + footer


def _weighted_pipeline_percent(phase_idx: int, done: int, total: int) -> int:
    weights = _PIPELINE_PROGRESS_WEIGHTS
    if phase_idx < 0 or phase_idx >= len(weights):
        return 0
    total = max(total, 1)
    wsum = _PIPELINE_PROGRESS_WEIGHT_SUM
    completed_before = sum(weights[:phase_idx]) / wsum
    in_phase = weights[phase_idx] / wsum * (done / total)
    return min(100, max(0, int((completed_before + in_phase) * 100.0)))


class ProcessWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)
    cancelled = Signal()
    progress = Signal(int, str, int, int, int)

    def __init__(
        self,
        pipeline: PipelineService,
        workbook: Path,
        layout: Path,
        patterns: Path,
        cancel_event: threading.Event,
    ) -> None:
        super().__init__()
        self._pipeline = pipeline
        self._workbook = workbook
        self._layout = layout
        self._patterns = patterns
        self._cancel_event = cancel_event
        self._progress_emit_interval_sec = 0.1
        self._last_progress_emit_at = 0.0
        self._last_progress_signature: tuple[int, int, int, int] | None = None

    def run(self) -> None:
        # O pipeline corre nesta QThread; sem isto o debugpy (VS Code/Cursor) não para em
        # breakpoints em código chamado daqui (ex.: sanitiser.updater).
        try:
            import debugpy  # type: ignore[import-not-found]

            if debugpy.is_client_connected():
                debugpy.debug_this_thread()
        except Exception:
            pass

        def on_progress(
            phase_idx: int, phase_name: str, done: int, total: int, sheet_row: int
        ) -> None:
            total = max(total, 1)
            signature = (phase_idx, done, total, sheet_row)
            if signature == self._last_progress_signature:
                return
            now = time.monotonic()
            should_emit = (
                self._last_progress_signature is None
                or phase_idx != self._last_progress_signature[0]
                or done >= total
                or sheet_row != self._last_progress_signature[3]
                or (now - self._last_progress_emit_at) >= self._progress_emit_interval_sec
            )
            if not should_emit:
                return
            self._last_progress_signature = signature
            self._last_progress_emit_at = now
            self.progress.emit(phase_idx, phase_name, done, total, sheet_row)

        try:
            result = self._pipeline.process(
                self._workbook,
                self._layout,
                self._patterns,
                on_progress=on_progress,
                cancel_event=self._cancel_event,
            )
        except PipelineCancelled:
            self.cancelled.emit()
            return
        except Exception:
            self.failed.emit(traceback.format_exc())
            return
        self.finished.emit(result)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Cadastro Limpo")
        self.resize(1050, 500)

        self._pipeline = PipelineService()
        self._thread: QThread | None = None
        self._worker: ProcessWorker | None = None
        self._cancel_event: threading.Event | None = None
        self._last_artifacts: RunArtifacts | None = None
        self._process_t0: float = 0.0
        self._last_process_elapsed_sec: float | None = None
        self._path_validation_timer = QTimer(self)
        self._path_validation_timer.setSingleShot(True)
        self._path_validation_timer.setInterval(250)
        self._path_validation_timer.timeout.connect(self._refresh_process_button_state)
        self._inputs_frozen = False

        self._workbook_input = QLineEdit()
        self._layout_input = QLineEdit()
        self._patterns_input = QLineEdit()
        self._process_btn = QPushButton("Processar")
        self._cancel_btn = QPushButton("Cancelar processamento")
        self._resumo_btn = QPushButton("Ver resultado")
        self._about_btn = self._make_about_tool_button()
        self._exit_btn = QPushButton("Sair")
        self._progress = QProgressBar()
        self._progress_lines_label = QLabel()
        self._logs = QPlainTextEdit()

        self._build_ui()
        self._wire_events()
        self._fill_default_paths()

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        form_box = QGroupBox("Arquivos de entrada")
        form = QFormLayout(form_box)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setHorizontalSpacing(8)
        wb_row, self._workbook_browse_btn = self._with_browse(self._workbook_input, "excel")
        form.addRow("Excel (.xlsx):", wb_row)
        layout_row, self._layout_gear_btn, self._layout_browse_btn = (
            self._path_row_with_config_gear(
                self._layout_input, "layout", initial_tab=_TAB_LAYOUT
            )
        )
        form.addRow("Leiaute (.json):", layout_row)
        patterns_row, self._patterns_gear_btn, self._patterns_browse_btn = (
            self._path_row_with_config_gear(
                self._patterns_input, "patterns", initial_tab=_TAB_PATTERNS
            )
        )
        form.addRow("Padrões (.json):", patterns_row)
        root.addWidget(form_box)

        buttons = QHBoxLayout()
        self._process_btn.setEnabled(False)
        buttons.addWidget(self._process_btn)
        buttons.addWidget(self._cancel_btn)
        buttons.addWidget(self._resumo_btn)
        buttons.addStretch(1)
        buttons.addWidget(self._about_btn)
        buttons.addWidget(self._exit_btn)
        root.addLayout(buttons)

        processamento_box = QGroupBox("Processamento")
        processamento_layout = QVBoxLayout(processamento_box)
        fusion = QStyleFactory.create("Fusion")
        if fusion is not None:
            self._progress.setStyle(fusion)
        self._progress.setTextVisible(True)
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat("%p%")
        self._progress_lines_label.setWordWrap(True)
        self._progress_lines_label.setTextFormat(Qt.TextFormat.RichText)
        self._progress_lines_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._progress_lines_label.setText("")
        self._logs.setReadOnly(True)
        self._logs.setMinimumHeight(40)
        self._logs.setPlaceholderText("")
        processamento_layout.addWidget(self._progress)
        processamento_layout.addWidget(self._progress_lines_label)
        processamento_layout.addWidget(self._logs, 1)
        root.addWidget(processamento_box, 1)

        self._cancel_btn.setEnabled(False)
        self._resumo_btn.setEnabled(False)

    def _path_row(
        self,
        line_edit: QLineEdit,
        browse_mode: str,
        *,
        gear_slot: Callable[[], None] | None = None,
    ) -> tuple[QWidget, QToolButton | None, QPushButton]:
        container = QWidget()
        row_layout = QHBoxLayout(container)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        hint_w = line_edit.sizeHint().width()
        base = max(hint_w, line_edit.fontMetrics().horizontalAdvance("M") * 12)
        line_edit.setMinimumWidth(base * 3)
        line_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row_layout.addWidget(line_edit, 1)
        browse = QPushButton("...")
        browse.setFixedWidth(36)
        browse.clicked.connect(lambda: self._browse_file(browse_mode))
        row_layout.addWidget(browse, 0)
        gear: QToolButton | None = None
        if gear_slot is not None:
            gear = self._make_config_gear_button(gear_slot)
            row_layout.addWidget(gear, 0)
        return container, gear, browse

    def _with_browse(self, line_edit: QLineEdit, mode: str) -> tuple[QWidget, QPushButton]:
        row, _, browse = self._path_row(line_edit, mode)
        return row, browse

    def _make_config_gear_button(self, slot: Callable[[], None]) -> QToolButton:
        btn = QToolButton()
        btn.setAutoRaise(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.setToolTip("Configurar expressões, domínios e leiaute")
        side = max(22, self.fontMetrics().height() + 6)
        icon = QIcon.fromTheme("preferences-system")
        if icon.isNull():
            btn.setText("\u2699")
            btn.setFixedSize(side, side)
        else:
            btn.setIcon(icon)
            btn.setIconSize(QSize(side - 8, side - 8))
            btn.setFixedSize(side, side)
        btn.clicked.connect(slot)
        return btn

    def _make_about_tool_button(self) -> QToolButton:
        btn = QToolButton()
        btn.setAutoRaise(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.setToolTip("Sobre o Cadastro Limpo")
        side = max(22, self.fontMetrics().height() + 6)
        icon = QIcon.fromTheme("help-about")
        if icon.isNull():
            icon = QIcon.fromTheme("dialog-information")
        if icon.isNull():
            icon = self.style().standardIcon(
                QStyle.StandardPixmap.SP_MessageBoxInformation
            )
        if icon.isNull():
            btn.setText("\u2139")
            btn.setFixedSize(side, side)
        else:
            btn.setIcon(icon)
            btn.setIconSize(QSize(side - 8, side - 8))
            btn.setFixedSize(side, side)
        btn.clicked.connect(self._show_about)
        return btn

    def _path_row_with_config_gear(
        self, line_edit: QLineEdit, browse_mode: str, *, initial_tab: int
    ) -> tuple[QWidget, QToolButton, QPushButton]:
        container, gear, browse = self._path_row(
            line_edit,
            browse_mode,
            gear_slot=lambda: self._open_config_dialog(initial_tab),
        )
        if gear is None:
            raise RuntimeError("Falha ao criar botão de configuração")
        return container, gear, browse

    def _wire_events(self) -> None:
        self._process_btn.clicked.connect(self._start_process)
        self._cancel_btn.clicked.connect(self._on_cancel_clicked)
        self._resumo_btn.clicked.connect(self._show_last_diff_summary)
        self._exit_btn.clicked.connect(self.close)
        self._workbook_input.textChanged.connect(self._schedule_process_button_state_refresh)
        self._layout_input.textChanged.connect(self._schedule_process_button_state_refresh)
        self._patterns_input.textChanged.connect(self._schedule_process_button_state_refresh)

    def _show_about(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Sobre")
        dlg.setModal(True)
        dlg.setMinimumWidth(440)
        if not self.windowIcon().isNull():
            dlg.setWindowIcon(self.windowIcon())

        root = QVBoxLayout(dlg)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(14)

        app_name = "Cadastro Limpo"
        title = QLabel(app_name)
        title_font = QFont(title.font())
        title_font.setBold(True)
        ps = title_font.pointSize()
        if ps > 0:
            title_font.setPointSize(ps + 3)
        elif title_font.pixelSize() > 0:
            title_font.setPixelSize(title_font.pixelSize() + 4)
        else:
            title_font.setPointSize(15)
        title.setFont(title_font)
        root.addWidget(title)

        desc = QLabel(__description__)
        desc.setWordWrap(True)
        desc.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        root.addWidget(desc)

        line = QFrame(dlg)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        root.addWidget(line)

        meta = QFormLayout()
        meta.setHorizontalSpacing(14)
        meta.setVerticalSpacing(8)
        meta.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        meta.setFormAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        meta.addRow("Versão", QLabel(__version__))
        meta.addRow("Autor", QLabel(__author__))
        email_lbl = QLabel(
            f'<a href="mailto:{_html_escape(__author_email__)}">'
            f"{_html_escape(__author_email__)}</a>"
        )
        email_lbl.setTextFormat(Qt.TextFormat.RichText)
        email_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        email_lbl.setOpenExternalLinks(True)
        meta.addRow("E-mail", email_lbl)
        root.addLayout(meta)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dlg.accept)
        root.addWidget(buttons)

        dlg.exec()

    def _inputs_complete(self) -> bool:
        wb = self._workbook_input.text().strip()
        lo = self._layout_input.text().strip()
        pa = self._patterns_input.text().strip()
        if not wb or not lo or not pa:
            return False
        workbook = Path(wb)
        layout = Path(lo)
        patterns = Path(pa)
        return workbook.exists() and layout.exists() and patterns.exists()

    def _refresh_process_button_state(self) -> None:
        if self._thread is not None:
            return
        self._process_btn.setEnabled(
            self._inputs_complete() and not self._inputs_frozen
        )

    def _schedule_process_button_state_refresh(self) -> None:
        if self._thread is not None or self._inputs_frozen:
            return
        self._path_validation_timer.start()

    def _fill_default_paths(self) -> None:
        tools_dir = Path(__file__).resolve().parents[2]
        self._layout_input.setText(str(tools_dir / "layout.morador.json"))
        self._patterns_input.setText(str(tools_dir / "patterns.json"))

    def _browse_file(self, mode: str) -> None:
        if mode == "excel":
            path, _ = QFileDialog.getOpenFileName(self, "Selecionar Excel", "", "Excel (*.xlsx)")
            if path:
                self._workbook_input.setText(path)
            return
        path, _ = QFileDialog.getOpenFileName(self, "Selecionar JSON", "", "JSON (*.json)")
        if not path:
            return
        if mode == "layout":
            self._layout_input.setText(path)
        elif mode == "patterns":
            self._patterns_input.setText(path)

    def _open_config_dialog(self, initial_tab: int = 0) -> None:
        try:
            patterns = Path(self._patterns_input.text().strip())
            layout = Path(self._layout_input.text().strip())
            if not patterns.exists() or not layout.exists():
                raise ValueError(
                    "Selecione caminhos válidos de padrões e de leiaute antes de configurar."
                )
        except ValueError as exc:
            QMessageBox.warning(self, "Configuração", str(exc))
            return

        dialog = ConfigDialog(patterns, layout, self, initial_tab=initial_tab)
        if dialog.exec():
            self._append_log("Configuração salva com sucesso.")

    def _start_process(self) -> None:
        if self._thread is not None:
            QMessageBox.warning(
                self, "Processamento", "Já existe um processamento em andamento."
            )
            return

        workbook = Path(self._workbook_input.text().strip())
        layout = Path(self._layout_input.text().strip())
        patterns = Path(self._patterns_input.text().strip())
        if not workbook.exists():
            QMessageBox.warning(
                self, "Entrada inválida", "Selecione um arquivo Excel válido."
            )
            return
        if not layout.exists() or not patterns.exists():
            QMessageBox.warning(
                self, "Entrada inválida", "Selecione arquivos JSON válidos."
            )
            return

        self._last_artifacts = None
        self._last_process_elapsed_sec = None
        self._resumo_btn.setEnabled(False)
        self._append_log(f"Processando arquivo {workbook.name}")
        self._cancel_event = threading.Event()

        self._thread = QThread(self)
        self._worker = ProcessWorker(self._pipeline, workbook, layout, patterns, self._cancel_event)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_pipeline_progress, Qt.ConnectionType.QueuedConnection)
        self._worker.finished.connect(self._on_process_done)
        self._worker.failed.connect(self._on_process_error)
        self._worker.cancelled.connect(self._on_process_cancelled, Qt.ConnectionType.QueuedConnection)
        self._worker.finished.connect(self._cleanup_thread)
        self._worker.failed.connect(self._cleanup_thread)
        self._worker.cancelled.connect(self._cleanup_thread)
        self._set_busy(True)
        self._process_t0 = time.monotonic()
        self._thread.start()

    def _on_pipeline_progress(
        self, phase_idx: int, _phase_name: str, done: int, total: int, sheet_row: int
    ) -> None:
        total = max(total, 1)
        line_pct = min(100, (done * 100) // total)
        overall_pct = _weighted_pipeline_percent(phase_idx, done, total)
        self._progress.setRange(0, 100)
        self._progress.setValue(overall_pct)
        self._progress.setFormat("%p%")
        row_line = ""
        if sheet_row == -1:
            row_line = "Gravando Excel com erros destacados…\n"
        if phase_idx in (0, 2):
            rows_caption = "Linhas verificadas"
            label_done, label_total = done, total
            # Na fase 2 o pipeline usa total = linhas + 1 para caber os passos de destaque;
            # no texto mostramos só a contagem de linhas da planilha.
            if phase_idx == 2 and total > 1:
                label_total = total - 1
                label_done = min(done, label_total)
            label_total = max(label_total, 1)
            step_pct = min(100, (label_done * 100) // label_total)
        else:
            rows_caption = "Linhas processadas"
            label_done, label_total = done, total
            step_pct = line_pct
        self._progress_lines_label.setText(
            _format_pipeline_status_html(
                phase_idx=phase_idx,
                row_line=row_line,
                rows_caption=rows_caption,
                label_done=label_done,
                label_total=label_total,
                step_pct=step_pct,
            )
        )

    def _on_process_done(self, artifacts: RunArtifacts) -> None:
        self._inputs_frozen = True
        elapsed = max(0.0, time.monotonic() - self._process_t0)
        self._last_process_elapsed_sec = elapsed
        self._last_artifacts = artifacts
        self._progress.setRange(0, 100)
        self._progress.setValue(100)
        self._progress.setFormat("%p%")
        self._progress_lines_label.setText(_format_pipeline_status_html_all_complete())
        self._append_log(f"Processamento concluído. Run: {artifacts.run_dir}")
        self._append_log(f"Excel de saída (sanitizado): {artifacts.output_workbook_highlighted}")
        self._open_diff_summary_dialog(artifacts, elapsed_seconds=elapsed)

    def _on_process_error(self, tb: str) -> None:
        self._last_artifacts = None
        self._last_process_elapsed_sec = None
        self._resumo_btn.setEnabled(False)
        self._progress.setFormat("%p%")
        self._progress_lines_label.setText("Erro no processamento (detalhes no registro abaixo).")
        self._append_log("Erro durante processamento.")
        self._append_log(tb)
        message_box = QMessageBox(self)
        message_box.setIcon(QMessageBox.Icon.Critical)
        message_box.setWindowTitle("Erro de processamento")
        message_box.setText("Falha durante o processamento do pipeline.")
        message_box.setInformativeText(
            "Verifique os caminhos de entrada e consulte os detalhes técnicos abaixo."
        )
        message_box.setDetailedText(tb)
        message_box.exec()

    def _on_process_cancelled(self) -> None:
        self._last_artifacts = None
        self._last_process_elapsed_sec = None
        self._resumo_btn.setEnabled(False)
        self._progress.setFormat("%p%")
        self._progress_lines_label.setText("Processamento cancelado pelo usuário.")
        self._append_log("Processamento cancelado pelo usuário.")

    def _on_cancel_clicked(self) -> None:
        if self._cancel_event is None:
            return
        answer = QMessageBox.question(
            self,
            "Cancelar processamento",
            "Deseja realmente cancelar o processamento em andamento?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._cancel_event.set()
        self._cancel_btn.setEnabled(False)

    def _cleanup_thread(self) -> None:
        if self._thread is not None:
            self._thread.quit()
            finished = self._thread.wait(5000)
            if not finished:
                self._append_log("Aviso: thread não finalizou dentro do timeout de 5 segundos.")
            self._thread = None
            self._worker = None
        self._cancel_event = None
        self._set_busy(False)

    def _set_busy(self, value: bool) -> None:
        paths_editable = (not value) and not self._inputs_frozen
        self._workbook_input.setReadOnly(not paths_editable)
        self._layout_input.setReadOnly(not paths_editable)
        self._patterns_input.setReadOnly(not paths_editable)
        self._workbook_browse_btn.setEnabled(paths_editable)
        self._layout_browse_btn.setEnabled(paths_editable)
        self._patterns_browse_btn.setEnabled(paths_editable)
        self._layout_gear_btn.setEnabled(paths_editable)
        self._patterns_gear_btn.setEnabled(paths_editable)
        if value:
            self._process_btn.setEnabled(False)
        else:
            self._refresh_process_button_state()
        self._cancel_btn.setEnabled(value)
        self._resumo_btn.setEnabled(not value and self._last_artifacts is not None)
        if value:
            self._progress.setRange(0, 100)
            self._progress.setValue(0)
            self._progress.setFormat("%p%")
            self._progress_lines_label.setText(
                _format_pipeline_status_html(
                    phase_idx=None,
                    row_line="",
                    rows_caption="",
                    label_done=0,
                    label_total=1,
                    step_pct=0,
                )
            )

    def _export_artifacts_from_dialog(
        self, parent: QWidget, artifacts: RunArtifacts
    ) -> None:
        destination = QFileDialog.getExistingDirectory(
            parent, "Selecionar pasta para exportar"
        )
        if not destination:
            return
        try:
            export_dir = export_artifacts_bundle(artifacts, Path(destination))
        except FileExistsError:
            QMessageBox.warning(
                parent,
                "Salvar resultados",
                "Já existe um pacote com este nome na pasta de destino.",
            )
            return
        except Exception as exc:
            QMessageBox.critical(parent, "Salvar resultados", str(exc))
            return
        self._append_log(f"Resultados exportados para: {export_dir}")
        QMessageBox.information(
            parent, "Salvar resultados", f"Artefatos exportados em:\n{export_dir}"
        )

    @staticmethod
    def _format_process_elapsed(seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.1f} s"
        total = max(0, int(round(seconds)))
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        if h == 0:
            return f"{m:02d}m{s:02d}s"
        return f"{h:02d}h{m:02d}m{s:02d}s"

    def _open_diff_summary_dialog(
        self,
        artifacts: RunArtifacts,
        *,
        elapsed_seconds: float | None = None,
    ) -> None:
        if elapsed_seconds is None:
            elapsed_seconds = self._last_process_elapsed_sec
        dialog = QDialog(self)
        dialog.setWindowTitle("Resultado")
        dialog.resize(720, 520)
        layout = QVBoxLayout(dialog)
        intro_text = (
            "Comparação entre os logs do validator na entrada e na saída do sanitise. "
            "O mesmo texto está salvo em diff_summary.txt no diretório do run."
        )
        if elapsed_seconds is not None:
            intro_text += (
                "\n\nTempo total de processamento: "
                f"{self._format_process_elapsed(elapsed_seconds)}."
            )
        intro = QLabel(intro_text)
        intro.setWordWrap(True)
        layout.addWidget(intro)
        view = QPlainTextEdit()
        view.setReadOnly(True)
        view.setPlainText(render_diff_summary_text(artifacts.diff_summary_payload))
        layout.addWidget(view)

        footer = QLabel(
            'O botão "Salvar resultados" exporta os artefatos '
            "(Excel sanitizado .xlsx, JSONs do validator e resultado da comparação)."
        )
        footer.setWordWrap(True)
        layout.addWidget(footer)

        button_row = QHBoxLayout()
        save_btn = QPushButton("Salvar resultados")
        save_btn.clicked.connect(
            lambda: self._export_artifacts_from_dialog(dialog, artifacts)
        )
        button_row.addWidget(save_btn)
        button_row.addStretch(1)
        ok_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        ok_box.accepted.connect(dialog.accept)
        button_row.addWidget(ok_box)
        layout.addLayout(button_row)

        dialog.exec()

    def _show_last_diff_summary(self) -> None:
        if self._thread is not None:
            QMessageBox.warning(
                self,
                "Processamento",
                "Aguarde o processamento em andamento antes de abrir o resultado.",
            )
            return
        if self._last_artifacts is None:
            QMessageBox.information(
                self,
                "Resultado",
                "Não há resultado disponível. Execute o processamento com sucesso primeiro.",
            )
            return
        self._open_diff_summary_dialog(self._last_artifacts)

    def _append_log(self, message: str) -> None:
        self._logs.appendPlainText(message)
        self._logs.verticalScrollBar().setValue(self._logs.verticalScrollBar().maximum())

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self._thread is not None:
            QMessageBox.warning(
                self, "Aplicação", "Aguarde o processamento finalizar antes de sair."
            )
            event.ignore()
            return
        event.accept()
