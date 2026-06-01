from __future__ import annotations

from html import escape

import streamlit as st

from frontend_app.formatting import initials
from frontend_app.state import logout, navigate_to


def _active_nav_page() -> str:
    current_page = st.session_state.get("current_page", "profile")
    if current_page in {"recommendations", "job_detail"}:
        return "recommendations"
    return "profile"


def _render_active_nav_styles() -> None:
    active_page = _active_nav_page()
    inactive_page = "recommendations" if active_page == "profile" else "profile"
    active_key = f"sidebar_nav_{active_page}"
    active_key_hyphen = f"sidebar-nav-{active_page}"
    inactive_key = f"sidebar_nav_{inactive_page}"
    inactive_key_hyphen = f"sidebar-nav-{inactive_page}"
    st.markdown(
        f"""
        <style>
        div[data-testid="stSidebar"] .st-key-{inactive_key} button,
        div[data-testid="stSidebar"] .st-key-{inactive_key_hyphen} button {{
            min-height: 44px !important;
            background: transparent !important;
            background-color: transparent !important;
            border-color: transparent !important;
            color: #111827 !important;
            box-shadow: none !important;
        }}

        div[data-testid="stSidebar"] .st-key-{active_key} button,
        div[data-testid="stSidebar"] .st-key-{active_key_hyphen} button {{
            min-height: 62px !important;
            color: #082f49 !important;
            background: #0ea5e9 !important;
            background-color: #0ea5e9 !important;
            border-color: #0ea5e9 !important;
            border-radius: 8px 24px 24px 8px !important;
            box-shadow: none !important;
        }}

        div[data-testid="stSidebar"] .st-key-{active_key} button p,
        div[data-testid="stSidebar"] .st-key-{active_key_hyphen} button p {{
            color: #082f49 !important;
            font-weight: 760 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _nav_item(label: str, icon: str, page: str) -> None:
    item_key = f"sidebar-nav-item-{page.replace('_', '-')}"
    button_key = f"sidebar_nav_{page}"
    with st.container(key=item_key):
        if st.button(
            f"{icon}  {label}",
            key=button_key,
            use_container_width=True,
            help=label,
        ):
            navigate_to(page)
            st.rerun()


def sidebar() -> None:
    with st.sidebar:
        if st.session_state.get("access_token"):
            profile = st.session_state.get("profile") or {}
            email = profile.get("email") or "Employee"
            st.markdown(
                f"""
                <div class="sidebar-brand">
                    <div class="sidebar-brand-mark">JM</div>
                    <div>
                        <div class="sidebar-brand-title">Job Matcher</div>
                        <div class="sidebar-brand-subtitle">Employee workspace</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            _render_active_nav_styles()
            st.markdown('<div class="sidebar-section-label">Navigation</div>', unsafe_allow_html=True)
            _nav_item("Profile", "👤", "profile")
            _nav_item("Recommendations", "💼", "recommendations")

            st.divider()
            st.markdown(
                f"""
                <div class="sidebar-user">
                    <div class="sidebar-user-avatar">{escape(initials(email, "EM"))}</div>
                    <div class="sidebar-user-meta">
                        <div class="sidebar-user-label">Signed in</div>
                        <div class="sidebar-user-email">{escape(email)}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Sign out", use_container_width=True):
                logout()
                st.rerun()

