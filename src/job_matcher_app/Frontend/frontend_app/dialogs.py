from __future__ import annotations

from typing import Any

import streamlit as st

from frontend_app.api_client import (
    ApiError,
    add_skill,
    create_education,
    create_experience,
    delete_education,
    delete_experience,
    delete_skill,
    refresh_profile,
    update_education,
    update_experience,
    update_profile,
)
from frontend_app.formatting import show_api_error
from frontend_app.forms import (
    education_payload_form,
    experience_payload_form,
    profile_payload_form,
    render_dialog_header,
    render_discard_confirmation,
)
from frontend_app.loading import form_loading
from frontend_app.state import clear_active_dialog_draft, close_dialog


# Streamlit requires a non-empty dialog title even when the native header is hidden.
DIALOG_NATIVE_TITLE = "\u200b"


def _skill_names_with_added(
    skills: list[dict[str, Any]] | None,
    skill_name: str,
) -> tuple[list[str], bool]:
    names = [
        str(skill.get("skill_name") or "").strip()
        for skill in skills or []
        if str(skill.get("skill_name") or "").strip()
    ]
    existing_keys = {name.lower() for name in names}
    normalized_skill_name = skill_name.strip()
    if normalized_skill_name.lower() in existing_keys:
        return names, False
    return [*names, normalized_skill_name], True


def _experience_label(experience: dict[str, Any]) -> str:
    title = experience.get("title") or "Experience"
    company = experience.get("company_name") or "Company"
    return f"{title} at {company}"


def _education_label(education: dict[str, Any]) -> str:
    return education.get("school") or "Education"


@st.dialog(DIALOG_NATIVE_TITLE, dismissible=False)
def profile_dialog(profile: dict[str, Any]) -> None:
    render_dialog_header("Edit profile", "profile_dialog")

    payload, action = profile_payload_form("profile_edit_form", profile)
    if action == "save":
        try:
            with form_loading("Saving profile..."):
                update_profile(payload)
                refresh_profile()
            close_dialog()
            st.success("Profile updated.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Could not update profile", exc)
    render_discard_confirmation("profile_dialog")



@st.dialog(DIALOG_NATIVE_TITLE, dismissible=False)
def add_experience_dialog() -> None:
    render_dialog_header("Add experience", "add_experience_dialog")

    payload, action = experience_payload_form("create_experience_form")
    if action == "save":
        try:
            with form_loading("Saving experience..."):
                create_experience(payload)
                refresh_profile()
            close_dialog()
            st.success("Experience added.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Could not add experience", exc)
    render_discard_confirmation("add_experience_dialog")



@st.dialog(DIALOG_NATIVE_TITLE, dismissible=False)
def edit_experience_dialog(profile: dict[str, Any]) -> None:
    render_dialog_header("Edit experience", "edit_experience_dialog")

    experiences = profile.get("experiences") or []
    experience_id = st.session_state.get("active_item_id")
    item = next(
        (
            experience
            for experience in experiences
            if experience.get("experience_id") == experience_id
        ),
        None,
    )
    if item is None:
        st.info("Experience not found.")
        return

    payload, action = experience_payload_form(
        f"edit_experience_form_{item['experience_id']}",
        item,
        allow_delete=True,
    )
    if action == "delete":
        try:
            with form_loading("Deleting experience..."):
                delete_experience(item["experience_id"])
                refresh_profile()
            close_dialog()
            st.success("Experience deleted.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Could not delete experience", exc)
    elif action == "save":
        try:
            with form_loading("Saving experience..."):
                update_experience(item["experience_id"], payload)
                refresh_profile()
            close_dialog()
            st.success("Experience updated.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Could not update experience", exc)
    render_discard_confirmation("edit_experience_dialog")



@st.dialog(DIALOG_NATIVE_TITLE, dismissible=False)
def add_education_dialog() -> None:
    render_dialog_header("Add education", "add_education_dialog")

    payload, action = education_payload_form("create_education_form")
    if action == "save":
        try:
            with form_loading("Saving education..."):
                create_education(payload)
                refresh_profile()
            close_dialog()
            st.success("Education added.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Could not add education", exc)
    render_discard_confirmation("add_education_dialog")



@st.dialog(DIALOG_NATIVE_TITLE, dismissible=False)
def edit_education_dialog(profile: dict[str, Any]) -> None:
    render_dialog_header("Edit education", "edit_education_dialog")

    educations = profile.get("educations") or []
    education_id = st.session_state.get("active_item_id")
    item = next(
        (
            education
            for education in educations
            if education.get("education_id") == education_id
        ),
        None,
    )
    if item is None:
        st.info("Education not found.")
        return

    payload, action = education_payload_form(
        f"edit_education_form_{item['education_id']}",
        item,
        allow_delete=True,
    )
    if action == "delete":
        try:
            with form_loading("Deleting education..."):
                delete_education(item["education_id"])
                refresh_profile()
            close_dialog()
            st.success("Education deleted.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Could not delete education", exc)
    elif action == "save":
        try:
            with form_loading("Saving education..."):
                update_education(item["education_id"], payload)
                refresh_profile()
            close_dialog()
            st.success("Education updated.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Could not update education", exc)
    render_discard_confirmation("edit_education_dialog")



