from __future__ import annotations

import re
from typing import Any, Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session


_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$")


def _validate_identifier(name: str) -> str:
	if not _IDENTIFIER_PATTERN.match(name):
		raise ValueError(f"Invalid SQL identifier: {name}")
	return name


def _to_pgvector_literal(vector: Sequence[float] | Any) -> str:
	if hasattr(vector, "tolist"):
		vector = vector.tolist()

	if not isinstance(vector, (list, tuple)):
		raise TypeError("query_vector must be a list, tuple, or array-like object")

	return "[" + ",".join(str(float(value)) for value in vector) + "]"


