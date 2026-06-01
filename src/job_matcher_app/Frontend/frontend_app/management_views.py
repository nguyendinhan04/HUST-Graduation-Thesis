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


def _skill_name(skill: dict[str, Any]) -> str:
    return skill.get("skill_name") or "Unnamed skill"


def _skill_key(skill_name: str) -> str:
    return skill_name.strip().lower()


def _skill_source_markup(source: dict[str, str]) -> str:
    return (
        '<div class="linkedin-skill-source">'
        f'<div class="skill-source-logo">{escape(source["logo"])}</div>'
        f'<div class="skill-source-text">{html_or_empty(source["label"])}</div>'
        "</div>"
    )


def _collect_linkedin_skills(profile: dict[str, Any]) -> list[dict[str, Any]]:
    skill_map: dict[str, dict[str, Any]] = {}

    def ensure_skill(skill: dict[str, Any]) -> dict[str, Any]:
        name = _skill_name(skill)
        key = _skill_key(name)
        if key not in skill_map:
            skill_map[key] = {
                "skill_id": skill.get("skill_id"),
                "skill_name": name,
                "standalone_skill_id": None,
                "sources": [],
            }
        return skill_map[key]

    def add_source(skill: dict[str, Any], label: str, logo: str) -> None:
        item = ensure_skill(skill)
        source = {"label": label, "logo": logo}
        if source not in item["sources"]:
            item["sources"].append(source)

    for skill in profile.get("skills") or []:
        item = ensure_skill(skill)
        item["standalone_skill_id"] = skill.get("skill_id")

    for experience in profile.get("experiences") or []:
        title = experience.get("title") or "Experience"
        company = experience.get("company_name") or "Company"
        label = f"{title} at {company}"
        logo = initials(company, "CO")
        for skill in experience.get("skills") or []:
            add_source(skill, label, logo)

    for education in profile.get("educations") or []:
        school = education.get("school") or "Education"
        label = school
        logo = initials(school, "ED")
        for skill in education.get("skills") or []:
            add_source(skill, label, logo)

    for item in skill_map.values():
        if item.get("standalone_skill_id") and not item["sources"]:
            item["sources"].append({"label": "Added to profile", "logo": "IN"})

    return sorted(skill_map.values(), key=lambda item: item["skill_name"].lower())


def render_management_header(title: str, add_dialog: str) -> None:
    with st.container(border=True, key=f"management-{title.lower()}-header-card"):
        back_col, title_col, add_col = st.columns([0.65, 8.8, 0.55], gap="small")
        if back_col.button("←", key=f"back_{title}", help="Back to profile"):
            navigate_to("profile")
            st.rerun()
        title_col.markdown(f'<div class="section-title">{escape(title)}</div>', unsafe_allow_html=True)
        if add_col.button("+", key=f"add_from_{title}", help=f"Add {title.lower()}"):
            open_dialog(add_dialog)


def _management_entity_markup(
    *,
    logo: str,
    title: str,
    subtitle: str,
    meta: str,
    description: Any,
    skill_summary: str,
) -> str:
    entity_html = [
        f"""
        <div class="entity-row management-entity-row">
            <div class="entity-logo">{escape(logo)}</div>
            <div>
                <div class="entity-title">{html_or_empty(title)}</div>
                <div class="entity-subtitle">{html_or_empty(subtitle)}</div>
                <div class="entity-meta">{html_or_empty(meta)}</div>
                <div class="entity-desc">{html_or_empty(description)}</div>
        """.strip()
    ]
    if skill_summary:
        entity_html.append(f'<div class="skill-line">{html_or_empty(skill_summary)}</div>')
    else:
        entity_html.append('<div class="skill-line-spacer"></div>')
    entity_html.append("</div></div>")
    return "\n".join(entity_html)



