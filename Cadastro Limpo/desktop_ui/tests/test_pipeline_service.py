from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from desktop_ui.application.pipeline_service import PipelineService


class PipelineServiceTests(unittest.TestCase):
    def test_process_generates_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            workbook = tmp_path / "input.xlsx"
            layout = tmp_path / "layout.json"
            patterns = tmp_path / "patterns.json"
            runs_dir = tmp_path / "runs"

            wb = Workbook()
            ws = wb.active
            ws["A1"] = "ok"
            wb.save(workbook)
            wb.close()
            layout.write_text(json.dumps({"x": 1}), encoding="utf-8")
            patterns.write_text(json.dumps({"x": 1}), encoding="utf-8")

            def fake_patterns_loader(_: Path):
                return "rules"

            def fake_char_layout_loader(_: Path):
                return "char-layout"

            def fake_sanitise_layout_loader(_: Path):
                return "sanitise-layout"

            def fake_validator(workbook_path: Path, _rules, _layout, **_kwargs):
                if workbook_path.name == "input.xlsx":
                    return [{"group": "before", "count": 2}]
                return [{"group": "after", "count": 1}]

            def fake_payload_builder(errors):
                if errors and errors[0]["group"] == "before":
                    return {
                        "count": 2,
                        "groups": [{"column": "X", "message": "M1", "count": 2, "errors": []}],
                    }
                return {
                    "count": 1,
                    "groups": [{"column": "X", "message": "M1", "count": 1, "errors": []}],
                }

            def fake_updater(_workbook, _layout, output, **kwargs):
                Path(output).write_bytes(Path(workbook).read_bytes())
                kwargs["progress_stream"].write("progress ok\n")
                kwargs["log_stream"].write("sanitise warning line\n")
                return 1

            def fake_highlight_writer(wb_path, _layout, _errors, out_path):
                Path(out_path).write_bytes(Path(wb_path).read_bytes())

            service = PipelineService(
                runs_base_dir=runs_dir,
                patterns_loader=fake_patterns_loader,
                char_layout_loader=fake_char_layout_loader,
                workbook_validator=fake_validator,
                payload_builder=fake_payload_builder,
                sanitise_layout_loader=fake_sanitise_layout_loader,
                workbook_updater=fake_updater,
                cell_highlight_writer=fake_highlight_writer,
            )

            artifacts = service.process(workbook, layout, patterns)

            self.assertTrue(artifacts.output_workbook_highlighted.exists())
            self.assertTrue(artifacts.input_char_log_json.exists())
            self.assertTrue(artifacts.output_char_log_json.exists())
            self.assertTrue(artifacts.diff_summary_json.exists())
            self.assertTrue(artifacts.diff_summary_txt.exists())
            self.assertIn("sanitise warning line", artifacts.sanitise_log_text)
            self.assertEqual(artifacts.diff_summary_payload["delta_total"], -1)
            names = {p.name for p in artifacts.run_dir.iterdir()}
            self.assertIn("input_sanitised.xlsx", names)
            self.assertNotIn("sanitise.log.txt", names)
            self.assertFalse(any(n.endswith("_sanitise_output.xlsx") for n in names))


if __name__ == "__main__":
    unittest.main()
