from __future__ import annotations

from datetime import date
from html import escape
from typing import Any

import streamlit as st

from frontend_app.formatting import (
    clean_payload,
    date_to_api,
    html_or_empty,
    nullable_text,
    parse_iso_date,
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
    marker_col, _, no_col, discard_col = st.columns([0.01, 2.65, 1.8, 1.8], gap="medium")
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


def _initial_skill_names(skills: list[dict[str, Any]] | None) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for skill in skills or []:
        name = nullable_text(skill.get("skill_name")).strip()
        key = name.lower()
        if name and key not in seen:
            names.append(name)
            seen.add(key)
    return names


def _skill_items_key(form_key: str) -> str:
    return f"{form_key}_skill_items"


def _render_skills_editor(form_key: str, item: dict[str, Any]) -> list[str]:
    items_key = _skill_items_key(form_key)
    adding_key = f"{form_key}_skill_adding"
    draft_key = f"{form_key}_skill_draft"
    if items_key not in st.session_state:
        st.session_state[items_key] = _initial_skill_names(item.get("skills"))
    st.session_state.setdefault(adding_key, False)

    st.markdown(
        """
        <div class="skills-editor-header">
            <div class="skills-editor-title">Skills</div>
            <div class="skills-editor-copy">
                We recommend adding your top 5 used in this role. They'll also appear in your Skills section.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    skill_items = st.session_state[items_key]
    for index, skill_name in enumerate(list(skill_items)):
        remove_col, name_col, handle_col = st.columns([0.45, 8.7, 0.45], gap="small")
        if remove_col.button(
            "×",
            key=f"{form_key}_skill_remove_{index}",
            help=f"Remove {skill_name}",
        ):
            skill_items.pop(index)
            st.rerun()
        name_col.markdown(
            f'<div class="skills-editor-item-name">{html_or_empty(skill_name)}</div>',
            unsafe_allow_html=True,
        )
        handle_col.markdown('<div class="skills-editor-handle">&#9776;</div>', unsafe_allow_html=True)

    if st.session_state[adding_key]:
        input_col, add_col, cancel_col = st.columns([6.2, 1.3, 1.3], gap="small")
        new_skill = input_col.text_input(
            "New skill",
            key=draft_key,
            label_visibility="collapsed",
            placeholder="Skill",
        )
        if add_col.button("Add", key=f"{form_key}_skill_add_confirm", use_container_width=True):
            normalized_skill = new_skill.strip()
            existing_keys = {name.lower() for name in skill_items}
            if normalized_skill and normalized_skill.lower() not in existing_keys:
                skill_items.append(normalized_skill)
            st.session_state[draft_key] = ""
            st.session_state[adding_key] = False
            st.rerun()
        if cancel_col.button("Cancel", key=f"{form_key}_skill_add_cancel", use_container_width=True):
            st.session_state[draft_key] = ""
            st.session_state[adding_key] = False
            st.rerun()
    else:
        add_skill_col, _ = st.columns([1.2, 7.8])
        if add_skill_col.button("Add skill", key=f"{form_key}_skill_add", help="Add skill"):
            st.session_state[adding_key] = True
            st.rerun()

    return list(skill_items)



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
    skills = _render_skills_editor(form_key, item)
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
            "skills": skills,
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
    school = st.text_input(
        "School",
        value=nullable_text(item.get("school")),
        key=f"{form_key}_school",
    )
    degree = st.text_input(
        "Degree",
        value=nullable_text(item.get("degree")),
        key=f"{form_key}_degree",
    )
    field_of_study = st.text_input(
        "Field of study",
        value=nullable_text(item.get("field_of_study")),
        key=f"{form_key}_field_of_study",
    )
    start_date = st.date_input(
        "Start date",
        value=parse_iso_date(item.get("start_date")) or date.today(),
        key=f"{form_key}_start_date",
    )
    currently_studying_here = st.checkbox(
        "Currently studying here",
        value=item.get("end_date") is None,
        key=f"{form_key}_currently_studying_here",
    )
    if currently_studying_here:
        end_date = None
        st.caption("End date will be shown as Now.")
    else:
        end_date = st.date_input(
            "End date",
            value=parse_iso_date(item.get("end_date")) or date.today(),
            key=f"{form_key}_end_date",
        )
    skills = _render_skills_editor(form_key, item)
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
            "school": school,
            "degree": degree,
            "field_of_study": field_of_study,
            "description": description,
            "start_date": date_to_api(start_date),
            "end_date": date_to_api(end_date),
            "skills": skills,
        }
    )
    action = "delete" if delete_submitted else "save" if save_submitted else None
    return payload, action

