from __future__ import annotations

import io
import json
import os
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from validator.layout import Layout
from validator.patterns import load_patterns
from validator.validator import (
    WorkbookValidationCancelled,
    grouped_errors_payload,
    validate_workbook,
    write_error_cell_highlights,
)
from sanitiser.layout import SanitiserLayout
from sanitiser.updater import WorkbookUpdateCancelled, update_workbook_from_api

from desktop_ui.application.log_diff_service import compare_char_logs, render_diff_summary_text
from desktop_ui.models.run_artifacts import RunArtifacts


class PipelineCancelled(Exception):
    """Processamento interrompido a pedido do usuário."""


class PipelineService:
    def __init__(
        self,
        runs_base_dir: Optional[Path] = None,
        *,
        patterns_loader: Callable[[Path], Any] = load_patterns,
        char_layout_loader: Callable[[Path], Any] = Layout.load,
        workbook_validator: Callable[..., Any] = validate_workbook,
        payload_builder: Callable[[Any], Dict[str, Any]] = grouped_errors_payload,
        sanitise_layout_loader: Callable[[Path], Any] = SanitiserLayout.load,
        workbook_updater: Callable[..., int] = update_workbook_from_api,
        cell_highlight_writer: Callable[..., None] = write_error_cell_highlights,
    ) -> None:
        self._runs_base_dir = Path(runs_base_dir or Path(__file__).resolve().parents[2] / "runs")
        self._patterns_loader = patterns_loader
        self._char_layout_loader = char_layout_loader
        self._workbook_validator = workbook_validator
        self._payload_builder = payload_builder
        self._sanitise_layout_loader = sanitise_layout_loader
        self._workbook_updater = workbook_updater
        self._cell_highlight_writer = cell_highlight_writer

    def process(
        self,
        workbook_path: Path,
        layout_path: Path,
        patterns_path: Path,
        *,
        on_progress: Optional[Callable[[int, str, int, int, int], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> RunArtifacts:
        workbook = Path(workbook_path)
        layout = Path(layout_path)
        patterns = Path(patterns_path)
        self._validate_inputs(workbook, layout, patterns)

        run_dir = self._make_run_dir()
        output_workbook_highlighted = run_dir / f"{workbook.stem}_sanitised.xlsx"
        input_char_log_json = run_dir / "input_char_log.json"
        output_char_log_json = run_dir / "output_char_log.json"
        diff_summary_json = run_dir / "diff_summary.json"
        diff_summary_txt = run_dir / "diff_summary.txt"

        rules = self._patterns_loader(patterns)
        char_layout = self._char_layout_loader(layout)
        sanitise_layout = self._sanitise_layout_loader(layout)

        cancel_check: Optional[Callable[[], bool]] = None
        if cancel_event is not None:
            cancel_check = cancel_event.is_set

        def emit(phase: Tuple[int, str], done: int, total: int, sheet_row: int = 0) -> None:
            if on_progress is not None:
                on_progress(phase[0], phase[1], done, total, sheet_row)

        sanitise_log_text = ""
        try:
            input_char_payload = self._run_char_validation(
                workbook,
                rules,
                char_layout,
                on_row_progress=lambda d, t, r: emit((0, "Validação (entrada)"), d, t, r),
                cancel_check=cancel_check,
            )
            self._write_json(input_char_log_json, input_char_payload)

            fd, temp_sanitise_name = tempfile.mkstemp(suffix=".xlsx")
            os.close(fd)
            temp_sanitise_workbook = Path(temp_sanitise_name)
            try:
                sanitise_log_stream = io.StringIO()
                sanitise_progress_stream = io.StringIO()
                warnings = self._workbook_updater(
                    workbook,
                    sanitise_layout,
                    temp_sanitise_workbook,
                    log_stream=sanitise_log_stream,
                    progress_stream=sanitise_progress_stream,
                    on_row_progress=lambda d, t, r: emit((1, "Sanitização (APIs)"), d, t, r),
                    cancel_check=cancel_check,
                )
                sanitise_log_text = (
                    sanitise_progress_stream.getvalue()
                    + sanitise_log_stream.getvalue()
                    + f"\nAvisos (sanitiser): {warnings}\n"
                )

                output_char_payload = self._run_char_validation(
                    temp_sanitise_workbook,
                    rules,
                    char_layout,
                    on_row_progress=lambda d, t, r: emit(
                        (2, "Validação da saída e destaque de erros"), d, t + 1, r
                    ),
                    cancel_check=cancel_check,
                    highlight_workbook=output_workbook_highlighted,
                )
                self._write_json(output_char_log_json, output_char_payload)

                diff_summary_payload = compare_char_logs(input_char_payload, output_char_payload)
                self._write_json(diff_summary_json, diff_summary_payload)
                diff_summary_txt.write_text(
                    render_diff_summary_text(diff_summary_payload),
                    encoding="utf-8",
                )
            finally:
                temp_sanitise_workbook.unlink(missing_ok=True)
        except (WorkbookValidationCancelled, WorkbookUpdateCancelled) as exc:
            raise PipelineCancelled() from exc

        return RunArtifacts(
            run_dir=run_dir,
            output_workbook_highlighted=output_workbook_highlighted,
            input_char_log_json=input_char_log_json,
            output_char_log_json=output_char_log_json,
            sanitise_log_text=sanitise_log_text,
            diff_summary_json=diff_summary_json,
            diff_summary_txt=diff_summary_txt,
            input_char_payload=input_char_payload,
            output_char_payload=output_char_payload,
            diff_summary_payload=diff_summary_payload,
        )

    def _validate_inputs(self, workbook: Path, layout: Path, patterns: Path) -> None:
        for path in (workbook, layout, patterns):
            if not path.exists():
                raise ValueError(f"Arquivo não encontrado: {path}")
            if not path.is_file():
                raise ValueError(f"Caminho não aponta para um arquivo: {path}")
        if workbook.suffix.lower() != ".xlsx":
            raise ValueError("O arquivo de entrada deve ser um .xlsx")
        if layout.suffix.lower() != ".json":
            raise ValueError("O arquivo de leiaute deve ser um .json")
        if patterns.suffix.lower() != ".json":
            raise ValueError("O arquivo de padrões deve ser um .json")

    def _make_run_dir(self) -> Path:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        run_dir = self._runs_base_dir / stamp
        idx = 1
        while run_dir.exists():
            idx += 1
            run_dir = self._runs_base_dir / f"{stamp}-{idx:02d}"
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir

    def _run_char_validation(
        self,
        workbook: Path,
        rules: Any,
        char_layout: Any,
        *,
        on_row_progress: Optional[Callable[[int, int, int], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
        highlight_workbook: Optional[Path] = None,
    ) -> Dict[str, Any]:
        last_total_rows = 0

        def validator_progress(d: int, t: int, r: int) -> None:
            nonlocal last_total_rows
            last_total_rows = max(last_total_rows, t)
            if on_row_progress is not None:
                on_row_progress(d, t, r)

        progress_cb = (
            validator_progress if highlight_workbook is not None else on_row_progress
        )

        errors = self._workbook_validator(
            workbook,
            rules,
            char_layout,
            on_row_progress=progress_cb,
            cancel_check=cancel_check,
        )
        if highlight_workbook is not None:
            total_rows = max(last_total_rows, 1)
            if on_row_progress is not None:
                # A fase 2 repassa total como t+1 ao progresso global. Com (d, t) = (rows, rows)
                # a UI via label_done/label_total marcava o passo 3 como concluído antes de gravar
                # o Excel com destaques; usar t = rows+1 deixa um subpasso pendente até o fim da escrita.
                on_row_progress(total_rows, total_rows + 1, -1)
            self._cell_highlight_writer(workbook, char_layout, errors, highlight_workbook)
            if on_row_progress is not None:
                on_row_progress(total_rows + 2, total_rows + 1, -1)
        return self._payload_builder(errors)

    @staticmethod
    def _write_json(path: Path, payload: Dict[str, Any]) -> None:
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
