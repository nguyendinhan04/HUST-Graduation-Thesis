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
from frontend_app.state import close_dialog


@st.dialog("Edit profile")
def profile_dialog(profile: dict[str, Any]) -> None:
    render_dialog_header("Edit profile", "profile_dialog")
    if render_discard_confirmation("profile_dialog"):
        return

    payload, action = profile_payload_form("profile_edit_form", profile)
    if action == "save":
        try:
            update_profile(payload)
            refresh_profile()
            close_dialog()
            st.success("Profile updated.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Could not update profile", exc)



@st.dialog("Add experience")
def add_experience_dialog() -> None:
    render_dialog_header("Add experience", "add_experience_dialog")
    if render_discard_confirmation("add_experience_dialog"):
        return

    payload, action = experience_payload_form("create_experience_form")
    if action == "save":
        try:
            create_experience(payload)
            refresh_profile()
            close_dialog()
            st.success("Experience added.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Could not add experience", exc)



@st.dialog("Edit experience")
def edit_experience_dialog(profile: dict[str, Any]) -> None:
    render_dialog_header("Edit experience", "edit_experience_dialog")
    if render_discard_confirmation("edit_experience_dialog"):
        return

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
            delete_experience(item["experience_id"])
            refresh_profile()
            close_dialog()
            st.success("Experience deleted.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Could not delete experience", exc)
    elif action == "save":
        try:
            update_experience(item["experience_id"], payload)
            refresh_profile()
            close_dialog()
            st.success("Experience updated.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Could not update experience", exc)



@st.dialog("Add education")
def add_education_dialog() -> None:
    render_dialog_header("Add education", "add_education_dialog")
    if render_discard_confirmation("add_education_dialog"):
        return

    payload, action = education_payload_form("create_education_form")
    if action == "save":
        try:
            create_education(payload)
            refresh_profile()
            close_dialog()
            st.success("Education added.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Could not add education", exc)



@st.dialog("Edit education")
def edit_education_dialog(profile: dict[str, Any]) -> None:
    render_dialog_header("Edit education", "edit_education_dialog")
    if render_discard_confirmation("edit_education_dialog"):
        return

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
            delete_education(item["education_id"])
            refresh_profile()
            close_dialog()
            st.success("Education deleted.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Could not delete education", exc)
    elif action == "save":
        try:
            update_education(item["education_id"], payload)
            refresh_profile()
            close_dialog()
            st.success("Education updated.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Could not update education", exc)



@st.dialog("Add skill")
def add_skill_dialog() -> None:
    render_dialog_header("Add skill", "add_skill_dialog")
    if render_discard_confirmation("add_skill_dialog"):
        return

    with st.form("add_skill_form"):
        skill_name = st.text_input("Skill name")
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
            add_skill(skill_name.strip())
            refresh_profile()
            close_dialog()
            st.success("Skill added.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Could not add skill", exc)



@st.dialog("Edit skills")
def manage_skills_dialog(profile: dict[str, Any]) -> None:
    render_dialog_header("Edit skills", "manage_skills_dialog")
    if render_discard_confirmation("manage_skills_dialog"):
        return

    skills = profile.get("skills") or []
    if not skills:
        st.info("No standalone skills yet.")
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
                delete_skill(skill["skill_id"])
                refresh_profile()
                close_dialog()
                st.success("Skill deleted.")
                st.rerun()
            except ApiError as exc:
                show_api_error("Could not delete skill", exc)



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
        add_skill_dialog()
    elif active_dialog == "manage_skills":
        manage_skills_dialog(profile)

