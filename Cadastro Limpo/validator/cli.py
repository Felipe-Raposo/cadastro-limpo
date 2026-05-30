from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from validator.layout import Layout
from validator.patterns import load_patterns
from validator.validator import (
    grouped_errors_payload,
    validate_workbook,
    write_error_cell_highlights,
)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Valida planilha Excel com regex definidas em JSON."
    )
    p.add_argument("workbook", type=Path, help="Caminho do arquivo .xlsx")
    p.add_argument(
        "--patterns",
        "-p",
        type=Path,
        required=True,
        help="JSON: objeto com 'patterns' (ids ER -> regex) e opcionalmente 'domains' (ids D -> listas)",
    )
    p.add_argument(
        "--layout",
        "-l",
        type=Path,
        required=True,
        help="JSON: initialLine, columns.{A:{description?,type?,required,patterns?}}, sheetName?",
    )
    p.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Se informado, grava JSON (count, groups por column/message); senão imprime em stdout",
    )
    p.add_argument(
        "--highlight-errors",
        "-H",
        action="store_true",
        help="Grava cópia do Excel com células inválidas destacadas em vermelho (use com --highlight-workbook)",
    )
    p.add_argument(
        "--highlight-workbook",
        type=Path,
        default=None,
        help="Caminho do .xlsx de saída quando --highlight-errors é usado",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.highlight_errors != (args.highlight_workbook is not None):
        parser.error(
            "Use --highlight-errors e --highlight-workbook juntos "
            "(caminho do .xlsx de saída com células inválidas destacadas)."
        )

    patterns = load_patterns(args.patterns)
    layout = Layout.load(args.layout)
    errors = validate_workbook(args.workbook, patterns, layout)
    payload = grouped_errors_payload(errors)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
    else:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")

    if args.highlight_errors:
        write_error_cell_highlights(args.workbook, layout, errors, args.highlight_workbook)

    return 1 if payload["count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
