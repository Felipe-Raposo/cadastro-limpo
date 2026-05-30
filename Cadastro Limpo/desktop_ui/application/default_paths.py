from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

from sanitiser.api_cache import app_cache_dir

_PATTERNS_FILENAME = "patterns.json"
_RUNS_DIRNAME = "runs"
_TEMP_DIRNAME = "Cadastro Limpo"


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


def runs_base_dir() -> Path:
    """Pasta dos artefatos de execução na área temporária do usuário.

    Fica fora do diretório dos executáveis para não poluir a instalação e por
    ser descartável: o conteúdo é limpo ao abrir e ao fechar o aplicativo.
    """
    runs_dir = Path(tempfile.gettempdir()) / _TEMP_DIRNAME / _RUNS_DIRNAME
    runs_dir.mkdir(parents=True, exist_ok=True)
    return runs_dir


def clear_runs_dir() -> None:
    """Remove todo o conteúdo da pasta de runs temporária, recriando-a vazia."""
    runs_dir = Path(tempfile.gettempdir()) / _TEMP_DIRNAME / _RUNS_DIRNAME
    shutil.rmtree(runs_dir, ignore_errors=True)
    runs_dir.mkdir(parents=True, exist_ok=True)


__all__ = [
    "clear_runs_dir",
    "default_patterns_seed_path",
    "resolve_patterns_path",
    "runs_base_dir",
    "user_patterns_path",
]
