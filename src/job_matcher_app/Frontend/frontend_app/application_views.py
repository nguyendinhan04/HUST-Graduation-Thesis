from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any

import streamlit as st

from frontend_app.api_client import ApiError, get_my_applications
from frontend_app.formatting import html_or_empty, initials, show_api_error
from frontend_app.loading import form_loading
from frontend_app.recommendation_views import _format_salary, _posted_label
from frontend_app.state import navigate_to_job_detail


def _load_my_applications() -> list[dict[str, Any]] | None:
    if "my_applications" not in st.session_state:
        try:
            with form_loading("Loading applications..."):
                st.session_state["my_applications"] = get_my_applications()
        except ApiError as exc:
            show_api_error("Could not load applications", exc)
            return None
    return st.session_state.get("my_applications") or []


def _format_datetime(value: str | None) -> str:
    if not value:
        return "Not set"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    return parsed.strftime("%d/%m/%Y")


def _status_label(status: Any) -> str:
    value = str(status or "pending").strip().lower()
    return value or "pending"


def _status_class(status: Any) -> str:
    return "employee-application-status-" + "".join(
        char for char in _status_label(status) if char.isalnum()
    )


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
    if job.get("employment_type"):
        bits.append(str(job["employment_type"]))
    if job.get("working_time"):
        bits.append(str(job["working_time"]))
    if job.get("deadline"):
        bits.append(f"Deadline: {_format_datetime(job.get('deadline'))}")
    return " | ".join(bits) or "No job metadata yet"


def _open_job_detail(job_id: int) -> None:
    navigate_to_job_detail(job_id, "applications")


def _render_application_card(application: dict[str, Any]) -> None:
    job = application.get("job") or {}
    job_id = job.get("job_id") or job.get("id") or application.get("job_id")
    application_id = application.get("application_id") or job_id or "missing"
    status = _status_label(application.get("status"))
    status_class = _status_class(status)
    wrap_key = f"employee-application-wrap-{application_id}"
    click_key = f"employee-application-click-{application_id}"

    with st.container(key=wrap_key):
        st.markdown(
            f"""
            <div class="job-card employee-application-card">
                <div class="job-card-media">{_job_logo_markup(job)}</div>
                <div class="job-card-body">
                    <div class="job-card-main">
                        <div>
                            <div class="job-card-title">{html_or_empty(job.get("title"), "Untitled job")}</div>
                            <div class="job-card-company">{html_or_empty(job.get("company_name"), "No company yet")}</div>
                            <div class="job-tag-row">{_job_tags(job)}</div>
                        </div>
                        <div class="employee-application-side">
                            <span class="employee-application-status {status_class}">{html_or_empty(status.title())}</span>
                            <div class="employee-application-salary">{html_or_empty(_format_salary(job))}</div>
                            <div class="employee-application-date">Applied: {html_or_empty(_format_datetime(application.get("applied_at")))}</div>
                        </div>
                    </div>
                    <div class="job-card-footer">
                        <div class="job-card-meta">{html_or_empty(_job_meta(job))}</div>
                        <div class="job-card-posted">{html_or_empty(_posted_label(job.get("created_at")))}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.button(
            "Xem chi tiết",
            key=click_key,
            disabled=job_id is None,
            help="Xem chi tiết công việc",
            use_container_width=True,
            on_click=_open_job_detail if job_id is not None else None,
            args=(int(job_id),) if job_id is not None else None,
        )


def render_applications_page() -> None:
    st.markdown('<div class="recommendation-title">My applications</div>', unsafe_allow_html=True)
    header_col, action_col = st.columns([8, 1.6], gap="small")
    header_col.markdown(
        '<div class="recommendation-subtitle">Track the jobs you have applied to and their current status.</div>',
        unsafe_allow_html=True,
    )
    if action_col.button("Refresh", key="refresh_my_applications", use_container_width=True):
        st.session_state.pop("my_applications", None)
        st.rerun()

    applications = _load_my_applications()
    if applications is None:
        return

    if not applications:
        st.markdown(
            '<div class="empty-state">You have not submitted any applications yet.</div>',
            unsafe_allow_html=True,
        )
        return

    for application in applications:
        _render_application_card(application)
