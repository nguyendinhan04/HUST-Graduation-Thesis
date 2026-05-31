from __future__ import annotations

from typing import Any

import streamlit as st

from frontend_app.api_client import ApiError, refresh_profile
from frontend_app.auth_views import render_auth_page
from frontend_app.dialogs import render_active_dialog
from frontend_app.formatting import show_api_error
from frontend_app.management_views import (
    render_education_management_page,
    render_experience_management_page,
    render_skill_management_page,
)
from frontend_app.profile_views import (
    render_educations,
    render_experiences,
    render_profile_actions,
    render_profile_summary,
    render_standalone_skills,
)
from frontend_app.sidebar import sidebar
from frontend_app.state import init_session_state
from frontend_app.styles import inject_linkedin_styles


def render_profile_page() -> None:
    if st.session_state.get("profile") is None:
        try:
            refresh_profile()
        except ApiError as exc:
            show_api_error("Could not load profile", exc)
            return

    profile = st.session_state["profile"]
    current_page = st.session_state.get("current_page", "profile")
    if current_page == "experiences":
        render_experience_management_page(profile)
        render_active_dialog(profile)
        return
    if current_page == "educations":
        render_education_management_page(profile)
        render_active_dialog(profile)
        return
    if current_page == "skills":
        render_skill_management_page(profile)
        render_active_dialog(profile)
        return

    render_profile_summary(profile)
    render_profile_actions()
    render_experiences(profile)
    render_educations(profile)
    render_standalone_skills(profile)
    render_active_dialog(profile)



def main() -> None:
    st.set_page_config(
        page_title="Employee Profile",
        page_icon="E",
        layout="wide",
    )
    init_session_state()
    inject_linkedin_styles()
    sidebar()

    if st.session_state.get("access_token"):
        render_profile_page()
    else:
        render_auth_page()

