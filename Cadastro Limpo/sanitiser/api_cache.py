from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, Mapping, Optional, Tuple

_APP_NAME = "Cadastro Limpo"
_APP_SLUG = "cadastro-limpo"
_DB_FILENAME = "api_cache.sqlite"


def default_api_cache_db_path() -> Path:
    """Arquivo embarcado junto ao pacote (`sanitiser/data/api_cache.sqlite`), usado como seed."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        return base / "sanitiser" / "data" / _DB_FILENAME
    return Path(__file__).resolve().parent / "data" / _DB_FILENAME


def app_cache_dir() -> Path:
    """Pasta-padrao de cache do usuario por SO (oculta por convencao do sistema)."""
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
        cache_dir = Path(base) / _APP_NAME
    elif sys.platform == "darwin":
        cache_dir = Path.home() / "Library" / "Caches" / _APP_NAME
    else:
        base = os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache")
        cache_dir = Path(base) / _APP_SLUG
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def user_api_cache_db_path() -> Path:
    """Caminho do cache SQLite na pasta de cache do usuario."""
    return app_cache_dir() / _DB_FILENAME


def resolve_cache_db_path() -> Path:
    """
    Caminho padrao do cache na pasta do usuario, copiando o sqlite embarcado
    (seed) na primeira execucao. Se nao houver seed, o banco e criado vazio.
    """
    target = user_api_cache_db_path()
    if not target.exists():
        seed = default_api_cache_db_path()
        if seed.is_file():
            shutil.copyfile(seed, target)
    return target


def source_id_from(url_template: str, headers: Mapping[str, str]) -> str:
    """Identificador estável da fonte (URL com placeholder + headers), para não misturar APIs."""
    canon = (
        url_template.strip()
        + "\0"
        + json.dumps(dict(headers), sort_keys=True, separators=(",", ":"))
    )
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class ApiCache:
    """Cache SQLite de respostas de API (payload JSON ou mensagem de erro)."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), timeout=10.0)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._auto_commit = True
        self._ensure_schema()

    def close(self) -> None:
        self._conn.close()

    def _ensure_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_cache (
                kind TEXT NOT NULL,
                query_key TEXT NOT NULL,
                source_id TEXT NOT NULL,
                payload_json TEXT,
                error_message TEXT,
                http_status INTEGER,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (kind, query_key, source_id)
            )
            """
        )
        cols = {
            row[1]
            for row in self._conn.execute("PRAGMA table_info(api_cache)").fetchall()
        }
        if "http_status" not in cols:
            self._conn.execute(
                "ALTER TABLE api_cache ADD COLUMN http_status INTEGER"
            )
        self._conn.commit()

    def begin_batch(self) -> None:
        if not self._auto_commit:
            return
        self._conn.execute("BEGIN")
        self._auto_commit = False

    def end_batch(self, *, commit: bool) -> None:
        if self._auto_commit:
            return
        if commit:
            self._conn.commit()
        else:
            self._conn.rollback()
        self._auto_commit = True

    @contextmanager
    def batch(self) -> Iterator[None]:
        self.begin_batch()
        try:
            yield
        except Exception:
            self.end_batch(commit=False)
            raise
        else:
            self.end_batch(commit=True)

    def purge_http_4xx_errors(self) -> None:
        """Remove entradas de erro HTTP 4xx (coluna http_status ou prefixo legado no texto)."""
        self._conn.execute(
            """
            DELETE FROM api_cache
            WHERE (http_status IS NOT NULL AND http_status >= 400 AND http_status <= 499)
               OR error_message LIKE 'HTTP 4__:%'
            """
        )
        # LIKE: _ casa um caractere; casa "HTTP 403:..." até "HTTP 499:...".
        self._conn.commit()

    def delete(self, kind: str, query_key: str, source_id: str) -> None:
        self._conn.execute(
            "DELETE FROM api_cache WHERE kind = ? AND query_key = ? AND source_id = ?",
            (kind, query_key, source_id),
        )
        if self._auto_commit:
            self._conn.commit()

    def get(
        self, kind: str, query_key: str, source_id: str
    ) -> Optional[Tuple[Optional[Dict[str, Any]], Optional[str], Optional[int]]]:
        """
        Retorna None se miss.
        Hit sucesso: (dict_payload, None, http_status).
        Hit erro cacheado: (None, mensagem, http_status).
        http_status pode ser NULL em linhas antigas ou erros não HTTP.
        """
        cur = self._conn.execute(
            "SELECT payload_json, error_message, http_status FROM api_cache "
            "WHERE kind = ? AND query_key = ? AND source_id = ?",
            (kind, query_key, source_id),
        )
        row = cur.fetchone()
        if row is None:
            return None
        payload_json, error_message, http_status = row
        status_i: Optional[int] = (
            int(http_status) if http_status is not None else None
        )
        if payload_json is not None:
            try:
                parsed: Any = json.loads(payload_json)
            except json.JSONDecodeError:
                return None
            if isinstance(parsed, dict):
                return (parsed, None, status_i)
            return None
        if error_message is not None:
            return (None, str(error_message), status_i)
        return None

    def put_success(
        self,
        kind: str,
        query_key: str,
        source_id: str,
        payload: Dict[str, Any],
        *,
        http_status: Optional[int] = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO api_cache
                (kind, query_key, source_id, payload_json, error_message, http_status, updated_at)
            VALUES (?, ?, ?, ?, NULL, ?, ?)
            """,
            (
                kind,
                query_key,
                source_id,
                json.dumps(payload, ensure_ascii=False, default=str),
                http_status,
                _utc_now_iso(),
            ),
        )
        if self._auto_commit:
            self._conn.commit()

    def put_error(
        self,
        kind: str,
        query_key: str,
        source_id: str,
        error_message: str,
        *,
        http_status: Optional[int] = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO api_cache
                (kind, query_key, source_id, payload_json, error_message, http_status, updated_at)
            VALUES (?, ?, ?, NULL, ?, ?, ?)
            """,
            (
                kind,
                query_key,
                source_id,
                error_message,
                http_status,
                _utc_now_iso(),
            ),
        )
        if self._auto_commit:
            self._conn.commit()


__all__ = [
    "ApiCache",
    "app_cache_dir",
    "default_api_cache_db_path",
    "resolve_cache_db_path",
    "source_id_from",
    "user_api_cache_db_path",
]
