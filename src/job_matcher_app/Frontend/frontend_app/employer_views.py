from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from html import escape
from typing import Any

import streamlit as st

from frontend_app.api_client import (
    ApiError,
    create_job_posting,
    get_job_detail,
    get_my_employer_jobs,
    refresh_employer_profile,
    update_job_posting,
)
from frontend_app.forms import render_dialog_header, render_discard_confirmation
from frontend_app.formatting import clean_payload, html_or_empty, initials, show_api_error
from frontend_app.loading import form_loading
from frontend_app.recommendation_views import _format_salary, _posted_label
from frontend_app.state import close_dialog, open_dialog


DIALOG_NATIVE_TITLE = "\u200b"
STATUS_OPTIONS = ["open", "draft", "closed"]
EMPLOYMENT_OPTIONS = ["", "Full-time", "Part-time", "Contract", "Internship", "Remote"]
LOCATION_TYPE_OPTIONS = ["", "On-site", "Hybrid", "Remote"]


def _load_employer_jobs() -> list[dict[str, Any]] | None:
    if "employer_jobs" not in st.session_state:
        try:
            with form_loading("Loading jobs..."):
                st.session_state["employer_jobs"] = get_my_employer_jobs()
        except ApiError as exc:
            show_api_error("Could not load employer jobs", exc)
            return None
    return st.session_state.get("employer_jobs") or []


def _load_job_detail(job_id: int) -> dict[str, Any] | None:
    cache_key = f"employer_job_detail_{job_id}"
    if cache_key not in st.session_state:
        try:
            with form_loading("Loading job detail..."):
                st.session_state[cache_key] = get_job_detail(job_id)
        except ApiError as exc:
            show_api_error("Could not load job detail", exc)
            return None
    return st.session_state.get(cache_key)


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


def _clean_text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _format_form_value(value: Any) -> str:
    return "" if value is None else str(value)


def _parse_decimal(value: str, label: str) -> str | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        amount = Decimal(cleaned)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{label} must be a valid number.") from exc
    if amount < 0:
        raise ValueError(f"{label} must be greater than or equal to 0.")
    return str(amount)


def _parse_int(value: str, label: str) -> int | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        number = int(cleaned)
    except ValueError as exc:
        raise ValueError(f"{label} must be a whole number.") from exc
    if number < 0:
        raise ValueError(f"{label} must be greater than or equal to 0.")
    return number


