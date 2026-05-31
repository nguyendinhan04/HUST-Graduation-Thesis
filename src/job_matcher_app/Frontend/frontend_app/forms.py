from __future__ import annotations

from datetime import date
from html import escape
from typing import Any

import streamlit as st

from frontend_app.formatting import (
    clean_payload,
    date_to_api,
    nullable_text,
    optional_date_input,
    parse_iso_date,
    skills_to_text,
    split_skills,
)
from frontend_app.state import (
    cancel_discard_confirmation,
    clear_active_dialog_draft,
    close_dialog,
    request_discard_confirmation,
)


def render_dialog_header(title: str, key_prefix: str) -> None:
    title_col, close_col = st.columns([10, 0.7], gap="small")
    title_col.markdown(
        f'<div class="custom-dialog-title">{escape(title)}</div>',
        unsafe_allow_html=True,
    )
    if close_col.button("×", key=f"{key_prefix}_close", help="Discard changes"):
        request_discard_confirmation()
        st.rerun()


def render_discard_confirmation(key_prefix: str) -> bool:
    if not st.session_state.get("confirm_discard"):
        return False

    st.markdown(
        """
        <div class="discard-confirm-backdrop"></div>
        <div class="discard-confirm">
            <div class="discard-title">Discard changes</div>
            <div class="discard-message">
                All unsaved changes will be discarded, and you'll return to your profile.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    marker_col, _, no_col, discard_col = st.columns([0.01, 4.49, 1.35, 1.35], gap="small")
    marker_col.markdown(
        '<div class="discard-confirm-actions-marker"></div>',
        unsafe_allow_html=True,
    )
    if no_col.button("No thanks", key=f"{key_prefix}_keep_editing", use_container_width=True):
        cancel_discard_confirmation()
        st.rerun()
    if discard_col.button(
        "Discard",
        key=f"{key_prefix}_discard",
        type="primary",
        use_container_width=True,
    ):
        clear_active_dialog_draft()
        close_dialog()
        st.rerun()
    return False



def profile_payload_form(form_key: str, profile: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    employee = profile.get("employee_profile") or {}
    with st.form(form_key):
        full_name = st.text_input("Full name", value=nullable_text(profile.get("full_name")))
        headline = st.text_input("Headline", value=nullable_text(employee.get("headline")))
        current_location = st.text_input(
            "Current location",
            value=nullable_text(employee.get("current_location")),
        )
        phone = st.text_input("Phone", value=nullable_text(profile.get("phone")))
        avatar_url = st.text_input(
            "Avatar URL",
            value=nullable_text(profile.get("avatar_url")),
        )
        years_of_experience = st.number_input(
            "Years of experience",
            min_value=0,
            step=1,
            value=int(employee.get("years_of_experience") or 0),
        )
        summary = st.text_area(
            "Summary",
            value=nullable_text(employee.get("summary")),
            height=120,
        )
        _, save_col = st.columns([5, 1.25])
        save_submitted = save_col.form_submit_button(
            "Save",
            type="primary",
            use_container_width=True,
        )

    payload = clean_payload(
        {
            "full_name": full_name,
            "phone": phone,
            "avatar_url": avatar_url,
            "headline": headline,
            "summary": summary,
            "years_of_experience": int(years_of_experience),
            "current_location": current_location,
        }
    )
    action = "save" if save_submitted else None
    return payload, action



def experience_payload_form(
    form_key: str,
    item: dict[str, Any] | None = None,
    *,
    allow_delete: bool = False,
) -> tuple[dict[str, Any], str | None]:
    item = item or {}
    title = st.text_input("Title", value=nullable_text(item.get("title")), key=f"{form_key}_title")
    employment_type = st.text_input(
        "Employment type",
        value=nullable_text(item.get("employment_type")),
        key=f"{form_key}_employment_type",
    )
    company_name = st.text_input(
        "Company",
        value=nullable_text(item.get("company_name")),
        key=f"{form_key}_company_name",
    )
    location = st.text_input(
        "Location",
        value=nullable_text(item.get("location")),
        key=f"{form_key}_location",
    )
    location_type = st.text_input(
        "Location type",
        value=nullable_text(item.get("location_type")),
        key=f"{form_key}_location_type",
    )
    start_date = st.date_input(
        "Start date",
        value=parse_iso_date(item.get("start_date")) or date.today(),
        key=f"{form_key}_start_date",
    )
    currently_work_here = st.checkbox(
        "Currently work here",
        value=item.get("end_date") is None,
        key=f"{form_key}_currently_work_here",
    )
    if currently_work_here:
        end_date = None
        st.caption("End date will be shown as Now.")
    else:
        end_date = st.date_input(
            "End date",
            value=parse_iso_date(item.get("end_date")) or date.today(),
            key=f"{form_key}_end_date",
        )
    skills = st.text_input(
        "Skills",
        value=skills_to_text(item.get("skills")),
        key=f"{form_key}_skills",
    )
    description = st.text_area(
        "Description",
        value=nullable_text(item.get("description")),
        height=120,
        key=f"{form_key}_description",
    )
    if allow_delete:
        delete_col, _, save_col = st.columns([1.3, 4.4, 1.3])
        delete_submitted = delete_col.button(
            "Delete",
            key=f"{form_key}_delete",
            use_container_width=True,
        )
        save_submitted = save_col.button(
            "Save",
            key=f"{form_key}_save",
            type="primary",
            use_container_width=True,
        )
    else:
        delete_submitted = False
        _, save_col = st.columns([5, 1.25])
        save_submitted = save_col.button(
            "Save",
            key=f"{form_key}_save",
            type="primary",
            use_container_width=True,
        )

    payload = clean_payload(
        {
            "title": title,
            "company_name": company_name,
            "employment_type": employment_type,
            "location": location,
            "location_type": location_type,
            "description": description,
            "start_date": date_to_api(start_date),
            "end_date": date_to_api(end_date),
            "skills": split_skills(skills),
        }
    )
    action = "delete" if delete_submitted else "save" if save_submitted else None
    return payload, action



def education_payload_form(
    form_key: str,
    item: dict[str, Any] | None = None,
    *,
    allow_delete: bool = False,
) -> tuple[dict[str, Any], str | None]:
    item = item or {}
    with st.form(form_key):
        school = st.text_input("School", value=nullable_text(item.get("school")))
        degree = st.text_input("Degree", value=nullable_text(item.get("degree")))
        field_of_study = st.text_input(
            "Field of study",
            value=nullable_text(item.get("field_of_study")),
        )
        start_date = optional_date_input(
            "Start date",
            f"{form_key}_start",
            item.get("start_date"),
        )
        end_date = optional_date_input(
            "End date",
            f"{form_key}_end",
            item.get("end_date"),
        )
        skills = st.text_input("Skills", value=skills_to_text(item.get("skills")))
        description = st.text_area(
            "Description",
            value=nullable_text(item.get("description")),
            height=120,
        )
        if allow_delete:
            delete_col, _, save_col = st.columns([1.3, 4.4, 1.3])
            delete_submitted = delete_col.form_submit_button(
                "Delete",
                use_container_width=True,
            )
            save_submitted = save_col.form_submit_button(
                "Save",
                type="primary",
                use_container_width=True,
            )
        else:
            delete_submitted = False
            _, save_col = st.columns([5, 1.25])
            save_submitted = save_col.form_submit_button(
                "Save",
                type="primary",
                use_container_width=True,
            )

    payload = clean_payload(
        {
            "school": school,
            "degree": degree,
            "field_of_study": field_of_study,
            "description": description,
            "start_date": date_to_api(start_date),
            "end_date": date_to_api(end_date),
            "skills": split_skills(skills),
        }
    )
    action = "delete" if delete_submitted else "save" if save_submitted else None
    return payload, action

