from __future__ import annotations

import streamlit as st

from frontend_app.api_client import ApiError, refresh_profile
from frontend_app.config import DEFAULT_API_BASE_URL
from frontend_app.formatting import show_api_error
from frontend_app.loading import form_loading
from frontend_app.state import api_base_url, logout


def sidebar() -> None:
    with st.sidebar:
        st.header("Settings")
        api_url = st.text_input("Backend API", value=api_base_url())
        normalized_url = api_url.strip().rstrip("/") or DEFAULT_API_BASE_URL
        if normalized_url != st.session_state["api_base_url"]:
            st.session_state["api_base_url"] = normalized_url
            st.session_state["profile"] = None

        if st.session_state.get("access_token"):
            profile = st.session_state.get("profile") or {}
            st.divider()
            st.caption("Signed in")
            st.write(profile.get("email", "Employee"))
            if st.button("Refresh profile", use_container_width=True):
                try:
                    with form_loading("Refreshing profile..."):
                        refresh_profile()
                    st.success("Profile refreshed.")
                except ApiError as exc:
                    show_api_error("Could not load profile", exc)
            if st.button("Sign out", use_container_width=True):
                logout()
                st.rerun()

