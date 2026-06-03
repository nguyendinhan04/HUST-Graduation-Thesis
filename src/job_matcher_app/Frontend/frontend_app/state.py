from __future__ import annotations

import os

import streamlit as st

from frontend_app.auth_persistence import request_persisted_auth_clear
from frontend_app.config import DEFAULT_API_BASE_URL


def init_session_state() -> None:
    st.session_state.setdefault(
        "api_base_url",
        os.getenv("API_BASE_URL", DEFAULT_API_BASE_URL).rstrip("/"),
    )
    st.session_state.setdefault("access_token", None)
    st.session_state.setdefault("token_type", "bearer")
    st.session_state.setdefault("user_role", None)
    st.session_state.setdefault("profile", None)
    st.session_state.setdefault("active_dialog", None)
    st.session_state.setdefault("active_item_id", None)
    st.session_state.setdefault("confirm_discard", False)
    st.session_state.setdefault("current_page", "profile")
    st.session_state.setdefault("selected_job_id", None)
    st.session_state.setdefault("selected_employer_job_id", None)
    st.session_state.setdefault("selected_job_return_page", "recommendations")



def api_base_url() -> str:
    return st.session_state["api_base_url"].rstrip("/")



def auth_headers() -> dict[str, str]:
    token = st.session_state.get("access_token")
    if not token:
        return {}
    token_type = st.session_state.get("token_type") or "bearer"
    return {"Authorization": f"{token_type.capitalize()} {token}"}



def logout() -> None:
    request_persisted_auth_clear()
    st.session_state["access_token"] = None
    st.session_state["token_type"] = "bearer"
    st.session_state["user_role"] = None
    st.session_state["profile"] = None
    st.session_state["active_dialog"] = None
    st.session_state["active_item_id"] = None
    st.session_state["confirm_discard"] = False
    st.session_state["current_page"] = "profile"
    st.session_state["selected_job_id"] = None
    st.session_state["selected_employer_job_id"] = None
    st.session_state["selected_job_return_page"] = "recommendations"
    _delete_state_keys_with_prefix("employer_jobs")
    _delete_state_keys_with_prefix("employer_job")
    _delete_state_keys_with_prefix("my_applications")



def open_dialog(name: str, item_id: int | None = None) -> None:
    st.session_state["active_dialog"] = name
    st.session_state["active_item_id"] = item_id
    st.session_state["confirm_discard"] = False



def close_dialog() -> None:
    st.session_state["active_dialog"] = None
    st.session_state["active_item_id"] = None
    st.session_state["confirm_discard"] = False



def _delete_state_keys_with_prefix(prefix: str) -> None:
    for key in list(st.session_state.keys()):
        if key.startswith(prefix):
            del st.session_state[key]



def clear_active_dialog_draft() -> None:
    active_dialog = st.session_state.get("active_dialog")
    active_item_id = st.session_state.get("active_item_id")

    if active_dialog == "add_experience":
        _delete_state_keys_with_prefix("create_experience_form_")
    elif active_dialog == "edit_experience" and active_item_id is not None:
        _delete_state_keys_with_prefix(f"edit_experience_form_{active_item_id}_")
    elif active_dialog == "add_education":
        _delete_state_keys_with_prefix("create_education_form_")
    elif active_dialog == "edit_education" and active_item_id is not None:
        _delete_state_keys_with_prefix(f"edit_education_form_{active_item_id}_")
    elif active_dialog == "profile":
        _delete_state_keys_with_prefix("profile_edit_form_")
    elif active_dialog == "add_skill":
        _delete_state_keys_with_prefix("add_skill_form_")
    elif active_dialog == "create_job":
        _delete_state_keys_with_prefix("employer_job_create_")
    elif active_dialog == "edit_job":
        _delete_state_keys_with_prefix("employer_job_edit_")



def request_discard_confirmation() -> None:
    st.session_state["confirm_discard"] = True



def cancel_discard_confirmation() -> None:
    st.session_state["confirm_discard"] = False



def navigate_to(page: str) -> None:
    st.session_state["current_page"] = page
    if page != "job_detail":
        st.session_state["selected_job_id"] = None
        st.session_state["selected_job_return_page"] = "recommendations"
    if page != "employer_job_detail":
        st.session_state["selected_employer_job_id"] = None
    close_dialog()


def navigate_to_job_detail(job_id: int, return_page: str = "recommendations") -> None:
    st.session_state["selected_job_id"] = job_id
    st.session_state["selected_job_return_page"] = return_page
    navigate_to("job_detail")


def navigate_to_employer_job_detail(job_id: int) -> None:
    st.session_state["selected_employer_job_id"] = job_id
    navigate_to("employer_job_detail")

