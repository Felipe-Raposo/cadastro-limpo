"""Atualiza planilhas Excel com dados de CPF/CNPJ e endereço (CEP) via APIs no leiaute.

Copyright (c) 2026. Todos os direitos reservados.
Felipe Raposo <feliperaposo@gmail.com>
"""

__all__ = ["SanitiserLayout", "update_workbook_from_api"]

from sanitiser.layout import SanitiserLayout
from sanitiser.updater import update_workbook_from_api
