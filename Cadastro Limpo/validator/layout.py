from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Union


def _normalize_col_letter(col: str) -> str:
    c = col.strip().upper()
    if not c:
        raise ValueError(f"Letra de coluna inválida: {col!r}")
    return c


def _normalize_rule_entry(col: str, value: Any) -> List[str]:
    """String (uma ER) ou lista de ids (OR)."""
    if isinstance(value, str):
        if not value.strip():
            raise ValueError(f"Id de regra vazio para coluna {col!r}")
        return [value.strip()]
    if isinstance(value, list):
        if not value:
            raise ValueError(f"Lista de regras vazia para coluna {col!r}")
        out: List[str] = []
        for i, item in enumerate(value):
            if not isinstance(item, str) or not item.strip():
                raise ValueError(
                    f"Item {i} da lista de regras da coluna {col!r} deve ser string não vazia"
                )
            out.append(item.strip())
        return out
    raise ValueError(
        f"Em {col!r}: patterns como string ou lista de strings, obteve {type(value).__name__}"
    )


def _patterns_from_column_spec(col: str, patterns_val: Any) -> List[str]:
    """patterns: null = sem ER; string; ou lista de ids ER."""
    if patterns_val is None:
        return []
    if isinstance(patterns_val, (str, list)):
        return _normalize_rule_entry(col, patterns_val)
    raise ValueError(
        f"Coluna {col!r}: 'patterns' deve ser null, string ou lista de ids ER, "
        f"obteve {type(patterns_val).__name__}"
    )


@dataclass(frozen=True)
class Layout:
    """Configuração de onde e o que validar na planilha (JSON com ``columns``)."""

    initial_line: int
    #: Por coluna: lista de ids ER (vazia = sem regex, só obrigatoriedade se ``required``).
    rules: Dict[str, List[str]]
    #: Por coluna: id de domínio (ex. ``D1``) quando a coluna usa ``domain`` no JSON.
    domain_rules: Dict[str, str]
    #: Colunas com ``required: true`` no layout.
    required_columns: FrozenSet[str]
    sheet_name: Optional[str] = None
    descriptions: Dict[str, str] = field(default_factory=dict)
    column_types: Dict[str, str] = field(default_factory=dict)

    @staticmethod
    def load(path: Union[Path, str]) -> Layout:
        p = Path(path)
        with p.open(encoding="utf-8") as f:
            raw: Any = json.load(f)

        if not isinstance(raw, dict):
            raise ValueError("Layout deve ser um objeto JSON")

        try:
            initial = raw["initialLine"]
            columns = raw["columns"]
        except KeyError as e:
            raise ValueError(
                f"Layout JSON faltando chave obrigatória: {e.args[0]} "
                "(esperado: initialLine, columns)"
            ) from e

        if not isinstance(initial, int) or initial < 1:
            raise ValueError("initialLine deve ser inteiro >= 1 (1 = primeira linha do Excel)")

        if not isinstance(columns, dict) or not columns:
            raise ValueError("columns deve ser objeto não vazio")

        rules: Dict[str, List[str]] = {}
        domain_rules: Dict[str, str] = {}
        descriptions: Dict[str, str] = {}
        column_types: Dict[str, str] = {}
        required_list: List[str] = []

        for col_key, spec in columns.items():
            if not isinstance(col_key, str) or not col_key:
                raise ValueError(f"Chave de coluna inválida: {col_key!r}")
            ck = _normalize_col_letter(col_key)

            if not isinstance(spec, dict):
                raise ValueError(
                    f"Coluna {ck!r}: esperado objeto com description, type, required, "
                    f"patterns?, domain?"
                )

            req = spec.get("required")
            if not isinstance(req, bool):
                raise ValueError(f"Coluna {ck!r}: 'required' deve ser booleano")

            desc = spec.get("description")
            if desc is not None and not isinstance(desc, str):
                raise ValueError(f"Coluna {ck!r}: 'description' deve ser string ou omitido")
            if desc:
                descriptions[ck] = desc.strip()

            typ = spec.get("type")
            if typ is not None:
                if not isinstance(typ, str) or not typ.strip():
                    raise ValueError(f"Coluna {ck!r}: 'type' deve ser string não vazia ou omitido")
                column_types[ck] = typ.strip()

            rules[ck] = _patterns_from_column_spec(ck, spec.get("patterns"))

            dom = spec.get("domain")
            if dom is not None:
                if not isinstance(dom, str) or not dom.strip():
                    raise ValueError(
                        f"Coluna {ck!r}: 'domain' deve ser string não vazia ou omitido"
                    )
                domain_rules[ck] = dom.strip()

            if req:
                required_list.append(ck)

        sheet = raw.get("sheetName")
        if sheet is not None and not isinstance(sheet, str):
            raise ValueError("sheetName, se presente, deve ser string")

        return Layout(
            initial_line=initial,
            rules=rules,
            domain_rules=domain_rules,
            required_columns=frozenset(required_list),
            sheet_name=sheet,
            descriptions=descriptions,
            column_types=column_types,
        )
