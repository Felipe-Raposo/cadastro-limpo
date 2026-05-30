from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from sanitiser.layout import SanitiserLayout
from sanitiser.updater import _DEFAULT_TIMEOUT_SEC, update_workbook_from_api


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Atualiza planilha Excel com dados de CPF/CNPJ (APIs em sanitiser.entity) "
            "e endereço por CEP (sanitiser.address), conforme leiaute JSON."
        )
    )
    p.add_argument("workbook", type=Path, help="Caminho do arquivo .xlsx de entrada")
    p.add_argument(
        "--layout",
        "-l",
        type=Path,
        required=True,
        help="JSON de leiaute (initialLine, sanitiser, …)",
    )
    p.add_argument(
        "--output",
        "-o",
        type=Path,
        required=True,
        help="Caminho do arquivo .xlsx de saída",
    )
    p.add_argument(
        "--lines",
        type=int,
        default=None,
        metavar="N",
        help="Processa no máximo N linhas a partir de initialLine no leiaute (padrão: até o fim da planilha).",
    )
    p.add_argument(
        "--http-timeout",
        type=float,
        default=None,
        metavar="SEC",
        help="Timeout por requisição HTTP às APIs (segundos; padrão: 30).",
    )
    cg = p.add_argument_group(
        "cache",
        "Cache SQLite das consultas CPF/CNPJ/CEP (reutiliza respostas; padrão: arquivo versionado em "
        "sanitiser/data/api_cache.sqlite no repositório/pacote).",
    )
    cg.add_argument(
        "--no-cache",
        action="store_true",
        help="Não usa nem grava cache (sempre chama as APIs).",
    )
    cg.add_argument(
        "--cache-db",
        type=Path,
        default=None,
        metavar="PATH",
        help="Caminho do arquivo .sqlite do cache (ignorado se --no-cache).",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        layout = SanitiserLayout.load(args.layout)
        timeout_sec = args.http_timeout
        if timeout_sec is None:
            timeout_sec = _DEFAULT_TIMEOUT_SEC
        if timeout_sec <= 0:
            raise ValueError("--http-timeout deve ser um número positivo")
        update_workbook_from_api(
            args.workbook,
            layout,
            args.output,
            max_lines=args.lines,
            timeout_sec=timeout_sec,
            use_api_cache=not args.no_cache,
            cache_db_path=args.cache_db,
        )
    except (ValueError, OSError) as e:
        print(f"sanitiser: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
