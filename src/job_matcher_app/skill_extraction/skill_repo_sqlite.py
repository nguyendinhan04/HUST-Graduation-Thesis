from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import List, Optional, Sequence

from .skill_repo_base import SkillRecord


class SqliteSkillRepository:
    def __init__(self, db_path: str) -> None:
        self._db_path = Path(db_path)

    @property
    def db_path(self) -> Path:
        return self._db_path

    def init_schema(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self._db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS skill_synonyms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    skill_id INTEGER NOT NULL,
                    synonym TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    UNIQUE(skill_id, synonym),
                    FOREIGN KEY(skill_id) REFERENCES skills(id) ON DELETE CASCADE
                );
                """
            )
            conn.commit()

    def has_any_skill(self) -> bool:
        if not self._db_path.exists():
            return False

        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute("SELECT 1 FROM skills LIMIT 1;").fetchone()
            return row is not None

    def list_skills(self) -> List[SkillRecord]:
        if not self._db_path.exists():
            return []

        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT s.name AS skill_name, ss.synonym AS synonym
                FROM skills s
                LEFT JOIN skill_synonyms ss ON ss.skill_id = s.id
                ORDER BY s.name ASC;
                """
            ).fetchall()

        skill_to_synonyms: dict[str, list[str]] = {}
        for row in rows:
            skill_name = row["skill_name"]
            skill_to_synonyms.setdefault(skill_name, [])

            synonym = row["synonym"]
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

        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self._db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON;")
            cur = conn.execute(
                "INSERT OR IGNORE INTO skills(name) VALUES (?);", (normalized_name,)
            )
            row = conn.execute(
                "SELECT id FROM skills WHERE name = ?;", (normalized_name,)
            ).fetchone()
            if row is None:
                raise RuntimeError("Failed to read back skill after upsert")

            skill_id = int(row[0])
            for synonym in normalized_synonyms:
                conn.execute(
                    "INSERT OR IGNORE INTO skill_synonyms(skill_id, synonym) VALUES (?, ?);",
                    (skill_id, synonym),
                )

            conn.commit()

        created = cur.rowcount == 1
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
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        with csv_file.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if name_column not in (reader.fieldnames or []):
                raise ValueError(
                    f"CSV missing required column '{name_column}'. Columns: {reader.fieldnames}"
                )

            with sqlite3.connect(self._db_path) as conn:
                conn.execute("PRAGMA foreign_keys = ON;")
                for idx, row in enumerate(reader):
                    if limit is not None and idx >= limit:
                        break

                    name = (row.get(name_column) or "").strip()
                    if not name:
                        continue

                    cur = conn.execute(
                        "INSERT OR IGNORE INTO skills(name) VALUES (?);", (name,)
                    )
                    if cur.rowcount == 1:
                        inserted += 1

                conn.commit()

        return inserted
