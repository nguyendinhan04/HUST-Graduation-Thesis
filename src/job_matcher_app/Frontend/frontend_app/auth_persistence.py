from __future__ import annotations

import json
from typing import Any

import streamlit as st
from streamlit_js_eval import streamlit_js_eval


AUTH_STORAGE_KEYS = {
    "access_token": "job_matcher.access_token",
    "token_type": "job_matcher.token_type",
    "user_role": "job_matcher.user_role",
}

_CLEAR_REQUESTED_KEY = "_auth_storage_clear_requested"
_PERSISTED_SNAPSHOT_KEY = "_auth_storage_persisted_snapshot"
_REVISION_KEY = "_auth_storage_revision"


def request_persisted_auth_clear() -> None:
    st.session_state[_CLEAR_REQUESTED_KEY] = True
    st.session_state[_PERSISTED_SNAPSHOT_KEY] = None


def sync_auth_storage() -> None:
    if st.session_state.get(_CLEAR_REQUESTED_KEY):
        _clear_persisted_auth()
        st.session_state[_CLEAR_REQUESTED_KEY] = False
        return

    if st.session_state.get("access_token"):
        _persist_current_auth()
        return

    _restore_auth_from_storage()


def _next_revision() -> int:
    revision = int(st.session_state.get(_REVISION_KEY, 0)) + 1
    st.session_state[_REVISION_KEY] = revision
    return revision


def _persist_current_auth() -> None:
    payload = {
        "access_token": st.session_state.get("access_token"),
        "token_type": st.session_state.get("token_type") or "bearer",
        "user_role": st.session_state.get("user_role"),
    }
    if not payload["access_token"] or payload["user_role"] not in {"employee", "employer"}:
        return

    snapshot = json.dumps(payload, sort_keys=True)
    if st.session_state.get(_PERSISTED_SNAPSHOT_KEY) == snapshot:
        return

    statements = [
        f"localStorage.setItem({json.dumps(AUTH_STORAGE_KEYS[name])}, {json.dumps(str(value))});"
        for name, value in payload.items()
    ]
    streamlit_js_eval(
        js_expressions="\n".join(statements),
        key=f"auth_storage_save_{_next_revision()}",
    )
    st.session_state[_PERSISTED_SNAPSHOT_KEY] = snapshot


def _restore_auth_from_storage() -> None:
    read_expression = (
        "JSON.stringify({"
        f"access_token: localStorage.getItem({json.dumps(AUTH_STORAGE_KEYS['access_token'])}),"
        f"token_type: localStorage.getItem({json.dumps(AUTH_STORAGE_KEYS['token_type'])}),"
        f"user_role: localStorage.getItem({json.dumps(AUTH_STORAGE_KEYS['user_role'])})"
        "})"
    )
    raw_value = streamlit_js_eval(
        js_expressions=read_expression,
        key=f"auth_storage_read_{st.session_state.get(_REVISION_KEY, 0)}",
    )
    if not raw_value:
        return

    try:
        payload: dict[str, Any] = json.loads(raw_value)
    except (TypeError, json.JSONDecodeError):
        request_persisted_auth_clear()
        return

    access_token = payload.get("access_token")
    user_role = payload.get("user_role")
    if not access_token or user_role not in {"employee", "employer"}:
        return

    st.session_state["access_token"] = access_token
    st.session_state["token_type"] = payload.get("token_type") or "bearer"
    st.session_state["user_role"] = user_role
    st.session_state[_PERSISTED_SNAPSHOT_KEY] = json.dumps(
        {
            "access_token": st.session_state["access_token"],
            "token_type": st.session_state["token_type"],
            "user_role": st.session_state["user_role"],
        },
        sort_keys=True,
    )


def _clear_persisted_auth() -> None:
    statements = [
        f"localStorage.removeItem({json.dumps(storage_key)});"
        for storage_key in AUTH_STORAGE_KEYS.values()
    ]
    streamlit_js_eval(
        js_expressions="\n".join(statements),
        key=f"auth_storage_clear_{_next_revision()}",
    )
