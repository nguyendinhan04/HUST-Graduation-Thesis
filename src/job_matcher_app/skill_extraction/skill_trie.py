from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Iterable, List, Sequence

from flashtext import KeywordProcessor


_EXTRA_WORD_CHARS = set(
    "àáảãạăằắẳẵặâầấẩẫậ"
    "èéẻẽẹêềếểễệ"
    "ìíỉĩị"
    "òóỏõọôồốổỗộơờớởỡợ"
    "ùúủũụưừứửữự"
    "ỳýỷỹỵ"
    "đ"
    "ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬ"
    "ÈÉẺẼẸÊỀẾỂỄỆ"
    "ÌÍỈĨỊ"
    "ÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢ"
    "ÙÚỦŨỤƯỪỨỬỮỰ"
    "ỲÝỶỸỴ"
    "Đ"
    "+#"
)


@dataclass(frozen=True)
class SkillMatch:
    name: str
    start: int
    end: int


class SkillTrie:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._keyword_processor = KeywordProcessor(case_sensitive=False)
        self._keyword_processor.non_word_boundaries.update(_EXTRA_WORD_CHARS)

        self._canonical_skills: set[str] = set()
        self._version = 0

    @property
    def version(self) -> int:
        return self._version

    def add_skill(self, name: str, synonyms: Iterable[str] | None = None) -> None:
        normalized_name = _normalize(name)
        if not normalized_name:
            return

        synonyms = synonyms or []
        normalized_synonyms = [_normalize(s) for s in synonyms]
        normalized_synonyms = [
            s
            for s in normalized_synonyms
            if s and s.casefold() != normalized_name.casefold()
        ]

        with self._lock:
            self._keyword_processor.add_keyword(normalized_name, normalized_name)
            for synonym in normalized_synonyms:
                self._keyword_processor.add_keyword(synonym, normalized_name)

            self._canonical_skills.add(normalized_name)
            self._version += 1

    def add_many(self, skills: Sequence[tuple[str, Sequence[str]]]) -> None:
        for name, synonyms in skills:
            self.add_skill(name, synonyms)

    def extract(self, text: str) -> List[str]:
        if not text:
            return []

        with self._lock:
            found = self._keyword_processor.extract_keywords(text)

        # keep unique, preserve order
        seen: set[str] = set()
        results: list[str] = []
        for skill in found:
            if skill in seen:
                continue
            seen.add(skill)
            results.append(skill)
        return results

    def extract_with_spans(self, text: str) -> List[SkillMatch]:
        if not text:
            return []

        with self._lock:
            found = self._keyword_processor.extract_keywords(text, span_info=True)

        return [SkillMatch(name=name, start=start, end=end) for name, start, end in found]

    def skill_count(self) -> int:
        with self._lock:
            return len(self._canonical_skills)

    def keyword_count(self) -> int:
        with self._lock:
            return len(self._keyword_processor)


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    return value.strip()