@st.dialog(DIALOG_NATIVE_TITLE, dismissible=False)
def add_skill_dialog(profile: dict[str, Any]) -> None:
    render_dialog_header("Add skill", "add_skill_dialog")

    with st.form("add_skill_form"):
        skill_name = st.text_input("Skill*", key="add_skill_form_skill_name")
        st.markdown(
            """
            <div class="add-skill-context">
                <div class="add-skill-context-title">Show us where you used this skill</div>
                <div class="add-skill-context-copy">
                    Search at least one item to show where you used this skill.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        selected_experience_ids = []
        experiences = profile.get("experiences") or []
        st.markdown('<div class="add-skill-group-label">Experience</div>', unsafe_allow_html=True)
        if experiences:
            for experience in experiences:
                experience_id = experience.get("experience_id")
                if experience_id is None:
                    continue
                checked = st.checkbox(
                    _experience_label(experience),
                    key=f"add_skill_form_experience_{experience_id}",
                )
                if checked:
                    selected_experience_ids.append(experience_id)
        else:
            st.caption("No experience yet.")

        selected_education_ids = []
        educations = profile.get("educations") or []
        st.markdown('<div class="add-skill-group-label">Education</div>', unsafe_allow_html=True)
        if educations:
            for education in educations:
                education_id = education.get("education_id")
                if education_id is None:
                    continue
                checked = st.checkbox(
                    _education_label(education),
                    key=f"add_skill_form_education_{education_id}",
                )
                if checked:
                    selected_education_ids.append(education_id)
        else:
            st.caption("No education yet.")

        _, save_col = st.columns([5, 1.25])
        action = "save" if save_col.form_submit_button(
            "Save",
            type="primary",
            use_container_width=True,
        ) else None
    if action == "save":
        if not skill_name.strip():
            st.warning("Please enter a skill name.")
            return
        try:
            with form_loading("Saving skill..."):
                normalized_skill_name = skill_name.strip()
                if not selected_experience_ids and not selected_education_ids:
                    add_skill(normalized_skill_name)
                else:
                    experiences_by_id = {
                        experience.get("experience_id"): experience
                        for experience in profile.get("experiences") or []
                    }
                    for experience_id in selected_experience_ids:
                        experience = experiences_by_id.get(experience_id)
                        if experience is None:
                            continue
                        skill_names, added = _skill_names_with_added(
                            experience.get("skills"),
                            normalized_skill_name,
                        )
                        if added:
                            update_experience(experience_id, {"skills": skill_names})

                    educations_by_id = {
                        education.get("education_id"): education
                        for education in profile.get("educations") or []
                    }
                    for education_id in selected_education_ids:
                        education = educations_by_id.get(education_id)
                        if education is None:
                            continue
                        skill_names, added = _skill_names_with_added(
                            education.get("skills"),
                            normalized_skill_name,
                        )
                        if added:
                            update_education(education_id, {"skills": skill_names})

                refresh_profile()
            clear_active_dialog_draft()
            close_dialog()
            st.success("Skill added.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Could not add skill", exc)
    render_discard_confirmation("add_skill_dialog")



@st.dialog(DIALOG_NATIVE_TITLE, dismissible=False)
def manage_skills_dialog(profile: dict[str, Any]) -> None:
    render_dialog_header("Edit skills", "manage_skills_dialog")

    skills = profile.get("skills") or []
    if not skills:
        st.info("No standalone skills yet.")
        render_discard_confirmation("manage_skills_dialog")
        return

    for skill in skills:
        col1, col2 = st.columns([3, 1])
        col1.write(skill.get("skill_name") or "Unnamed skill")
        if col2.button(
            "Delete",
            key=f"delete_skill_{skill['skill_id']}",
            use_container_width=True,
        ):
            try:
                with form_loading("Deleting skill..."):
                    delete_skill(skill["skill_id"])
                    refresh_profile()
                close_dialog()
                st.success("Skill deleted.")
                st.rerun()
            except ApiError as exc:
                show_api_error("Could not delete skill", exc)
    render_discard_confirmation("manage_skills_dialog")



def render_active_dialog(profile: dict[str, Any]) -> None:
    active_dialog = st.session_state.get("active_dialog")

    if active_dialog == "profile":
        profile_dialog(profile)
    elif active_dialog == "add_experience":
        add_experience_dialog()
    elif active_dialog == "edit_experience":
        edit_experience_dialog(profile)
    elif active_dialog == "add_education":
        add_education_dialog()
    elif active_dialog == "edit_education":
        edit_education_dialog(profile)
    elif active_dialog == "add_skill":
        add_skill_dialog(profile)
    elif active_dialog == "manage_skills":
        manage_skills_dialog(profile)

