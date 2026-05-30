from __future__ import annotations

import shutil
import sys
from pathlib import Path

from sanitiser.api_cache import app_cache_dir

_PATTERNS_FILENAME = "patterns.json"


def default_patterns_seed_path() -> Path:
    """patterns.json embarcado (semente), usado para popular a pasta do usuário."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        return base / _PATTERNS_FILENAME
    return Path(__file__).resolve().parents[2] / _PATTERNS_FILENAME


def user_patterns_path() -> Path:
    """patterns.json na pasta de cache do usuário (mesmo local do cache SQLite)."""
    return app_cache_dir() / _PATTERNS_FILENAME


def resolve_patterns_path() -> Path:
    """
    Caminho padrão do patterns.json na pasta do usuário, copiando o arquivo
    embarcado (semente) na primeira execução. Se não houver semente, o caminho
    é retornado mesmo sem o arquivo existir.
    """
    target = user_patterns_path()
    if not target.exists():
        seed = default_patterns_seed_path()
        if seed.is_file():
            shutil.copyfile(seed, target)
    return target


__all__ = [
    "default_patterns_seed_path",
    "resolve_patterns_path",
    "user_patterns_path",
]
