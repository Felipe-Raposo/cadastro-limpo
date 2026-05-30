from __future__ import annotations

import unittest

from desktop_ui.application.log_diff_service import compare_char_logs


class LogDiffServiceTests(unittest.TestCase):
    def test_compare_char_logs_classifies_groups(self) -> None:
        input_payload = {
            "count": 6,
            "groups": [
                {"column": "Nome", "message": "Célula vazia", "count": 2, "errors": []},
                {"column": "CPF", "message": "Regex", "count": 3, "pattern": "ER9", "errors": []},
                {"column": "UF", "message": "Dominio", "count": 1, "domain": "D1", "errors": []},
            ],
        }
        output_payload = {
            "count": 4,
            "groups": [
                {"column": "CPF", "message": "Regex", "count": 1, "pattern": "ER9", "errors": []},
                {"column": "UF", "message": "Dominio", "count": 1, "domain": "D1", "errors": []},
                {"column": "Email", "message": "Regex", "count": 2, "pattern": "ER75", "errors": []},
            ],
        }

        summary = compare_char_logs(input_payload, output_payload)

        self.assertEqual(summary["input_total"], 6)
        self.assertEqual(summary["output_total"], 4)
        self.assertEqual(summary["delta_total"], -2)
        self.assertEqual(len(summary["resolved_groups"]), 1)
        self.assertEqual(len(summary["new_groups"]), 1)
        self.assertEqual(len(summary["changed_groups"]), 1)
        self.assertEqual(summary["unchanged_groups"], 1)

    def test_compare_char_logs_merges_duplicated_groups(self) -> None:
        input_payload = {
            "count": 3,
            "groups": [
                {"column": "CPF", "message": "Regex", "count": 1, "pattern": "ER9", "errors": []},
                {"column": "CPF", "message": "Regex", "count": 2, "pattern": "ER9", "errors": []},
            ],
        }
        output_payload = {"count": 0, "groups": []}

        summary = compare_char_logs(input_payload, output_payload)

        self.assertEqual(len(summary["resolved_groups"]), 1)
        self.assertEqual(summary["resolved_groups"][0]["input_count"], 3)


if __name__ == "__main__":
    unittest.main()
