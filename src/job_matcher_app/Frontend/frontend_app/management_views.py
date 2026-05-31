from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from frontend_app.api_client import ApiError, delete_skill, refresh_profile
from frontend_app.formatting import (
    format_date_range,
    html_or_empty,
    initials,
    show_api_error,
    summarize_skills,
)
from frontend_app.loading import form_loading
from frontend_app.state import navigate_to, open_dialog


def render_management_header(title: str, add_dialog: str) -> None:
    with st.container(border=True):
        back_col, title_col, add_col = st.columns([0.65, 8.8, 0.55], gap="small")
        if back_col.button("←", key=f"back_{title}", help="Back to profile"):
            navigate_to("profile")
            st.rerun()
        title_col.markdown(f'<div class="section-title">{escape(title)}</div>', unsafe_allow_html=True)
        if add_col.button("+", key=f"add_from_{title}", help=f"Add {title.lower()}"):
            open_dialog(add_dialog)



def render_experience_management_page(profile: dict[str, Any]) -> None:
    render_management_header("Experience", "add_experience")
    experiences = profile.get("experiences") or []
    if not experiences:
        with st.container(border=True):
            st.markdown('<div class="empty-state">No experience yet.</div>', unsafe_allow_html=True)
        return

    with st.container(border=True):
        for index, item in enumerate(experiences, start=1):
            title = item.get("title") or f"Experience #{index}"
            company = item.get("company_name") or "No company yet"
            location_bits = [
                value
                for value in [item.get("location"), item.get("location_type")]
                if value
            ]
            location = " · ".join(location_bits)
            skill_summary = summarize_skills(item.get("skills"))
            logo_col, body_col, edit_col = st.columns([0.8, 8.6, 0.6], gap="small")
            logo_col.markdown(
                f'<div class="entity-logo">{escape(initials(company, "CO"))}</div>',
                unsafe_allow_html=True,
            )
            body_col.markdown(
                f"""
                <div class="entity-title">{html_or_empty(title)}</div>
                <div class="entity-subtitle">{html_or_empty(company)} · {html_or_empty(item.get("employment_type"), "No employment type yet")}</div>
                <div class="entity-meta">{html_or_empty(format_date_range(item.get("start_date"), item.get("end_date")))}{(" · " + html_or_empty(location)) if location else ""}</div>
                <div class="entity-desc">{html_or_empty(item.get("description"))}</div>
                {f'<div class="skill-line">{html_or_empty(skill_summary)}</div>' if skill_summary else ""}
                """,
                unsafe_allow_html=True,
            )
            if edit_col.button("✎", key=f"edit_experience_page_{item['experience_id']}", help="Edit experience"):
                open_dialog("edit_experience", item["experience_id"])
            if index < len(experiences):
                st.divider()



def render_education_management_page(profile: dict[str, Any]) -> None:
    render_management_header("Education", "add_education")
    educations = profile.get("educations") or []
    if not educations:
        with st.container(border=True):
            st.markdown('<div class="empty-state">No education yet.</div>', unsafe_allow_html=True)
        return

    with st.container(border=True):
        for index, item in enumerate(educations, start=1):
            school = item.get("school") or f"Education #{index}"
            degree = item.get("degree") or "No degree yet"
            skill_summary = summarize_skills(item.get("skills"))
            logo_col, body_col, edit_col = st.columns([0.8, 8.6, 0.6], gap="small")
            logo_col.markdown(
                f'<div class="entity-logo">{escape(initials(school, "ED"))}</div>',
                unsafe_allow_html=True,
            )
            body_col.markdown(
                f"""
                <div class="entity-title">{html_or_empty(school)}</div>
                <div class="entity-subtitle">{html_or_empty(degree)}, {html_or_empty(item.get("field_of_study"), "No field of study yet")}</div>
                <div class="entity-meta">{html_or_empty(format_date_range(item.get("start_date"), item.get("end_date")))}</div>
                <div class="entity-desc">{html_or_empty(item.get("description"))}</div>
                {f'<div class="skill-line">{html_or_empty(skill_summary)}</div>' if skill_summary else ""}
                """,
                unsafe_allow_html=True,
            )
            if edit_col.button("✎", key=f"edit_education_page_{item['education_id']}", help="Edit education"):
                open_dialog("edit_education", item["education_id"])
            if index < len(educations):
                st.divider()



def render_skill_management_page(profile: dict[str, Any]) -> None:
    render_management_header("Skills", "add_skill")
    skills = profile.get("skills") or []
    if not skills:
        with st.container(border=True):
            st.markdown('<div class="empty-state">No standalone skills yet.</div>', unsafe_allow_html=True)
        return

    with st.container(border=True):
        for index, skill in enumerate(skills, start=1):
            name_col, delete_col = st.columns([9.3, 0.7], gap="small")
            name_col.markdown(
                f'<div class="skill-row">{html_or_empty(skill.get("skill_name"), "Unnamed skill")}</div>',
                unsafe_allow_html=True,
            )
            if delete_col.button("×", key=f"delete_skill_page_{skill['skill_id']}", help="Delete skill"):
                try:
                    with form_loading("Deleting skill..."):
                        delete_skill(skill["skill_id"])
                        refresh_profile()
                    st.success("Skill deleted.")
                    st.rerun()
                except ApiError as exc:
                    show_api_error("Could not delete skill", exc)
            if index < len(skills):
                st.divider()

