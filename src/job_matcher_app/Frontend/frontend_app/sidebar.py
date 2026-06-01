from __future__ import annotations

from html import escape

import streamlit as st

from frontend_app.formatting import initials
from frontend_app.state import logout, navigate_to


def _nav_item(label: str, icon: str, page: str) -> None:
    is_active = st.session_state.get("current_page", "profile") == page
    rendered_key = f"sidebar-nav-{page.replace('_', '-')}"
    legacy_rendered_key = f"sidebar_nav_{page}"
    if st.button(
        f"{icon}  {label}",
        key=f"sidebar_nav_{page}",
        use_container_width=True,
        help=label,
    ):
        navigate_to(page)
        st.rerun()
    if is_active:
        st.markdown(
            f"""
            <style>
            div[data-testid="stSidebar"] .st-key-{legacy_rendered_key} button,
            div[data-testid="stSidebar"] .st-key-{rendered_key} button {{
                min-height: 62px !important;
                color: #082f49 !important;
                background: #0ea5e9 !important;
                background-color: #0ea5e9 !important;
                border-color: #0ea5e9 !important;
                border-radius: 8px 24px 24px 8px !important;
                box-shadow: none !important;
            }}
            div[data-testid="stSidebar"] .st-key-{legacy_rendered_key} button p,
            div[data-testid="stSidebar"] .st-key-{rendered_key} button p {{
                color: #082f49 !important;
                font-weight: 760 !important;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )


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

