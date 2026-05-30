from __future__ import annotations

import unittest

from desktop_ui.application.config_validation import (
    parse_json_document,
    validate_layout_payload,
    validate_patterns_payload,
)


class ConfigValidationTests(unittest.TestCase):
    def test_parse_json_document_requires_object(self) -> None:
        with self.assertRaises(ValueError):
            parse_json_document("[]", "patterns")

    def test_validate_patterns_payload_accepts_example(self) -> None:
        payload = {
            "patterns": {"ER1": r"\d+"},
            "domains": {"D1": ["SP", "RJ"]},
        }
        validate_patterns_payload(payload)

    def test_validate_layout_payload_accepts_minimal_layout(self) -> None:
        payload = {
            "initialLine": 2,
            "columns": {
                "A": {"required": True, "patterns": "ER1"},
                "B": {"required": False, "domain": "D1"},
                "C": {"required": False},
            },
            "sanitiser": {
                "entity": {
                    "cpf_cnpj_column": "C",
                    "cpf": {
                        "api": {"url": "https://x/{cpf}"},
                        "response_to_column": {"NOME": "A"},
                    },
                    "cnpj": {
                        "api": {"url": "https://x/{cnpj}"},
                        "response_to_column": {"razao_social": "A"},
                    },
                }
            },
        }
        validate_layout_payload(payload)


if __name__ == "__main__":
    unittest.main()
