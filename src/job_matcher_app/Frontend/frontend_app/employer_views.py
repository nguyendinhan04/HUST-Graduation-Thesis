from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any

import streamlit as st

from frontend_app.api_client import ApiError, get_my_employer_jobs, refresh_employer_profile
from frontend_app.formatting import html_or_empty, initials, show_api_error
from frontend_app.loading import form_loading
from frontend_app.recommendation_views import _format_salary, _posted_label


def _load_employer_jobs() -> list[dict[str, Any]] | None:
    if "employer_jobs" not in st.session_state:
        try:
            with form_loading("Loading jobs..."):
                st.session_state["employer_jobs"] = get_my_employer_jobs()
        except ApiError as exc:
            show_api_error("Could not load employer jobs", exc)
            return None
    return st.session_state.get("employer_jobs") or []


def _format_datetime(value: str | None) -> str:
    if not value:
        return "Not set"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    return parsed.strftime("%d/%m/%Y")


def _job_meta(job: dict[str, Any]) -> str:
    bits = []
    if job.get("address"):
        bits.append(str(job["address"]))
    elif job.get("location_type"):
        bits.append(str(job["location_type"]))
    if job.get("employment_type"):
        bits.append(str(job["employment_type"]))
    if job.get("working_time"):
        bits.append(str(job["working_time"]))
    experience_required = job.get("experience_required")
    if experience_required is not None:
        bits.append(f"{experience_required} years exp")
    return " | ".join(bits) or "No job metadata yet"


def _status_label(status: Any) -> str:
    value = str(status or "unknown").strip().lower()
    return value or "unknown"


def _render_company_summary(profile: dict[str, Any]) -> None:
    company = profile.get("company") or {}
    employer_profile = profile.get("employer_profile") or {}
    company_name = company.get("name") or "Company"
    logo_url = (company.get("logo_url") or "").strip()
    logo_markup = (
        f'<img class="employer-company-logo" src="{escape(logo_url)}" alt="{html_or_empty(company_name)}">'
        if logo_url
        else f'<div class="employer-company-logo-placeholder">{escape(initials(company_name, "CO"))}</div>'
    )
    facts = [
        company.get("industry"),
        company.get("company_size"),
        company.get("location") or company.get("address"),
    ]
    fact_markup = "".join(
        f'<span class="employer-fact">{html_or_empty(fact)}</span>'
        for fact in facts
        if fact
    )
    website = company.get("website")
    website_markup = (
        f'<a class="employer-company-link" href="{escape(website)}" target="_blank">Website</a>'
        if website
        else ""
    )
    description = company.get("description") or "No company description yet."
    signed_in_name = profile.get("full_name") or profile.get("email") or "Employer"
    position = employer_profile.get("position") or "Employer"

    st.markdown(
        f"""
        <section class="employer-summary">
            <div class="employer-summary-header">
                <div class="employer-summary-logo">{logo_markup}</div>
                <div class="employer-summary-main">
                    <div class="employer-title-row">
                        <div class="employer-company-name">{html_or_empty(company_name)}</div>
                        {website_markup}
                    </div>
                    <div class="employer-profile-line">{html_or_empty(signed_in_name)} · {html_or_empty(position)}</div>
                    <div class="employer-fact-row">{fact_markup}</div>
                </div>
            </div>
            <div class="employer-description">{html_or_empty(description)}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_job_row(job: dict[str, Any]) -> None:
    status = _status_label(job.get("status"))
    status_class = "employer-job-status-" + "".join(
        char for char in status if char.isalnum()
    )
    st.markdown(
        f"""
        <div class="employer-job-row">
            <div class="employer-job-main">
                <div class="employer-job-title">{html_or_empty(job.get("title"), "Untitled job")}</div>
                <div class="employer-job-meta">{html_or_empty(_job_meta(job))}</div>
            </div>
            <div class="employer-job-side">
                <span class="employer-job-status {status_class}">{html_or_empty(status.title())}</span>
                <div class="employer-job-salary">{html_or_empty(_format_salary(job))}</div>
                <div class="employer-job-date">Deadline: {html_or_empty(_format_datetime(job.get("deadline")))}</div>
                <div class="employer-job-date">{html_or_empty(_posted_label(job.get("created_at")))}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_jobs_section(jobs: list[dict[str, Any]]) -> None:
    header_col, action_col = st.columns([5, 1], gap="small")
    header_col.markdown(
        f'<div class="employer-section-title">Jobs <span>{len(jobs)}</span></div>',
        unsafe_allow_html=True,
    )
    if action_col.button("Refresh", key="employer_jobs_refresh", use_container_width=True):
        st.session_state.pop("employer_jobs", None)
        st.rerun()

    if not jobs:
        st.markdown(
            '<div class="empty-state">No jobs posted by this employer yet.</div>',
            unsafe_allow_html=True,
        )
        return

    for job in jobs:
        _render_job_row(job)


def render_employer_workspace() -> None:
    if st.session_state.get("profile") is None:
        try:
            with form_loading("Loading employer profile..."):
                refresh_employer_profile()
        except ApiError as exc:
            show_api_error("Could not load employer profile", exc)
            return

    profile = st.session_state["profile"]
    st.markdown('<div class="recommendation-title">Employer dashboard</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="recommendation-subtitle">Manage your company workspace and review posted jobs.</div>',
        unsafe_allow_html=True,
    )
    _render_company_summary(profile)

    jobs = _load_employer_jobs()
    if jobs is None:
        return
    _render_jobs_section(jobs)
