"""Testes para fusão logradouro + complemento na coluna de endereço."""
import unittest

from sanitiser.updater import _merge_logradouro_cell


class TestMergeLogradouroCell(unittest.TestCase):
    def test_preserves_suffix_after_first_comma(self) -> None:
        self.assertEqual(
            _merge_logradouro_cell("Av. Paulista", "Paulista, 1234, 5º andar"),
            "Av. Paulista, 1234, 5º andar",
        )

    def test_no_comma_replaces_whole_cell(self) -> None:
        self.assertEqual(_merge_logradouro_cell("Av. Paulista", "Paulista"), "Av. Paulista")

    def test_empty_current_uses_api_only(self) -> None:
        self.assertEqual(_merge_logradouro_cell("Rua X", None), "Rua X")
        self.assertEqual(_merge_logradouro_cell("Rua X", ""), "Rua X")

    def test_numeric_cell_treated_as_string_without_comma(self) -> None:
        self.assertEqual(_merge_logradouro_cell("Rua Um", 123), "Rua Um")

    def test_comma_only_preserves_trailing_empty_complement(self) -> None:
        self.assertEqual(_merge_logradouro_cell("Nova", "Velha,"), "Nova,")
