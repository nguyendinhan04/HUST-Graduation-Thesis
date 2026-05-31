from __future__ import annotations

from typing import Any

import streamlit as st

from frontend_app.formatting import (
    clean_payload,
    date_to_api,
    nullable_text,
    optional_date_input,
    skills_to_text,
    split_skills,
)
from frontend_app.state import close_dialog


def render_dialog_close(key: str) -> None:
    _, close_col = st.columns([10, 0.55], gap="small")
    if close_col.button("×", key=key, help="Discard changes"):
        close_dialog()
        st.rerun()



def profile_payload_form(form_key: str, profile: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    employee = profile.get("employee_profile") or {}
    with st.form(form_key):
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full name", value=nullable_text(profile.get("full_name")))
            phone = st.text_input("Phone", value=nullable_text(profile.get("phone")))
            avatar_url = st.text_input(
                "Avatar URL",
                value=nullable_text(profile.get("avatar_url")),
            )
        with col2:
            headline = st.text_input("Headline", value=nullable_text(employee.get("headline")))
            years_of_experience = st.number_input(
                "Years of experience",
                min_value=0,
                step=1,
                value=int(employee.get("years_of_experience") or 0),
            )
            current_location = st.text_input(
                "Current location",
                value=nullable_text(employee.get("current_location")),
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
    with st.form(form_key):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Title", value=nullable_text(item.get("title")))
            company_name = st.text_input(
                "Company",
                value=nullable_text(item.get("company_name")),
            )
            employment_type = st.text_input(
                "Employment type",
                value=nullable_text(item.get("employment_type")),
            )
            location = st.text_input("Location", value=nullable_text(item.get("location")))
        with col2:
            location_type = st.text_input(
                "Location type",
                value=nullable_text(item.get("location_type")),
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
        col1, col2 = st.columns(2)
        with col1:
            school = st.text_input("School", value=nullable_text(item.get("school")))
            degree = st.text_input("Degree", value=nullable_text(item.get("degree")))
            field_of_study = st.text_input(
                "Field of study",
                value=nullable_text(item.get("field_of_study")),
            )
        with col2:
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

