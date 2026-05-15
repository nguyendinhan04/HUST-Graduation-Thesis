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


def get_top100_similar_vectors_tfidf(
	db: Session,
	query_vector: Sequence[float] | Any,
	table_name: str = "jobs",
	vector_column: str = "embedding",
	id_column: str = "id",
	limit: int = 100,
) -> list[dict[str, Any]]:
	"""
	Query the top-k rows with the highest cosine similarity to query_vector.

	This function expects a PostgreSQL pgvector column and uses the cosine
	distance operator <=>. The smaller the distance, the higher the similarity.
	"""

	if limit <= 0:
		raise ValueError("limit must be greater than 0")

	safe_table_name = _validate_identifier(table_name)
	safe_vector_column = _validate_identifier(vector_column)
	safe_id_column = _validate_identifier(id_column)
	pgvector_literal = _to_pgvector_literal(query_vector)

	query = text(
		f"""
		SELECT
			{safe_id_column} AS id,
			1 - ({safe_vector_column} <=> CAST(:query_vector AS vector)) AS similarity
		FROM {safe_table_name}
		WHERE {safe_vector_column} IS NOT NULL
		ORDER BY {safe_vector_column} <=> CAST(:query_vector AS vector) ASC
		LIMIT :limit
		"""
	)

	result = db.execute(query, {"query_vector": pgvector_literal, "limit": limit})
	return [dict(row) for row in result.mappings().all()]
