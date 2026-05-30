from __future__ import annotations

import shutil
from pathlib import Path

from desktop_ui.models.run_artifacts import RunArtifacts


def export_artifacts_bundle(artifacts: RunArtifacts, destination_dir: Path) -> Path:
    destination = Path(destination_dir)
    destination.mkdir(parents=True, exist_ok=True)

    export_dir = destination / artifacts.run_dir.name
    export_dir.mkdir(parents=True, exist_ok=False)

    files = [
        artifacts.output_workbook_highlighted,
        artifacts.input_char_log_json,
        artifacts.output_char_log_json,
        artifacts.diff_summary_json,
        artifacts.diff_summary_txt,
    ]
    for src in files:
        shutil.copy2(src, export_dir / src.name)
    return export_dir
