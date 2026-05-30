from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple


def _group_key(group: Dict[str, Any]) -> Tuple[str, str, str, str]:
    return (
        str(group.get("column") or ""),
        str(group.get("message") or ""),
        str(group.get("pattern") or ""),
        str(group.get("domain") or ""),
    )


def _groups_by_key(groups: Iterable[Dict[str, Any]]) -> Dict[Tuple[str, str, str, str], Dict[str, Any]]:
    mapped: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
    for group in groups:
        key = _group_key(group)
        existing = mapped.get(key)
        if existing is None:
            mapped[key] = dict(group)
            continue
        existing_count = int(existing.get("count", 0))
        incoming_count = int(group.get("count", 0))
        existing["count"] = existing_count + incoming_count
        existing_errors = existing.get("errors", [])
        incoming_errors = group.get("errors", [])
        if isinstance(existing_errors, list) and isinstance(incoming_errors, list):
            existing["errors"] = [*existing_errors, *incoming_errors]
    return mapped


def compare_char_logs(input_payload: Dict[str, Any], output_payload: Dict[str, Any]) -> Dict[str, Any]:
    input_groups = _groups_by_key(input_payload.get("groups", []))
    output_groups = _groups_by_key(output_payload.get("groups", []))

    resolved_groups: List[Dict[str, Any]] = []
    new_groups: List[Dict[str, Any]] = []
    changed_groups: List[Dict[str, Any]] = []
    unchanged_groups = 0

    all_keys = sorted(set(input_groups.keys()) | set(output_groups.keys()))
    for key in all_keys:
        in_group = input_groups.get(key)
        out_group = output_groups.get(key)
        in_count = int(in_group.get("count", 0)) if in_group else 0
        out_count = int(out_group.get("count", 0)) if out_group else 0
        if in_count == out_count and in_group and out_group:
            unchanged_groups += 1
            continue

        row = {
            "column": key[0],
            "message": key[1],
            "pattern": key[2] or None,
            "domain": key[3] or None,
            "input_count": in_count,
            "output_count": out_count,
            "delta": out_count - in_count,
            "input_examples": (in_group or {}).get("errors", [])[:5],
            "output_examples": (out_group or {}).get("errors", [])[:5],
        }
        if in_group and not out_group:
            resolved_groups.append(row)
        elif out_group and not in_group:
            new_groups.append(row)
        else:
            changed_groups.append(row)

    input_total = int(input_payload.get("count", 0))
    output_total = int(output_payload.get("count", 0))
    delta_total = output_total - input_total
    improvement_percent = 0.0
    if input_total > 0:
        improvement_percent = ((input_total - output_total) / input_total) * 100.0

    return {
        "input_total": input_total,
        "output_total": output_total,
        "delta_total": delta_total,
        "improvement_percent": round(improvement_percent, 2),
        "resolved_groups": resolved_groups,
        "new_groups": new_groups,
        "changed_groups": changed_groups,
        "unchanged_groups": unchanged_groups,
    }


def render_diff_summary_text(summary: Dict[str, Any]) -> str:
    lines = [
        "Resumo da comparação de logs",
        f"- Total de erros (entrada): {summary.get('input_total', 0)}",
        f"- Total de erros (saída): {summary.get('output_total', 0)}",
        f"- Delta total: {summary.get('delta_total', 0)}",
        f"- Melhora percentual: {summary.get('improvement_percent', 0.0)}%",
        f"- Grupos resolvidos: {len(summary.get('resolved_groups', []))}",
        f"- Grupos novos: {len(summary.get('new_groups', []))}",
        f"- Grupos alterados: {len(summary.get('changed_groups', []))}",
        f"- Grupos inalterados: {summary.get('unchanged_groups', 0)}",
    ]

    def add_block(title: str, items: List[Dict[str, Any]]) -> None:
        if not items:
            return
        lines.append("")
        lines.append(title)
        for item in items[:10]:
            lines.append(
                "- {column} | {message} | in={input_count} out={output_count} delta={delta}".format(
                    **item
                )
            )

    add_block("Grupos resolvidos:", summary.get("resolved_groups", []))
    add_block("Grupos novos:", summary.get("new_groups", []))
    add_block("Grupos alterados:", summary.get("changed_groups", []))
    return "\n".join(lines) + "\n"
