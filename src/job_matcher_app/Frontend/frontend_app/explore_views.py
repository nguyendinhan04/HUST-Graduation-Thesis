from __future__ import annotations

from typing import Any

import streamlit as st

from frontend_app.api_client import ApiError, search_jobs
from frontend_app.formatting import html_or_empty, show_api_error
from frontend_app.loading import form_loading
from frontend_app.recommendation_views import (
    _format_salary,
    _job_logo_markup,
    _job_meta,
    _job_tags,
    _posted_label,
)
from frontend_app.state import navigate_to_job_detail


EXPERIENCE_OPTIONS = ["Any", "0 years", "1 year", "2 years", "3 years", "5 years", "7 years", "10 years"]
EMPLOYMENT_OPTIONS = ["Any type", "Full-time", "Part-time", "Contract", "Internship", "Remote"]
LIMIT_OPTIONS = [20, 30, 50, 100]


def _clean_filter(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    return cleaned or None


def _selected_experience(value: str) -> int | None:
    if value == "Any":
        return None
    return int(value.split()[0])


def _load_jobs(
    query: str | None,
    location: str | None,
    employment_type: str | None,
    max_experience: int | None,
    limit: int,
) -> list[dict[str, Any]] | None:
    cache_key = (
        "explore_jobs",
        query or "",
        location or "",
        employment_type or "",
        max_experience,
        limit,
    )
    if st.session_state.get("explore_jobs_cache_key") != cache_key:
        st.session_state["explore_jobs_cache_key"] = cache_key
        st.session_state.pop("explore_jobs", None)

    if "explore_jobs" not in st.session_state:
        try:
            with form_loading("Loading jobs..."):
                st.session_state["explore_jobs"] = search_jobs(
                    query=query,
                    location=location,
                    employment_type=employment_type,
                    max_experience=max_experience,
                    limit=limit,
                )
        except ApiError as exc:
            show_api_error("Could not load jobs", exc)
            return None

    return st.session_state.get("explore_jobs") or []


def _render_job_card(job: dict[str, Any]) -> None:
    job_id = job.get("id") or job.get("job_id")
    card_key = f"job-card-wrap-explore-{job_id or 'missing'}"
    click_key = f"job-card-click-explore-{job_id or 'missing'}"
    with st.container(key=card_key):
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
            on_click=navigate_to_job_detail if job_id is not None else None,
            args=(int(job_id), "explore") if job_id is not None else None,
        )


def render_explore_jobs_page() -> None:
    st.markdown('<div class="recommendation-title">Explore jobs</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="recommendation-subtitle">Search open jobs by title, company, location, job type, and required experience.</div>',
        unsafe_allow_html=True,
    )

    with st.container(key="explore-jobs-filters"):
        search_col, location_col = st.columns([1.4, 1], gap="small")
        query = search_col.text_input(
            "Keyword",
            key="explore_jobs_query",
            placeholder="Title, company, or keyword",
        )
        location = location_col.text_input(
            "Location",
            key="explore_jobs_location",
            placeholder="City or remote",
        )

        type_col, exp_col, limit_col, action_col = st.columns([1, 1, 0.8, 0.8], gap="small")
        employment_label = type_col.selectbox(
            "Job type",
            EMPLOYMENT_OPTIONS,
            key="explore_jobs_employment_type",
        )
        experience_label = exp_col.selectbox(
            "Experience",
            EXPERIENCE_OPTIONS,
            key="explore_jobs_experience",
        )
        limit = int(limit_col.selectbox("Limit", LIMIT_OPTIONS, index=1, key="explore_jobs_limit"))
        action_col.write("")
        action_col.write("")
        if action_col.button("Refresh", key="explore_jobs_refresh", use_container_width=True):
            st.session_state.pop("explore_jobs", None)

    jobs = _load_jobs(
        query=_clean_filter(query),
        location=_clean_filter(location),
        employment_type=None if employment_label == "Any type" else employment_label,
        max_experience=_selected_experience(experience_label),
        limit=limit,
    )
    if jobs is None:
        return

    st.markdown(
        f'<div class="explore-result-count">{len(jobs)} jobs found</div>',
        unsafe_allow_html=True,
    )
    if not jobs:
        st.markdown('<div class="empty-state">No jobs match your filters.</div>', unsafe_allow_html=True)
        return

    for job in jobs:
        _render_job_card(job)
