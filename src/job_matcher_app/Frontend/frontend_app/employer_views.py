from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from html import escape
from typing import Any

import streamlit as st

from frontend_app.api_client import (
    ApiError,
    create_job_posting,
    get_job_applications,
    get_job_detail,
    get_my_employer_jobs,
    refresh_employer_profile,
    update_job_posting,
)
from frontend_app.forms import render_dialog_header, render_discard_confirmation
from frontend_app.formatting import (
    clean_payload,
    format_date_range,
    html_or_empty,
    initials,
    show_api_error,
)
from frontend_app.loading import form_loading
from frontend_app.recommendation_views import _format_salary, _posted_label
from frontend_app.state import close_dialog, navigate_to, navigate_to_employer_job_detail, open_dialog


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


def _load_job_applications(job_id: int) -> list[dict[str, Any]] | None:
    cache_key = f"employer_job_applications_{job_id}"
    if cache_key not in st.session_state:
        try:
            with form_loading("Loading applications..."):
                st.session_state[cache_key] = get_job_applications(job_id)
        except ApiError as exc:
            show_api_error("Could not load applications", exc)
            return None
    return st.session_state.get(cache_key) or []


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
        st.session_state.pop(f"employer_job_applications_{job_id}", None)
    else:
        _delete_session_keys_with_prefix("employer_job_detail_")
        _delete_session_keys_with_prefix("employer_job_applications_")


def _render_view_dialog_header(title: str, key_prefix: str) -> None:
    title_col, close_col = st.columns([10, 0.7], gap="small")
    title_col.markdown(
        f'<div class="custom-dialog-title">{html_or_empty(title)}</div>',
        unsafe_allow_html=True,
    )
    if close_col.button("×", key=f"{key_prefix}_close", help="Close"):
        close_dialog()
        st.rerun()


def _employee_name(application: dict[str, Any]) -> str:
    employee = application.get("employee") or {}
    return employee.get("full_name") or employee.get("email") or "Candidate"


def _employee_profile(application: dict[str, Any]) -> dict[str, Any]:
    employee = application.get("employee") or {}
    return employee.get("employee_profile") or {}


def _application_subtitle(application: dict[str, Any]) -> str:
    profile = _employee_profile(application)
    bits = [
        profile.get("headline"),
        profile.get("current_location"),
    ]
    years = profile.get("years_of_experience")
    if years is not None:
        bits.append(f"{years} years exp")
    return " | ".join(str(bit) for bit in bits if bit) or "No profile summary yet"


def _skill_chips(skills: list[dict[str, Any]] | None) -> str:
    if not skills:
        return '<span class="candidate-muted">No skills yet.</span>'
    return "".join(
        f'<span class="candidate-skill-chip">{html_or_empty(skill.get("skill_name"))}</span>'
        for skill in skills
        if skill.get("skill_name")
    )


def _open_candidate_dialog(application: dict[str, Any]) -> None:
    st.session_state["active_candidate_application"] = application
    open_dialog("candidate_detail", application.get("application_id"))


