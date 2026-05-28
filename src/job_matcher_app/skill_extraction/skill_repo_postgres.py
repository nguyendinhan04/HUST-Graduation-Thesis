from __future__ import annotations

import csv
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, List, Optional, Sequence

try:
    import psycopg2
    from psycopg2 import sql
except ImportError:  # pragma: no cover - exercised only when dependency is absent
    psycopg2 = None  # type: ignore[assignment]
    sql = None  # type: ignore[assignment]

from .skill_repo_base import SkillRecord


class PostgresSkillRepository:
    def __init__(
        self,
        dsn: str | None = None,
        *,
        host: str | None = None,
        port: int | str | None = None,
        database: str | None = None,
        user: str | None = None,
        password: str | None = None,
        schema: str = "public",
    ) -> None:
        self._require_driver()

        self._dsn = _normalize_dsn(dsn)
        self._connect_kwargs = {
            key: value
            for key, value in {
                "host": host,
                "port": port,
                "dbname": database,
                "user": user,
                "password": password,
            }.items()
            if value is not None
        }
        self._schema = schema.strip() if schema else "public"
        if not self._schema:
            raise ValueError("PostgreSQL schema must not be empty")

    @property
    def schema(self) -> str:
        return self._schema

    @property
    def dsn(self) -> str | None:
        return self._dsn

    @property
    def connection_label(self) -> str:
        if self._dsn:
            return _redact_dsn(self._dsn)

        host = self._connect_kwargs.get("host", "<libpq-default>")
        port = self._connect_kwargs.get("port", "<libpq-default>")
        dbname = self._connect_kwargs.get("dbname", "<libpq-default>")
        user = self._connect_kwargs.get("user", "<libpq-default>")
        return f"postgresql://{user}@{host}:{port}/{dbname}?schema={self._schema}"

    def init_schema(self) -> None:
        with self._cursor() as cur:
            cur.execute(
                sql.SQL("CREATE SCHEMA IF NOT EXISTS {};").format(
                    sql.Identifier(self._schema)
                )
            )
            cur.execute(
                sql.SQL(
                    """
                    CREATE TABLE IF NOT EXISTS {} (
                        id BIGSERIAL PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    );
                    """
                ).format(self._table("skills"))
            )
            cur.execute(
                sql.SQL(
                    """
                    CREATE TABLE IF NOT EXISTS {} (
                        id BIGSERIAL PRIMARY KEY,
                        skill_id BIGINT NOT NULL,
                        synonym TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                        UNIQUE(skill_id, synonym),
                        FOREIGN KEY(skill_id) REFERENCES {}(id) ON DELETE CASCADE
                    );
                    """
                ).format(self._table("skill_synonyms"), self._table("skills"))
            )

    def has_any_skill(self) -> bool:
        try:
            with self._cursor() as cur:
                cur.execute(
                    sql.SQL("SELECT 1 FROM {} LIMIT 1;").format(
                        self._table("skills")
                    )
                )
                return cur.fetchone() is not None
        except (
            psycopg2.errors.InvalidSchemaName,
            psycopg2.errors.UndefinedTable,
        ):
            return False

    def list_skills(self) -> List[SkillRecord]:
        try:
            with self._cursor() as cur:
                cur.execute(
                    sql.SQL(
                        """
                        SELECT s.name AS skill_name, ss.synonym AS synonym
                        FROM {} s
                        LEFT JOIN {} ss ON ss.skill_id = s.id
                        ORDER BY s.name ASC, ss.synonym ASC;
                        """
                    ).format(self._table("skills"), self._table("skill_synonyms"))
                )
                rows = cur.fetchall()
        except (
            psycopg2.errors.InvalidSchemaName,
            psycopg2.errors.UndefinedTable,
        ):
            return []

        skill_to_synonyms: dict[str, list[str]] = {}
        for skill_name, synonym in rows:
            skill_to_synonyms.setdefault(skill_name, [])
            if synonym:
                skill_to_synonyms[skill_name].append(synonym)

        return [
            SkillRecord(name=name, synonyms=synonyms)
            for name, synonyms in skill_to_synonyms.items()
        ]

    def upsert_skill(self, name: str, synonyms: Sequence[str] | None = None) -> bool:
        normalized_name = (name or "").strip()
        if not normalized_name:
            raise ValueError("Skill name must not be empty")

        synonyms = synonyms or []
        normalized_synonyms = [s.strip() for s in synonyms if (s or "").strip()]
        normalized_synonyms = [
            s for s in normalized_synonyms if s.casefold() != normalized_name.casefold()
        ]

        with self._cursor() as cur:
            cur.execute(
                sql.SQL(
                    """
                    INSERT INTO {}(name)
                    VALUES (%s)
                    ON CONFLICT (name) DO NOTHING
                    RETURNING id;
                    """
                ).format(self._table("skills")),
                (normalized_name,),
            )
            row = cur.fetchone()
            created = row is not None

            if row is None:
                cur.execute(
                    sql.SQL("SELECT id FROM {} WHERE name = %s;").format(
                        self._table("skills")
                    ),
                    (normalized_name,),
                )
                row = cur.fetchone()

            if row is None:
                raise RuntimeError("Failed to read back skill after upsert")

            skill_id = int(row[0])
            for synonym in normalized_synonyms:
                cur.execute(
                    sql.SQL(
                        """
                        INSERT INTO {}(skill_id, synonym)
                        VALUES (%s, %s)
                        ON CONFLICT (skill_id, synonym) DO NOTHING;
                        """
                    ).format(self._table("skill_synonyms")),
                    (skill_id, synonym),
                )

        return created

    def seed_from_csv(
        self,
        csv_path: str,
        name_column: str = "skill_name",
        limit: Optional[int] = None,
    ) -> int:
        """Seed skills table from a CSV file (one skill per row).

        Intended for local/dev only.
        """

        csv_file = Path(csv_path)
        if not csv_file.exists():
            raise FileNotFoundError(str(csv_file))

        inserted = 0
        with csv_file.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if name_column not in (reader.fieldnames or []):
                raise ValueError(
                    f"CSV missing required column '{name_column}'. Columns: {reader.fieldnames}"
                )

            with self._cursor() as cur:
                insert_sql = sql.SQL(
                    """
                    INSERT INTO {}(name)
                    VALUES (%s)
                    ON CONFLICT (name) DO NOTHING;
                    """
                ).format(self._table("skills"))

                for idx, row in enumerate(reader):
                    if limit is not None and idx >= limit:
                        break

                    name = (row.get(name_column) or "").strip()
                    if not name:
                        continue

                    cur.execute(insert_sql, (name,))
                    if cur.rowcount == 1:
                        inserted += 1

        return inserted

    @contextmanager
    def _cursor(self) -> Iterator[Any]:
        conn = self._connect()
        try:
            with conn:
                with conn.cursor() as cur:
                    yield cur
        finally:
            conn.close()

    def _connect(self) -> Any:
        self._require_driver()
        if self._dsn:
            return psycopg2.connect(self._dsn)
        return psycopg2.connect(**self._connect_kwargs)

    def _table(self, name: str) -> Any:
        return sql.SQL("{}.{}").format(sql.Identifier(self._schema), sql.Identifier(name))

    @staticmethod
    def _require_driver() -> None:
        if psycopg2 is None or sql is None:
            raise ImportError(
                "PostgresSkillRepository requires 'psycopg2-binary'. "
                "Install it with: pip install psycopg2-binary"
            )


def _normalize_dsn(dsn: str | None) -> str | None:
    if not dsn:
        return None

    normalized = dsn.strip()
    for prefix in ("postgresql+psycopg2://", "postgresql+psycopg://"):
        if normalized.startswith(prefix):
            return "postgresql://" + normalized[len(prefix) :]
    return normalized


def _redact_dsn(dsn: str) -> str:
    if "password=" in dsn:
        return re.sub(r"password=[^\s]+", "password=***", dsn)

    if "@" not in dsn or "://" not in dsn:
        return dsn

    scheme, rest = dsn.split("://", 1)
    credentials, host_part = rest.split("@", 1)
    if ":" not in credentials:
        return dsn

    user, _password = credentials.split(":", 1)
    return f"{scheme}://{user}:***@{host_part}"
