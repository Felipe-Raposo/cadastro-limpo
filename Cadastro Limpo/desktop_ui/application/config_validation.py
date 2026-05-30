from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Any, Dict

from validator.layout import Layout
from sanitiser.layout import SanitiserLayout


def parse_json_document(text: str, field_name: str) -> Dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field_name}: JSON inválido ({exc})") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{field_name}: documento deve ser um objeto JSON")
    return payload


def validate_patterns_payload(payload: Dict[str, Any]) -> None:
    patterns = payload.get("patterns")
    if not isinstance(patterns, dict) or not patterns:
        raise ValueError("patterns: a chave 'patterns' deve ser um objeto não vazio")
    for key, regex in patterns.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("patterns: identificador de regex inválido")
        if not isinstance(regex, str):
            raise ValueError(f"patterns.{key}: a regex deve ser uma string")
        try:
            re.compile(regex)
        except re.error as exc:
            raise ValueError(f"patterns.{key}: regex inválida ({exc})") from exc

    domains = payload.get("domains")
    if domains is None:
        return
    if not isinstance(domains, dict):
        raise ValueError("domains: deve ser um objeto")
    for key, values in domains.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("domains: identificador de domínio inválido")
        if not isinstance(values, list):
            raise ValueError(f"domains.{key}: o domínio deve ser uma lista")
        for index, item in enumerate(values):
            if not isinstance(item, str) or not item.strip():
                raise ValueError(f"domains.{key}[{index}]: item de domínio inválido")


def validate_layout_payload(payload: Dict[str, Any]) -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", encoding="utf-8", delete=False) as tmp:
        json.dump(payload, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        tmp_path = Path(tmp.name)
    try:
        Layout.load(tmp_path)
        SanitiserLayout.load(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)
