from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, FrozenSet, Mapping, Optional, Union


def _normalize_col_letter(col: str) -> str:
    c = col.strip().upper()
    if not c:
        raise ValueError(f"Letra de coluna inválida: {col!r}")
    return c


def _optional_bool(value: Any, ctx: str) -> bool:
    if value is None:
        return False
    if not isinstance(value, bool):
        raise ValueError(f"{ctx}, se presente, deve ser boolean (true/false)")
    return value


def _optional_col(value: Any, ctx: str) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    if not isinstance(value, str):
        raise ValueError(f"{ctx}: valor de coluna deve ser string ou null, obteve {type(value).__name__}")
    return _normalize_col_letter(value)


def _parse_headers(raw: Any, ctx: str) -> Dict[str, str]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f"{ctx}.headers deve ser objeto ou omitido")
    headers: Dict[str, str] = {}
    for hk, hv in raw.items():
        if not isinstance(hk, str) or not isinstance(hv, str):
            raise ValueError(f"{ctx}.headers: chaves e valores devem ser strings")
        headers[hk] = hv
    return headers


def _parse_api_mapping(
    block: Any,
    ctx: str,
    placeholder: str,
) -> tuple[str, Dict[str, str], Dict[str, Optional[str]]]:
    if not isinstance(block, dict):
        raise ValueError(f"{ctx} deve ser um objeto")
    api = block.get("api")
    if not isinstance(api, dict):
        raise ValueError(f"{ctx}.api deve ser um objeto")
    url = api.get("url")
    if not isinstance(url, str) or not url.strip():
        raise ValueError(f"{ctx}.api.url deve ser string não vazia")
    url = url.strip()
    if placeholder not in url:
        raise ValueError(f"{ctx}.api.url deve incluir o placeholder {placeholder!r}")
    headers = _parse_headers(api.get("headers"), f"{ctx}.api")
    rtc = block.get("response_to_column")
    if not isinstance(rtc, dict):
        raise ValueError(f"{ctx}.response_to_column deve ser um objeto")
    mapping: Dict[str, Optional[str]] = {}
    for k, v in rtc.items():
        if not isinstance(k, str) or not k.strip():
            raise ValueError(f"{ctx}.response_to_column: chaves devem ser strings não vazias")
        key = k.strip()
        mapping[key] = _optional_col(v, f"{ctx}.response_to_column[{key!r}]")
    return url, headers, mapping


@dataclass(frozen=True)
class AddressBlock:
    cep_column: str
    url_template: str
    headers: Mapping[str, str]
    response_to_column: Mapping[str, Optional[str]]
    capitalise: bool = False