def _render_applications_section(job_id: int) -> None:
    title_col, refresh_col = st.columns([4, 1], gap="small")
    title_col.markdown(
        '<div class="applications-section-title">Applications</div>',
        unsafe_allow_html=True,
    )
    if refresh_col.button(
        "Reload",
        key=f"refresh_job_applications_{job_id}",
        use_container_width=True,
    ):
        st.session_state.pop(f"employer_job_applications_{job_id}", None)
        st.rerun()

    applications = _load_job_applications(job_id)
    if applications is None:
        return

    st.markdown(
        f'<div class="applications-count">{len(applications)} applications</div>',
        unsafe_allow_html=True,
    )
    if not applications:
        st.markdown(
            '<div class="empty-state">No applications for this job yet.</div>',
            unsafe_allow_html=True,
        )
        return

    for application in applications:
        application_id = application.get("application_id")
        employee = application.get("employee") or {}
        profile = employee.get("employee_profile") or {}
        row_col, action_col = st.columns([4, 1], gap="small")
        row_col.markdown(
            f"""
            <div class="application-row">
                <div class="application-main">
                    <div class="application-name">{html_or_empty(_employee_name(application))}</div>
                    <div class="application-meta">{html_or_empty(_application_subtitle(application))}</div>
                </div>
                <div class="application-side">
                    <span class="application-status">{html_or_empty(str(application.get("status") or "pending").title())}</span>
                    <div class="application-date">Applied: {html_or_empty(_format_datetime(application.get("applied_at")))}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        action_col.write("")
        if action_col.button(
            "View",
            key=f"view_candidate_{application_id or employee.get('employee_id')}",
            use_container_width=True,
            on_click=_open_candidate_dialog,
            args=(application,),
        ):
            pass


def _render_candidate_timeline_item(item: dict[str, Any], kind: str) -> None:
    if kind == "experience":
        title = item.get("title") or "Experience"
        secondary = item.get("company_name")
    else:
        title = item.get("school") or "Education"
        secondary = " | ".join(
            str(bit)
            for bit in (item.get("degree"), item.get("field_of_study"))
            if bit
        )
    meta_bits = [
        secondary,
        item.get("employment_type"),
        item.get("location") or item.get("location_type"),
        format_date_range(item.get("start_date"), item.get("end_date")),
    ]
    meta = " | ".join(str(bit) for bit in meta_bits if bit)
    description = item.get("description") or ""
    st.markdown(
        f"""
        <div class="candidate-timeline-item">
            <div class="candidate-item-title">{html_or_empty(title)}</div>
            <div class="candidate-item-meta">{html_or_empty(meta)}</div>
            <div class="candidate-item-description">{html_or_empty(description, "No description yet.")}</div>
            <div class="candidate-skill-row">{_skill_chips(item.get("skills"))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.dialog(DIALOG_NATIVE_TITLE, dismissible=False)
def candidate_detail_dialog() -> None:
    application = st.session_state.get("active_candidate_application") or {}
    employee = application.get("employee") or {}
    profile = employee.get("employee_profile") or {}
    title = _employee_name(application)
    _render_view_dialog_header(title, "candidate_detail_dialog")

    contact_bits = [
        employee.get("email"),
        employee.get("phone"),
        profile.get("current_location"),
    ]
    contact = " | ".join(str(bit) for bit in contact_bits if bit)
    st.markdown(
        f"""
        <div class="candidate-hero">
            <div class="candidate-avatar">{html_or_empty(initials(title, "CA"))}</div>
            <div class="candidate-hero-main">
                <div class="candidate-headline">{html_or_empty(profile.get("headline"), "No headline yet.")}</div>
                <div class="candidate-contact">{html_or_empty(contact, "No contact details yet.")}</div>
                <div class="candidate-application-meta">
                    Applied {_format_datetime(application.get("applied_at"))} · {html_or_empty(str(application.get("status") or "pending").title())}
                </div>
            </div>
        </div>
        <div class="candidate-summary">{html_or_empty(profile.get("summary"), "No profile summary yet.")}</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="candidate-section-title">Skills</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="candidate-skill-row">{_skill_chips(employee.get("skills"))}</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="candidate-section-title">Experience</div>', unsafe_allow_html=True)
    experiences = employee.get("experiences") or []
    if not experiences:
        st.markdown('<div class="empty-state">No experience yet.</div>', unsafe_allow_html=True)
    for experience in experiences:
        _render_candidate_timeline_item(experience, "experience")

    st.markdown('<div class="candidate-section-title">Education</div>', unsafe_allow_html=True)
    educations = employee.get("educations") or []
    if not educations:
        st.markdown('<div class="empty-state">No education yet.</div>', unsafe_allow_html=True)
    for education in educations:
        _render_candidate_timeline_item(education, "education")


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


def _render_job_detail_text_section(title: str, value: Any) -> None:
    body = _clean_text(value)
    st.markdown(
        f"""
        <section class="employer-job-detail-section">
            <div class="employer-job-detail-section-title">{html_or_empty(title)}</div>
            <div class="employer-job-detail-section-body">{html_or_empty(body, "No information yet.")}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_employer_job_detail_page(job_id: int) -> None:
    job = _load_job_detail(job_id)
    if job is None:
        if st.button("Back to dashboard", key="employer_job_detail_back_error"):
            navigate_to("dashboard")
            st.rerun()
        return

    back_col, edit_col = st.columns([4, 1], gap="small")
    if back_col.button("Back to dashboard", key="employer_job_detail_back"):
        navigate_to("dashboard")
        st.rerun()
    if edit_col.button(
        "Edit",
        key=f"employer_job_detail_edit_{job_id}",
        use_container_width=True,
        on_click=_open_edit_job_dialog,
        args=(job_id,),
    ):
        pass

    status = _status_label(job.get("status"))
    status_class = "employer-job-status-" + "".join(
        char for char in status if char.isalnum()
    )
    company = job.get("company") or {}
    st.markdown(
        f"""
        <section class="employer-job-detail-hero">
            <div class="employer-job-detail-title-row">
                <div>
                    <div class="employer-job-detail-title">{html_or_empty(job.get("title"), "Untitled job")}</div>
                    <div class="employer-job-detail-company">{html_or_empty(company.get("name"), "Company")}</div>
                </div>
                <span class="employer-job-status {status_class}">{html_or_empty(status.title())}</span>
            </div>
            <div class="employer-job-detail-stat-grid">
                <div class="employer-job-detail-stat">
                    <div class="employer-job-detail-stat-label">Salary</div>
                    <div class="employer-job-detail-stat-value">{html_or_empty(_format_salary(job))}</div>
                </div>
                <div class="employer-job-detail-stat">
                    <div class="employer-job-detail-stat-label">Location</div>
                    <div class="employer-job-detail-stat-value">{html_or_empty(job.get("location") or job.get("address") or job.get("location_type"), "Not set")}</div>
                </div>
                <div class="employer-job-detail-stat">
                    <div class="employer-job-detail-stat-label">Type</div>
                    <div class="employer-job-detail-stat-value">{html_or_empty(job.get("employment_type"), "Not set")}</div>
                </div>
                <div class="employer-job-detail-stat">
                    <div class="employer-job-detail-stat-label">Deadline</div>
                    <div class="employer-job-detail-stat-value">{html_or_empty(_format_datetime(job.get("deadline")))}</div>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    _render_job_detail_text_section("Description", job.get("description"))
    _render_job_detail_text_section("Requirement", job.get("requirement"))
    _render_job_detail_text_section("Benefit", job.get("benefit"))
    _render_applications_section(job_id)
    _render_active_employer_dialog()


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

        if is_edit:
            delete_col, _, submit_col = st.columns([1.3, 2.7, 1.3])
            delete_submitted = delete_col.form_submit_button(
                "Delete",
                use_container_width=True,
            )
        else:
            delete_submitted = False
            _, submit_col = st.columns([4, 1.3])
        submitted = submit_col.form_submit_button(
            submit_label,
            type="primary",
            use_container_width=True,
        )

    if delete_submitted:
        if job_id is None:
            st.warning("Job not found.")
            return
        try:
            with form_loading("Deleting job..."):
                update_job_posting(int(job_id), {"status": "deleted"})
            _clear_job_caches(int(job_id))
            _clear_job_form_state()
            close_dialog()
            st.success("Job deleted.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Could not delete job", exc)
        return

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
    elif active_dialog == "candidate_detail":
        candidate_detail_dialog()


def _open_create_job_dialog() -> None:
    _clear_job_form_state()
    open_dialog("create_job")


def _open_edit_job_dialog(job_id: int) -> None:
    _clear_job_form_state()
    open_dialog("edit_job", job_id)


def _open_employer_job_detail(job_id: int) -> None:
    navigate_to_employer_job_detail(job_id)


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
            "View job",
            key=button_key,
            disabled=job_id is None,
            help="View job detail",
            use_container_width=True,
            on_click=_open_employer_job_detail if job_id is not None else None,
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

    if st.session_state.get("current_page") == "employer_job_detail":
        job_id = st.session_state.get("selected_employer_job_id")
        if job_id is None:
            navigate_to("dashboard")
            st.rerun()
            return
        _render_employer_job_detail_page(int(job_id))
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
