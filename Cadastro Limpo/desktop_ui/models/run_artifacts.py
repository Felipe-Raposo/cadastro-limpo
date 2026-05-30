from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass(frozen=True)
class RunArtifacts:
    run_dir: Path
    output_workbook_highlighted: Path
    input_char_log_json: Path
    output_char_log_json: Path
    sanitise_log_text: str
    diff_summary_json: Path
    diff_summary_txt: Path
    input_char_payload: Dict[str, Any]
    output_char_payload: Dict[str, Any]
    diff_summary_payload: Dict[str, Any]
