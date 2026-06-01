from __future__ import annotations

from html import escape

import streamlit as st

from frontend_app.formatting import initials
from frontend_app.state import logout, navigate_to


def _nav_item(label: str, icon: str, page: str) -> None:
    current_page = st.session_state.get("current_page", "profile")
    profile_pages = {"profile", "experiences", "educations", "skills"}
    recommendation_pages = {"recommendations", "job_detail"}
    is_active = (
        page == "profile"
        and current_page in profile_pages
        or page == "recommendations"
        and current_page in recommendation_pages
    )
    item_key = f"sidebar-nav-item-{page.replace('_', '-')}"
    button_key = f"sidebar_nav_{page}"
    with st.container(key=item_key):
        if is_active:
            st.markdown('<div class="sidebar-nav-active-marker"></div>', unsafe_allow_html=True)
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

