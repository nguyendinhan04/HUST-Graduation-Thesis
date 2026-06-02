from __future__ import annotations

from html import escape

import streamlit as st

from frontend_app.formatting import initials
from frontend_app.state import logout, navigate_to


def _active_nav_page() -> str:
    if st.session_state.get("user_role") == "employer":
        return "dashboard"
    current_page = st.session_state.get("current_page", "profile")
    if current_page == "job_detail":
        return_page = st.session_state.get("selected_job_return_page") or "recommendations"
        return return_page if return_page in {"profile", "explore", "recommendations"} else "recommendations"
    if current_page in {"explore", "recommendations"}:
        return current_page
    return "profile"


def _render_active_nav_styles() -> None:
    active_page = _active_nav_page()
    active_key = f"sidebar-nav-{active_page}"
    nav_pages = (
        ("dashboard",)
        if st.session_state.get("user_role") == "employer"
        else ("profile", "explore", "recommendations")
    )
    inactive_keys = [
        f"sidebar-nav-{page}"
        for page in nav_pages
        if page != active_page
    ]
    inactive_styles = "\n".join(
        f"""
        div[data-testid="stSidebar"] .st-key-{inactive_key} button {{
            min-height: 46px !important;
            background: transparent !important;
            background-color: transparent !important;
            border-color: transparent !important;
            color: #4b5563 !important;
            box-shadow: none !important;
        }}
        """
        for inactive_key in inactive_keys
    )
    st.markdown(
        f"""
        <style>
        {inactive_styles}

        div[data-testid="stSidebar"] .st-key-{active_key} button {{
            min-height: 46px !important;
            color: #111827 !important;
            background: #d9dee8 !important;
            background-color: #d9dee8 !important;
            border-color: #d9dee8 !important;
            border-radius: 8px !important;
            box-shadow: none !important;
        }}

        div[data-testid="stSidebar"] .st-key-{active_key} button p {{
            color: #111827 !important;
            font-weight: 800 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _nav_item(label: str, icon: str, page: str) -> None:
    button_key = f"sidebar-nav-{page.replace('_', '-')}"
    if st.button(
        f"{icon}  {label}",
        key=button_key,
        use_container_width=True,
    ):
        navigate_to(page)
        st.rerun()


def sidebar() -> None:
    with st.sidebar:
        if st.session_state.get("access_token"):
            profile = st.session_state.get("profile") or {}
            is_employer = st.session_state.get("user_role") == "employer"
            company = profile.get("company") or {}
            email = profile.get("email") or ("Employer" if is_employer else "Employee")
            subtitle = "Employer workspace" if is_employer else "Employee workspace"
            st.markdown(
                f"""
                <div class="sidebar-brand">
                    <div class="sidebar-brand-mark">JM</div>
                    <div>
                        <div class="sidebar-brand-title">Job Matcher</div>
                        <div class="sidebar-brand-subtitle">{escape(subtitle)}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.container(key="sidebar-navigator"):
                _render_active_nav_styles()
                st.markdown(
                    '<div class="sidebar-section-label">Navigation</div>',
                    unsafe_allow_html=True,
                )
                if is_employer:
                    _nav_item("Dashboard", "▦", "dashboard")
                else:
                    _nav_item("Profile", "👤", "profile")
                    _nav_item("Explore jobs", "🔎", "explore")
                    _nav_item("Recommendations", "💼", "recommendations")

            display_name = company.get("name") if is_employer else email
            display_name = display_name or email
            
            st.markdown(
                f"""
                <div class="sidebar-footer-marker"></div>
                <div class="sidebar-footer">
                    <div class="sidebar-user">
                        <div class="sidebar-user-avatar">{escape(initials(email, "EM"))}</div>
                        <div class="sidebar-user-meta">
                            <div class="sidebar-user-label">Signed in</div>
                            <div class="sidebar-user-email">{escape(str(display_name))}</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.container(key="sidebar-signout"):
                if st.button("Sign out", use_container_width=True):
                    logout()
                    st.rerun()
