from __future__ import annotations

from datetime import date, datetime
from html import escape
from typing import Any

import streamlit as st

from frontend_app.api_client import ApiError


def nullable_text(value: Any) -> str:
    return "" if value is None else str(value)



def split_skills(raw_value: str) -> list[str]:
    return [skill.strip() for skill in raw_value.split(",") if skill.strip()]



def skills_to_text(skills: list[dict[str, Any]] | None) -> str:
    if not skills:
        return ""
    return ", ".join(skill.get("skill_name", "") for skill in skills if skill)



def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None



def date_to_api(value: date | None) -> str | None:
    return value.isoformat() if value else None



def optional_date_input(
    label: str,
    key_prefix: str,
    value: str | None = None,
) -> date | None:
    parsed_value = parse_iso_date(value)
    enabled = st.checkbox(
        f"Set {label.lower()}",
        value=parsed_value is not None,
        key=f"{key_prefix}_enabled",
    )
    if not enabled:
        return None
    return st.date_input(
        label,
        value=parsed_value or date.today(),
        key=f"{key_prefix}_date",
    )



def clean_payload(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned = {}
    for key, value in payload.items():
        if isinstance(value, str):
            cleaned[key] = value.strip() or None
        else:
            cleaned[key] = value
    return cleaned



def show_api_error(message: str, exc: ApiError) -> None:
    st.error(f"{message}: {exc}")



def initials(value: str | None, fallback: str = "IN") -> str:
    words = [word for word in nullable_text(value).replace(",", " ").split() if word]
    if not words:
        return fallback
    return "".join(word[0].upper() for word in words[:2])



def format_month_year(value: str | None) -> str:
    parsed = parse_iso_date(value)
    if not parsed:
        return ""
    return parsed.strftime("%b %Y")



def format_date_range(start: str | None, end: str | None) -> str:
    start_label = format_month_year(start)
    end_label = format_month_year(end) or "Present"
    if start_label:
        return f"{start_label} - {end_label}"
    return end_label



def summarize_skills(skills: list[dict[str, Any]] | None, visible_count: int = 2) -> str:
    names = [skill.get("skill_name", "") for skill in skills or [] if skill.get("skill_name")]
    if not names:
        return ""
    visible = ", ".join(names[:visible_count])
    hidden_count = len(names) - visible_count
    if hidden_count > 0:
        return f"{visible} and +{hidden_count} skills"
    return visible



def html_or_empty(value: Any, fallback: str = "") -> str:
    return escape(nullable_text(value) or fallback)