def _parse_deadline(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _deadline_to_api(enabled: bool, value: date | None) -> str | None:
    if not enabled or value is None:
        return None
    return datetime.combine(value, time(hour=23, minute=59, second=59)).isoformat()


def _select_index(options: list[str], value: Any) -> int:
    cleaned = _clean_text(value)
    return options.index(cleaned) if cleaned in options else 0


def _delete_session_keys_with_prefix(prefix: str) -> None:
    for key in list(st.session_state.keys()):
        if key.startswith(prefix):
            del st.session_state[key]


def _clear_job_form_state() -> None:
    _delete_session_keys_with_prefix("employer_job_create_")
    _delete_session_keys_with_prefix("employer_job_edit_")
    st.session_state["employer_job_form_mode"] = None
    st.session_state["employer_edit_job_id"] = None


def _clear_job_caches(job_id: int | None = None) -> None:
    st.session_state.pop("employer_jobs", None)
    if job_id is not None:
        st.session_state.pop(f"employer_job_detail_{job_id}", None)


def _render_company_summary(profile: dict[str, Any]) -> None:
    company = profile.get("company") or {}
    employer_profile = profile.get("employer_profile") or {}
    company_name = _clean_text(company.get("name")) or "Company profile"
    logo_url = (company.get("logo_url") or "").strip()
    logo_markup = (
        f'<img class="employer-company-logo" src="{escape(logo_url)}" alt="{html_or_empty(company_name)}">'
        if logo_url
        else f'<div class="employer-company-logo-placeholder">{escape(initials(company_name, "CO"))}</div>'
    )
    facts = [
        _clean_text(company.get("industry")),
        _clean_text(company.get("company_size")),
        _clean_text(company.get("location")) or _clean_text(company.get("address")),
    ]
    fact_markup = "".join(
        f'<span class="employer-fact">{html_or_empty(fact)}</span>'
        for fact in facts
        if fact
    )
    fact_row_markup = (
        f'<div class="employer-fact-row">{fact_markup}</div>'
        if fact_markup
        else '<div class="employer-missing-note">Company details have not been updated.</div>'
    )
    website = _clean_text(company.get("website"))
    website_markup = (
        f'<a class="employer-company-link" href="{escape(website)}" target="_blank">Website</a>'
        if website
        else ""
    )
    description = _clean_text(company.get("description"))
    description_markup = (
        f'<div class="employer-description">{html_or_empty(description)}</div>'
        if description
        else '<div class="employer-description employer-description-muted">No company description yet.</div>'
    )
    signed_in_name = _clean_text(profile.get("full_name")) or _clean_text(profile.get("email"))
    position = _clean_text(employer_profile.get("position"))
    profile_bits = [bit for bit in (signed_in_name, position) if bit]
    profile_line_markup = (
        f'<div class="employer-profile-line">{" &middot; ".join(html_or_empty(bit) for bit in profile_bits)}</div>'
        if profile_bits
        else ""
    )

    summary_markup = (
        '<div class="employer-summary">'
        '<div class="employer-summary-header">'
        f'<div class="employer-summary-logo">{logo_markup}</div>'
        '<div class="employer-summary-main">'
        '<div class="employer-title-row">'
        f'<div class="employer-company-name">{html_or_empty(company_name)}</div>'
        f'{website_markup}'
        '</div>'
        f'{profile_line_markup}'
        f'{fact_row_markup}'
        '</div>'
        '</div>'
        f'{description_markup}'
        '</div>'
    )

    st.markdown(summary_markup, unsafe_allow_html=True)


def _build_job_payload(
    *,
    title: str,
    description: str,
    requirement: str,
    benefit: str,
    salary_min: str,
    salary_max: str,
    salary_currency: str,
    experience_required: str,
    employment_type: str,
    working_time: str,
    location_type: str,
    address: str,
    deadline_enabled: bool,
    deadline: date | None,
    status: str,
) -> dict[str, Any]:
    salary_min_value = _parse_decimal(salary_min, "Salary min")
    salary_max_value = _parse_decimal(salary_max, "Salary max")
    if salary_min_value is not None and salary_max_value is not None:
        if Decimal(salary_max_value) < Decimal(salary_min_value):
            raise ValueError("Salary max must be greater than or equal to salary min.")

    return clean_payload(
        {
            "title": title,
            "description": description,
            "requirement": requirement,
            "benefit": benefit,
            "salary_min": salary_min_value,
            "salary_max": salary_max_value,
            "salary_currency": salary_currency,
            "experience_required": _parse_int(experience_required, "Experience required"),
            "employment_type": employment_type,
            "working_time": working_time,
            "location_type": location_type,
            "address": address,
            "deadline": _deadline_to_api(deadline_enabled, deadline),
            "status": status,
        }
    )


def _render_job_form(mode: str, job: dict[str, Any] | None = None) -> None:
    job = job or {}
    is_edit = mode == "edit"
    job_id = job.get("job_id") or job.get("id")
    submit_label = "Save changes" if is_edit else "Create job"
    form_key = f"employer_job_{mode}_{job_id or 'new'}"
    parsed_deadline = _parse_deadline(job.get("deadline"))

    with st.form(f"{form_key}_form"):
        title = st.text_input(
            "Title",
            value=_format_form_value(job.get("title")),
            key=f"{form_key}_title",
        )
        status = st.selectbox(
            "Status",
            STATUS_OPTIONS,
            index=_select_index(STATUS_OPTIONS, job.get("status") or "open"),
            key=f"{form_key}_status",
        )

        salary_col, exp_col, currency_col = st.columns(3)
        salary_min = salary_col.text_input(
            "Salary min",
            value=_format_form_value(job.get("salary_min")),
            key=f"{form_key}_salary_min",
        )
        salary_max = exp_col.text_input(
            "Salary max",
            value=_format_form_value(job.get("salary_max")),
            key=f"{form_key}_salary_max",
        )
        salary_currency = currency_col.text_input(
            "Currency",
            value=_format_form_value(job.get("salary_currency") or "VND"),
            key=f"{form_key}_salary_currency",
        )

        type_col, working_col, location_type_col = st.columns(3)
        employment_type = type_col.selectbox(
            "Employment type",
            EMPLOYMENT_OPTIONS,
            index=_select_index(EMPLOYMENT_OPTIONS, job.get("employment_type")),
            key=f"{form_key}_employment_type",
        )
        working_time = working_col.text_input(
            "Working time",
            value=_format_form_value(job.get("working_time")),
            key=f"{form_key}_working_time",
        )
        location_type = location_type_col.selectbox(
            "Location type",
            LOCATION_TYPE_OPTIONS,
            index=_select_index(LOCATION_TYPE_OPTIONS, job.get("location_type")),
            key=f"{form_key}_location_type",
        )

        address_col, experience_col = st.columns([2, 1])
        address = address_col.text_input(
            "Address",
            value=_format_form_value(job.get("address")),
            key=f"{form_key}_address",
        )
        experience_required = experience_col.text_input(
            "Experience required",
            value=_format_form_value(job.get("experience_required")),
            key=f"{form_key}_experience_required",
        )

        deadline_enabled = st.checkbox(
            "Set deadline",
            value=parsed_deadline is not None,
            key=f"{form_key}_deadline_enabled",
        )
        deadline = None
        if deadline_enabled:
            deadline = st.date_input(
                "Deadline",
                value=parsed_deadline or date.today(),
                key=f"{form_key}_deadline",
            )

        description = st.text_area(
            "Description",
            value=_format_form_value(job.get("description")),
            key=f"{form_key}_description",
        )
        requirement = st.text_area(
            "Requirement",
            value=_format_form_value(job.get("requirement")),
            key=f"{form_key}_requirement",
        )
        benefit = st.text_area(
            "Benefit",
            value=_format_form_value(job.get("benefit")),
            key=f"{form_key}_benefit",
        )

        _, submit_col = st.columns([4, 1.3])
        submitted = submit_col.form_submit_button(
            submit_label,
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return

    if not title.strip():
        st.warning("Title is required.")
        return

    try:
        payload = _build_job_payload(
            title=title,
            description=description,
            requirement=requirement,
            benefit=benefit,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            experience_required=experience_required,
            employment_type=employment_type,
            working_time=working_time,
            location_type=location_type,
            address=address,
            deadline_enabled=deadline_enabled,
            deadline=deadline,
            status=status,
        )
    except ValueError as exc:
        st.warning(str(exc))
        return

    try:
        loading_label = "Saving job..." if is_edit else "Creating job..."
        with form_loading(loading_label):
            if is_edit and job_id is not None:
                update_job_posting(int(job_id), payload)
            else:
                create_job_posting(payload)
        _clear_job_caches(int(job_id) if job_id is not None else None)
        _clear_job_form_state()
        close_dialog()
        st.success("Job saved successfully.")
        st.rerun()
    except ApiError as exc:
        show_api_error("Could not save job", exc)


@st.dialog(DIALOG_NATIVE_TITLE, dismissible=False)
def create_job_dialog() -> None:
    render_dialog_header("Create job", "create_job_dialog")
    _render_job_form("create")
    render_discard_confirmation("create_job_dialog")


@st.dialog(DIALOG_NATIVE_TITLE, dismissible=False)
def edit_job_dialog() -> None:
    render_dialog_header("Edit job", "edit_job_dialog")

    job_id = st.session_state.get("active_item_id")
    if job_id is None:
        st.info("Job not found.")
        render_discard_confirmation("edit_job_dialog")
        return

    job_detail = _load_job_detail(int(job_id))
    if job_detail is not None:
        _render_job_form("edit", job_detail)
    render_discard_confirmation("edit_job_dialog")


def _render_active_employer_dialog() -> None:
    active_dialog = st.session_state.get("active_dialog")
    if active_dialog == "create_job":
        create_job_dialog()
    elif active_dialog == "edit_job":
        edit_job_dialog()


def _open_create_job_dialog() -> None:
    _clear_job_form_state()
    open_dialog("create_job")


def _open_edit_job_dialog(job_id: int) -> None:
    _clear_job_form_state()
    open_dialog("edit_job", job_id)


def _render_job_row(job: dict[str, Any]) -> None:
    job_id = job.get("job_id") or job.get("id")
    status = _status_label(job.get("status"))
    status_class = "employer-job-status-" + "".join(
        char for char in status if char.isalnum()
    )
    row_key = f"employer-job-wrap-{job_id or 'missing'}"
    button_key = f"employer-job-click-{job_id or 'missing'}"
    with st.container(key=row_key):
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
        st.button(
            "Edit job",
            key=button_key,
            disabled=job_id is None,
            help="Edit job",
            use_container_width=True,
            on_click=_open_edit_job_dialog if job_id is not None else None,
            args=(int(job_id),) if job_id is not None else None,
        )


def _render_jobs_section(jobs: list[dict[str, Any]]) -> None:
    header_col, create_col, refresh_col = st.columns([4, 1, 1], gap="small")
    header_col.markdown(
        f'<div class="employer-section-title">Jobs <span>{len(jobs)}</span></div>',
        unsafe_allow_html=True,
    )
    create_col.button(
        "Create",
        key="employer_jobs_create",
        use_container_width=True,
        on_click=_open_create_job_dialog,
    )
    if refresh_col.button("Refresh", key="employer_jobs_refresh", use_container_width=True):
        _clear_job_caches()
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
    _render_active_employer_dialog()
