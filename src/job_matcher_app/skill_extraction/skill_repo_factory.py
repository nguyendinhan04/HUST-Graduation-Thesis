from __future__ import annotations

from typing import Optional

from .skill_repo_base import SkillRepository
from .skill_repo_sqlite import SqliteSkillRepository


def create_skill_repository(
    *,
    backend: str,
    sqlite_db_path: str | None = None,
    postgres_dsn: str | None = None,
    postgres_host: str | None = None,
    postgres_port: int | str | None = None,
    postgres_database: str | None = None,
    postgres_user: str | None = None,
    postgres_password: str | None = None,
    postgres_schema: str = "public",
) -> SkillRepository:
    normalized = (backend or "sqlite").strip().lower()

    if normalized in {"sqlite", "sqlite3"}:
        return SqliteSkillRepository(sqlite_db_path)

    if normalized in {"postgres", "postgresql", "pg"}:
        from .skill_repo_postgres import PostgresSkillRepository

        return PostgresSkillRepository(
            dsn=postgres_dsn,
            host=postgres_host,
            port=postgres_port,
            database=postgres_database,
            user=postgres_user,
            password=postgres_password,
            schema=postgres_schema,
        )

    raise ValueError(
        f"Unsupported SKILLS_DB_BACKEND '{backend}'. Use 'sqlite' or 'postgres'."
    )


def describe_skill_repository(repo: SkillRepository) -> str:
    db_path = getattr(repo, "db_path", None)
    if db_path is not None:
        return str(db_path)

    connection_label = getattr(repo, "connection_label", None)
    if connection_label is not None:
        return str(connection_label)

    return repo.__class__.__name__


def parse_optional_port(port: Optional[str]) -> int | None:
    if port is None:
        return None
    try:
        return int(port)
    except ValueError as exc:
        raise ValueError(f"Invalid PostgreSQL port: {port}") from exc