def render_experience_management_page(profile: dict[str, Any]) -> None:
    render_management_header("Experience", "add_experience")
    experiences = profile.get("experiences") or []
    if not experiences:
        with st.container(border=True, key="management-experiences-empty-card"):
            st.markdown('<div class="empty-state">No experience yet.</div>', unsafe_allow_html=True)
        return

    with st.container(border=True, key="management-experiences-list-card"):
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
            meta = html_or_empty(format_date_range(item.get("start_date"), item.get("end_date")))
            if location:
                meta += f" · {html_or_empty(location)}"
            body_col, edit_col = st.columns([9.4, 0.6], gap="small")
            body_col.markdown(
                _management_entity_markup(
                    logo=initials(company, "CO"),
                    title=title,
                    subtitle=f"{company} · {item.get('employment_type') or 'No employment type yet'}",
                    meta=meta,
                    description=item.get("description"),
                    skill_summary=skill_summary,
                ),
                unsafe_allow_html=True,
            )
            if edit_col.button("✎", key=f"edit_experience_page_{item['experience_id']}", help="Edit experience"):
                open_dialog("edit_experience", item["experience_id"])
            if index < len(experiences):
                st.markdown('<div class="management-divider"></div>', unsafe_allow_html=True)



def render_education_management_page(profile: dict[str, Any]) -> None:
    render_management_header("Education", "add_education")
    educations = profile.get("educations") or []
    if not educations:
        with st.container(border=True, key="management-educations-empty-card"):
            st.markdown('<div class="empty-state">No education yet.</div>', unsafe_allow_html=True)
        return

    with st.container(border=True, key="management-educations-list-card"):
        for index, item in enumerate(educations, start=1):
            school = item.get("school") or f"Education #{index}"
            degree = item.get("degree") or "No degree yet"
            skill_summary = summarize_skills(item.get("skills"))
            body_col, edit_col = st.columns([9.4, 0.6], gap="small")
            body_col.markdown(
                _management_entity_markup(
                    logo=initials(school, "ED"),
                    title=school,
                    subtitle=f"{degree}, {item.get('field_of_study') or 'No field of study yet'}",
                    meta=format_date_range(item.get("start_date"), item.get("end_date")),
                    description=item.get("description"),
                    skill_summary=skill_summary,
                ),
                unsafe_allow_html=True,
            )
            if edit_col.button("✎", key=f"edit_education_page_{item['education_id']}", help="Edit education"):
                open_dialog("edit_education", item["education_id"])
            if index < len(educations):
                st.markdown('<div class="management-divider"></div>', unsafe_allow_html=True)



def render_skill_management_page(profile: dict[str, Any]) -> None:
    render_management_header("Skills", "add_skill")
    skills = _collect_linkedin_skills(profile)
    if not skills:
        with st.container(border=True, key="management-skills-empty-card"):
            st.markdown('<div class="empty-state">No skills yet.</div>', unsafe_allow_html=True)
        return

    with st.container(border=True, key="management-skills-list-card"):
        st.markdown(
            """
            <div class="skills-filter-row">
                <span class="skill-filter-pill active">All</span>
                <span class="skill-filter-pill">Industry Knowledge</span>
                <span class="skill-filter-pill">Tools &amp; Technologies</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        for skill in skills:
            name_col, action_col = st.columns([9.3, 0.7], gap="small")
            sources = skill.get("sources") or []
            source_markup = "".join(
                _skill_source_markup(source) for source in sources[:2]
            )
            if len(sources) > 2:
                source_markup += (
                    '<div class="linkedin-skill-source">'
                    '<div class="skill-source-logo">+</div>'
                    f'<div class="skill-source-text">Also shown in {len(sources) - 2} other sections</div>'
                    "</div>"
                )
            name_col.markdown(
                f"""
                <div class="linkedin-skill-row">
                    <div class="linkedin-skill-name">{html_or_empty(skill.get("skill_name"), "Unnamed skill")}</div>
                    {source_markup}
                </div>
                """,
                unsafe_allow_html=True,
            )
            standalone_skill_id = skill.get("standalone_skill_id")
            delete_clicked = action_col.button(
                "×",
                key=f"delete_skill_page_{skill['skill_id']}",
                help="Delete standalone skill" if standalone_skill_id else "Skill comes from experience or education",
                disabled=standalone_skill_id is None,
            )
            if delete_clicked and standalone_skill_id is not None:
                try:
                    with form_loading("Deleting skill..."):
                        delete_skill(standalone_skill_id)
                        refresh_profile()
                    st.success("Skill deleted.")
                    st.rerun()
                except ApiError as exc:
                    show_api_error("Could not delete skill", exc)

