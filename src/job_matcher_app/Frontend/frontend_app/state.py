from __future__ import annotations

import os

import streamlit as st

from frontend_app.config import DEFAULT_API_BASE_URL


def init_session_state() -> None:
    st.session_state.setdefault(
        "api_base_url",
        os.getenv("API_BASE_URL", DEFAULT_API_BASE_URL).rstrip("/"),
    )
    st.session_state.setdefault("access_token", None)
    st.session_state.setdefault("token_type", "bearer")
    st.session_state.setdefault("profile", None)
    st.session_state.setdefault("active_dialog", None)
    st.session_state.setdefault("active_item_id", None)
    st.session_state.setdefault("current_page", "profile")



def api_base_url() -> str:
    return st.session_state["api_base_url"].rstrip("/")



def auth_headers() -> dict[str, str]:
    token = st.session_state.get("access_token")
    if not token:
        return {}
    token_type = st.session_state.get("token_type") or "bearer"
    return {"Authorization": f"{token_type.capitalize()} {token}"}



def logout() -> None:
    st.session_state["access_token"] = None
    st.session_state["token_type"] = "bearer"
    st.session_state["profile"] = None
    st.session_state["active_dialog"] = None
    st.session_state["active_item_id"] = None
    st.session_state["current_page"] = "profile"



def open_dialog(name: str, item_id: int | None = None) -> None:
    st.session_state["active_dialog"] = name
    st.session_state["active_item_id"] = item_id



def close_dialog() -> None:
    st.session_state["active_dialog"] = None
    st.session_state["active_item_id"] = None



def navigate_to(page: str) -> None:
    st.session_state["current_page"] = page
    close_dialog()

