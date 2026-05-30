from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, FrozenSet, Pattern, Union


@dataclass(frozen=True)
class CompiledRules:
    """Regras carregadas de JSON no formato ``patterns.example.json``."""

    regexes: Dict[str, Pattern[str]]
    domains: Dict[str, FrozenSet[str]]


def load_patterns(path: Union[Path, str]) -> CompiledRules:
    """Carrega ``patterns`` (regex compiladas) e ``domains`` (conjuntos de valores).

    O arquivo JSON deve ser um objeto com:
    - ``patterns``: objeto id -> string regex (ex.: ``ER1``, ``ER2``)
    - ``domains`` (opcional): objeto id -> lista de strings permitidas (ex.: ``D1``)
    """
    raw = _read_json(path)
    if not isinstance(raw, dict):
        raise ValueError(
            "JSON de padrões deve ser objeto com chave 'patterns' e opcionalmente 'domains'"
        )
    if "patterns" not in raw:
        raise ValueError("JSON de padrões deve conter a chave 'patterns'")

    patterns_obj = raw["patterns"]
    if not isinstance(patterns_obj, dict) or not patterns_obj:
        raise ValueError("'patterns' deve ser um objeto não vazio")

    compiled_regex: Dict[str, Pattern[str]] = {}
    for name, pat in patterns_obj.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Chave de padrão inválida: {name!r}")
        if not isinstance(pat, str):
            raise ValueError(
                f"Padrão para '{name}' deve ser string, obteve {type(pat).__name__}"
            )
        key = name.strip()
        try:
            compiled_regex[key] = re.compile(pat)
        except re.error as e:
            raise ValueError(f"Regex inválida em '{key}': {e}") from e

    domains: Dict[str, FrozenSet[str]] = {}
    if "domains" in raw and raw["domains"] is not None:
        dom_raw = raw["domains"]
        if not isinstance(dom_raw, dict):
            raise ValueError("'domains', se presente, deve ser um objeto")
        for dname, dlist in dom_raw.items():
            if not isinstance(dname, str) or not dname.strip():
                raise ValueError(f"Chave de domínio inválida: {dname!r}")
            if not isinstance(dlist, list):
                raise ValueError(
                    f"Domínio '{dname}': valor deve ser lista, obteve {type(dlist).__name__}"
                )
            vals: list[str] = []
            for i, v in enumerate(dlist):
                if not isinstance(v, str):
                    raise ValueError(
                        f"Domínio '{dname}' item {i}: esperado string, obteve {type(v).__name__}"
                    )
                s = v.strip()
                if not s:
                    raise ValueError(f"Domínio '{dname}' item {i}: string vazia não permitida")
                vals.append(s)
            domains[dname.strip()] = frozenset(vals)

    return CompiledRules(regexes=compiled_regex, domains=domains)


def _read_json(path: Union[Path, str]) -> Any:
    p = Path(path)
    with p.open(encoding="utf-8") as f:
        return json.load(f)
