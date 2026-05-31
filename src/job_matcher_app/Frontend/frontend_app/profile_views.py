from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from frontend_app.api_client import ApiError, refresh_profile
from frontend_app.formatting import (
    format_date_range,
    html_or_empty,
    initials,
    nullable_text,
    show_api_error,
    summarize_skills,
)
from frontend_app.state import navigate_to, open_dialog


def render_skill_chips(skills: list[dict[str, Any]] | None) -> None:
    if not skills:
        st.caption("No skills yet.")
        return

    names = [skill.get("skill_name", "") for skill in skills if skill.get("skill_name")]
    st.markdown(" ".join(f"`{name}`" for name in names))



def render_profile_summary(profile: dict[str, Any]) -> None:
    employee = profile.get("employee_profile") or {}
    avatar_url = nullable_text(profile.get("avatar_url")).strip()
    if avatar_url:
        avatar_markup = (
            f'<img class="profile-avatar" src="{escape(avatar_url)}" '
            f'alt="{html_or_empty(profile.get("full_name"), "Employee")}">'
        )
    else:
        avatar_markup = (
            f'<div class="profile-avatar-placeholder">'
            f'{escape(initials(profile.get("full_name"), "E"))}</div>'
        )

    summary = employee.get("summary") or "No profile summary yet."
    st.markdown(
        f"""
        <div class="linkedin-card">
            <div class="profile-cover"></div>
            <div class="profile-body">
                {avatar_markup}
                <div class="profile-name">{html_or_empty(profile.get("full_name"), "No name yet")}</div>
                <div class="profile-headline">{html_or_empty(employee.get("headline"), "No headline yet")}</div>
                <div class="muted">{html_or_empty(employee.get("current_location"), "No location yet")} · {html_or_empty(profile.get("email"))}</div>
                <div class="muted">{html_or_empty(profile.get("phone"), "No phone yet")} · {employee.get("years_of_experience") or 0} years of experience</div>
                <div class="entity-desc">{html_or_empty(summary)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_profile_actions() -> None:
    spacer, edit_col, refresh_col = st.columns([9, 0.55, 0.55], gap="small")
    if edit_col.button("✎", key="open_profile_dialog", help="Edit profile"):
        open_dialog("profile")
    if refresh_col.button("↻", key="refresh_profile_top", help="Refresh profile"):
        try:
            refresh_profile()
            st.success("Profile refreshed.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Could not load profile", exc)



def render_experience_item(item: dict[str, Any]) -> None:
    title = item.get("title") or "No title yet"
    company = item.get("company_name") or "No company yet"
    employment = item.get("employment_type") or "No employment type yet"
    location_bits = [
        value
        for value in [item.get("location"), item.get("location_type")]
        if value
    ]
    location = " · ".join(location_bits)
    date_range = format_date_range(item.get("start_date"), item.get("end_date"))
    description = item.get("description") or ""
    skill_summary = summarize_skills(item.get("skills"))
    skill_markup = (
        f'<div class="skill-line">{html_or_empty(skill_summary)}</div>'
        if skill_summary
        else ""
    )

    st.markdown(
        f"""
        <div class="entity-row">
            <div class="entity-logo">{escape(initials(company, "CO"))}</div>
            <div>
                <div class="entity-title">{html_or_empty(title)}</div>
                <div class="entity-subtitle">{html_or_empty(company)} · {html_or_empty(employment)}</div>
                <div class="entity-meta">{html_or_empty(date_range)}{(" · " + html_or_empty(location)) if location else ""}</div>
                <div class="entity-desc">{html_or_empty(description)}</div>
                {skill_markup}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_education_item(item: dict[str, Any]) -> None:
    school = item.get("school") or "No school yet"
    degree = item.get("degree") or "No degree yet"
    field_of_study = item.get("field_of_study") or "No field of study yet"
    date_range = format_date_range(item.get("start_date"), item.get("end_date"))
    description = item.get("description") or ""
    skill_summary = summarize_skills(item.get("skills"))
    skill_markup = (
        f'<div class="skill-line">{html_or_empty(skill_summary)}</div>'
        if skill_summary
        else ""
    )

    st.markdown(
        f"""
        <div class="entity-row">
            <div class="entity-logo">{escape(initials(school, "ED"))}</div>
            <div>
                <div class="entity-title">{html_or_empty(school)}</div>
                <div class="entity-subtitle">{html_or_empty(degree)}, {html_or_empty(field_of_study)}</div>
                <div class="entity-meta">{html_or_empty(date_range)}</div>
                <div class="entity-desc">{html_or_empty(description)}</div>
                {skill_markup}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_experiences(profile: dict[str, Any]) -> None:
    experiences = profile.get("experiences") or []
    with st.container(border=True):
        header_left, add_col, edit_col = st.columns([9, 0.55, 0.55], gap="small")
        header_left.markdown('<div class="section-title">Experience</div>', unsafe_allow_html=True)
        if add_col.button("+", key="add_experience", help="Add experience"):
            open_dialog("add_experience")
        if edit_col.button("✎", key="manage_experiences", help="Edit experience"):
            navigate_to("experiences")
            st.rerun()

        if not experiences:
            st.markdown('<div class="empty-state">No experience yet.</div>', unsafe_allow_html=True)
            return

        for item in experiences:
            render_experience_item(item)



def render_educations(profile: dict[str, Any]) -> None:
    educations = profile.get("educations") or []
    with st.container(border=True):
        header_left, add_col, edit_col = st.columns([9, 0.55, 0.55], gap="small")
        header_left.markdown('<div class="section-title">Education</div>', unsafe_allow_html=True)
        if add_col.button("+", key="add_education", help="Add education"):
            open_dialog("add_education")
        if edit_col.button("✎", key="manage_educations", help="Edit education"):
            navigate_to("educations")
            st.rerun()

        if not educations:
            st.markdown('<div class="empty-state">No education yet.</div>', unsafe_allow_html=True)
            return

        for item in educations:
            render_education_item(item)



def render_standalone_skills(profile: dict[str, Any]) -> None:
    skills = profile.get("skills") or []
    with st.container(border=True):
        header_left, add_col, edit_col = st.columns([9, 0.55, 0.55], gap="small")
        header_left.markdown(
            f'<div class="section-title">Skills ({len(skills)})</div>',
            unsafe_allow_html=True,
        )
        if add_col.button("+", key="add_skill", help="Add skill"):
            open_dialog("add_skill")
        if edit_col.button("✎", key="manage_skills", help="Edit skills"):
            navigate_to("skills")
            st.rerun()

        if not skills:
            st.markdown('<div class="empty-state">No standalone skills yet.</div>', unsafe_allow_html=True)
            return

        visible_skills = skills[:5]
        for skill in visible_skills:
            st.markdown(
                f'<div class="skill-row">{html_or_empty(skill.get("skill_name"))}</div>',
                unsafe_allow_html=True,
            )

        if len(skills) > 5:
            st.caption(f"Show all {len(skills)} skills")

