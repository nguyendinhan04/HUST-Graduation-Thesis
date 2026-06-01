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
PAGE_SIZE = 10


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
    page: int,
) -> dict[str, Any] | None:
    cache_key = (
        "explore_jobs",
        query or "",
        location or "",
        employment_type or "",
        max_experience,
        page,
        PAGE_SIZE,
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
                    page=page,
                    page_size=PAGE_SIZE,
                )
        except ApiError as exc:
            show_api_error("Could not load jobs", exc)
            return None

    return st.session_state.get("explore_jobs") or {
        "items": [],
        "total": 0,
        "page": page,
        "page_size": PAGE_SIZE,
        "total_pages": 1,
    }


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
                            <div class="job-card-title">{html_or_empty(job.get("title"), "Untitled job")}</div>
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


def _sync_filter_page(filter_key: tuple[Any, ...]) -> int:
    if st.session_state.get("explore_jobs_filter_key") != filter_key:
        st.session_state["explore_jobs_filter_key"] = filter_key
        st.session_state["explore_jobs_page"] = 1
        st.session_state.pop("explore_jobs", None)
    return int(st.session_state.setdefault("explore_jobs_page", 1))


def _render_pagination(page: int, total_pages: int) -> None:
    prev_col, meta_col, next_col = st.columns([1, 2, 1], gap="small")
    if prev_col.button(
        "Previous",
        key="explore_jobs_prev",
        use_container_width=True,
        disabled=page <= 1,
    ):
        st.session_state["explore_jobs_page"] = max(page - 1, 1)
        st.session_state.pop("explore_jobs", None)
        st.rerun()
    meta_col.markdown(
        f'<div class="explore-pagination-meta">Page {page} of {total_pages}</div>',
        unsafe_allow_html=True,
    )
    if next_col.button(
        "Next",
        key="explore_jobs_next",
        use_container_width=True,
        disabled=page >= total_pages,
    ):
        st.session_state["explore_jobs_page"] = page + 1
        st.session_state.pop("explore_jobs", None)
        st.rerun()


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

        type_col, exp_col, action_col = st.columns([1, 1, 0.8], gap="small")
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
        action_col.write("")
        action_col.write("")
        if action_col.button("Refresh", key="explore_jobs_refresh", use_container_width=True):
            st.session_state.pop("explore_jobs", None)

    query_filter = _clean_filter(query)
    location_filter = _clean_filter(location)
    employment_filter = None if employment_label == "Any type" else employment_label
    experience_filter = _selected_experience(experience_label)
    page = _sync_filter_page(
        (
            query_filter or "",
            location_filter or "",
            employment_filter or "",
            experience_filter,
        )
    )

    result = _load_jobs(
        query=query_filter,
        location=location_filter,
        employment_type=employment_filter,
        max_experience=experience_filter,
        page=page,
    )
    if result is None:
        return

    jobs = result.get("items") or []
    total = int(result.get("total") or 0)
    page = int(result.get("page") or page)
    total_pages = int(result.get("total_pages") or 1)
    if st.session_state.get("explore_jobs_page") != page:
        st.session_state["explore_jobs_page"] = page

    start_index = ((page - 1) * PAGE_SIZE) + 1 if total else 0
    end_index = min(page * PAGE_SIZE, total)
    st.markdown(
        f'<div class="explore-result-count">Showing {start_index}-{end_index} of {total} jobs</div>',
        unsafe_allow_html=True,
    )
    if not jobs:
        st.markdown('<div class="empty-state">No jobs match your filters.</div>', unsafe_allow_html=True)
        return

    for job in jobs:
        _render_job_card(job)

    _render_pagination(page, total_pages)
