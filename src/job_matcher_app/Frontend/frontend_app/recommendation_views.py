from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from html import escape
from typing import Any

import streamlit as st

from frontend_app.api_client import ApiError, get_recommended_jobs
from frontend_app.formatting import html_or_empty, initials, show_api_error
from frontend_app.loading import form_loading
from frontend_app.state import navigate_to_job_detail


def _format_salary(job: dict[str, Any]) -> str:
    salary_min = _to_decimal(job.get("salary_min"))
    salary_max = _to_decimal(job.get("salary_max"))
    currency = (job.get("salary_currency") or "").upper()
    if salary_min is None and salary_max is None:
        return "Thoả thuận"

    divisor = (
        Decimal("1000000")
        if currency in {"VND", "VNĐ"} and max(salary_min or 0, salary_max or 0) >= Decimal("1000000")
        else Decimal("1")
    )
    suffix = " triệu" if currency in {"VND", "VNĐ"} else f" {currency}".rstrip()
    if salary_min is not None and salary_max is not None:
        return f"{_compact_decimal(salary_min / divisor)} - {_compact_decimal(salary_max / divisor)}{suffix}"
    if salary_min is not None:
        return f"Từ {_compact_decimal(salary_min / divisor)}{suffix}"
    return f"Đến {_compact_decimal(salary_max / divisor)}{suffix}"


def _to_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _compact_decimal(value: Decimal) -> str:
    normalized = value.quantize(Decimal("0.1")) if value != value.to_integral() else value
    return f"{normalized.normalize():f}"


def _posted_label(value: str | None) -> str:
    if not value:
        return "Đăng gần đây"
    try:
        created_at = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return "Đăng gần đây"
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    days = max((datetime.now(timezone.utc) - created_at.astimezone(timezone.utc)).days, 0)
    if days == 0:
        return "Đăng hôm nay"
    if days < 7:
        return f"Đăng {days} ngày trước"
    weeks = max(days // 7, 1)
    return f"Đăng {weeks} tuần trước"


def _job_logo_markup(job: dict[str, Any]) -> str:
    logo_url = (job.get("company_logo_url") or "").strip()
    company_name = job.get("company_name") or "Company"
    if logo_url:
        return (
            f'<img class="job-card-logo" src="{escape(logo_url)}" '
            f'alt="{html_or_empty(company_name)}">'
        )
    return f'<div class="job-card-logo-placeholder">{escape(initials(company_name, "CO"))}</div>'


def _job_tags(job: dict[str, Any]) -> str:
    tags = []
    location = job.get("location") or job.get("location_type")
    if location:
        tags.append(str(location))
    experience_required = job.get("experience_required")
    if experience_required is not None:
        tags.append(f"{experience_required} năm")
    return "".join(f'<span class="job-tag">{html_or_empty(tag)}</span>' for tag in tags)


def _job_meta(job: dict[str, Any]) -> str:
    bits = []
    experience_required = job.get("experience_required")
    if experience_required is not None:
        bits.append(f"{experience_required} năm kinh nghiệm chuyên môn")
    if job.get("employment_type"):
        bits.append(str(job["employment_type"]))
    if job.get("working_time"):
        bits.append(str(job["working_time"]))
    return " | ".join(bits)


def render_recommendations_page() -> None:
    st.markdown('<div class="recommendation-title">Recommended jobs</div>', unsafe_allow_html=True)
    header_col, action_col = st.columns([8, 1.6], gap="small")
    header_col.markdown(
        '<div class="recommendation-subtitle">Jobs matched from your profile, skills, experience, and education.</div>',
        unsafe_allow_html=True,
    )
    if action_col.button("Refresh", key="refresh_recommendations", use_container_width=True):
        st.session_state.pop("recommended_jobs", None)

    if "recommended_jobs" not in st.session_state:
        try:
            with form_loading("Loading recommendations..."):
                st.session_state["recommended_jobs"] = get_recommended_jobs()
        except ApiError as exc:
            show_api_error("Could not load recommendations", exc)
            return

    jobs = st.session_state.get("recommended_jobs") or []
    if not jobs:
        st.markdown('<div class="empty-state">No recommended jobs yet.</div>', unsafe_allow_html=True)
        return

    for index, job in enumerate(jobs):
        job_id = job.get("id")
        st.markdown(
            f"""
            <div class="job-card">
                <div class="job-card-media">{_job_logo_markup(job)}</div>
                <div class="job-card-body">
                    <div class="job-card-main">
                        <div>
                            <div class="job-card-title">{html_or_empty(job.get("title"), "Untitled job")} <span class="verified-dot">✓</span></div>
                            <div class="job-card-company">{html_or_empty(job.get("company_name"), "No company yet")}</div>
                            <div class="job-tag-row">{_job_tags(job)}</div>
                        </div>
                        <div class="job-card-salary">{html_or_empty(_format_salary(job))}</div>
                    </div>
                    <div class="job-card-footer">
                        <div class="job-card-meta">{html_or_empty(_job_meta(job))}</div>
                        <div class="job-card-posted">{html_or_empty(_posted_label(job.get("created_at")))}</div>
                        <div class="job-save-button">♡</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        action_col, _ = st.columns([1.8, 6], gap="small")
        if action_col.button(
            "Xem chi tiết",
            key=f"job_detail_open_{job_id or index}",
            type="primary",
            use_container_width=True,
            disabled=job_id is None,
        ):
            navigate_to_job_detail(int(job_id))
            st.rerun()