@dataclass(frozen=True)
class SanitiserLayout:
    initial_line: int
    sheet_name: Optional[str]
    cpf_cnpj_column: Optional[str] = None
    cpf_url: Optional[str] = None
    cpf_headers: Mapping[str, str] = field(default_factory=dict)
    cpf_response_to_column: Mapping[str, Optional[str]] = field(default_factory=dict)
    cnpj_url: Optional[str] = None
    cnpj_headers: Mapping[str, str] = field(default_factory=dict)
    cnpj_response_to_column: Mapping[str, Optional[str]] = field(default_factory=dict)
    address: Optional[AddressBlock] = None
    entity_capitalise: bool = False
    text_columns: FrozenSet[str] = field(default_factory=frozenset)

    @staticmethod
    def load(path: Union[Path, str]) -> "SanitiserLayout":
        p = Path(path)
        with p.open(encoding="utf-8") as f:
            raw: Any = json.load(f)

        if not isinstance(raw, dict):
            raise ValueError("Leiaute deve ser um objeto JSON")

        try:
            initial = raw["initialLine"]
        except KeyError as e:
            raise ValueError("Leiaute JSON faltando chave obrigatória: initialLine") from e

        if not isinstance(initial, int) or initial < 1:
            raise ValueError("initialLine deve ser inteiro >= 1")

        sheet = raw.get("sheetName")
        if sheet is not None and not isinstance(sheet, str):
            raise ValueError("sheetName, se presente, deve ser string")

        text_columns: FrozenSet[str] = frozenset()
        cols_raw = raw.get("columns")
        if isinstance(cols_raw, dict):
            text_set: set[str] = set()
            for col_key, spec in cols_raw.items():
                if not isinstance(col_key, str) or not col_key.strip():
                    continue
                if not isinstance(spec, dict):
                    continue
                typ = spec.get("type")
                if not isinstance(typ, str):
                    continue
                if typ.strip().lower() == "text":
                    text_set.add(_normalize_col_letter(col_key))
            text_columns = frozenset(text_set)

        st = raw.get("sanitiser")
        if not isinstance(st, dict):
            raise ValueError("Leiaute deve conter objeto 'sanitiser'")

        cpf_cnpj_column: Optional[str] = None
        cpf_url: Optional[str] = None
        cpf_headers: Dict[str, str] = {}
        cpf_map: Dict[str, Optional[str]] = {}
        cnpj_url: Optional[str] = None
        cnpj_headers: Dict[str, str] = {}
        cnpj_map: Dict[str, Optional[str]] = {}
        entity_capitalise = False

        entity = st.get("entity")
        if entity is not None:
            if not isinstance(entity, dict):
                raise ValueError("sanitiser.entity deve ser um objeto")

            cpf_cnpj_raw = entity.get("cpf_cnpj_column")
            if not isinstance(cpf_cnpj_raw, str) or not cpf_cnpj_raw.strip():
                raise ValueError("sanitiser.entity.cpf_cnpj_column é obrigatório (letra da coluna)")
            cpf_cnpj_column = _normalize_col_letter(cpf_cnpj_raw)

            cpf_url, cpf_headers, cpf_map = _parse_api_mapping(
                entity.get("cpf"), "sanitiser.entity.cpf", "{cpf}"
            )
            cnpj_url, cnpj_headers, cnpj_map = _parse_api_mapping(
                entity.get("cnpj"), "sanitiser.entity.cnpj", "{cnpj}"
            )
            entity_capitalise = _optional_bool(
                entity.get("capitalise"), "sanitiser.entity.capitalise"
            )

        address_block: Optional[AddressBlock] = None
        addr_raw = st.get("address")
        if addr_raw is not None:
            if not isinstance(addr_raw, dict):
                raise ValueError("sanitiser.address, se presente, deve ser um objeto")
            cep_raw = addr_raw.get("cep_column")
            if not isinstance(cep_raw, str) or not cep_raw.strip():
                raise ValueError("sanitiser.address.cep_column é obrigatório quando address existe")
            cep_col = _normalize_col_letter(cep_raw)
            address_capitalise = _optional_bool(
                addr_raw.get("capitalise"), "sanitiser.address.capitalise"
            )
            a_url, a_headers, a_map = _parse_api_mapping(
                {k: v for k, v in addr_raw.items() if k not in ("cep_column", "capitalise")},
                "sanitiser.address",
                "{cep}",
            )
            address_block = AddressBlock(
                cep_column=cep_col,
                url_template=a_url,
                headers=a_headers,
                response_to_column=a_map,
                capitalise=address_capitalise,
            )

        if cpf_cnpj_column is None and address_block is None:
            raise ValueError("Leiaute deve conter 'sanitiser.entity' ou 'sanitiser.address'")

        return SanitiserLayout(
            initial_line=initial,
            sheet_name=sheet.strip() if isinstance(sheet, str) and sheet.strip() else None,
            cpf_cnpj_column=cpf_cnpj_column,
            cpf_url=cpf_url,
            cpf_headers=cpf_headers,
            cpf_response_to_column=cpf_map,
            cnpj_url=cnpj_url,
            cnpj_headers=cnpj_headers,
            cnpj_response_to_column=cnpj_map,
            address=address_block,
            entity_capitalise=entity_capitalise,
            text_columns=text_columns,
        )
