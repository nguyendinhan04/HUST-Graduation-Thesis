from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol, Sequence


@dataclass(frozen=True)
class SkillRecord:
    name: str
    synonyms: List[str]


class SkillRepository(Protocol):
    def init_schema(self) -> None:
        ...

    def has_any_skill(self) -> bool:
        ...

    def list_skills(self) -> List[SkillRecord]:
        ...

    def upsert_skill(self, name: str, synonyms: Sequence[str] | None = None) -> bool:
        ...

    def seed_from_csv(
        self,
        csv_path: str,
        name_column: str = "skill_name",
        limit: Optional[int] = None,
    ) -> int:
        ...
