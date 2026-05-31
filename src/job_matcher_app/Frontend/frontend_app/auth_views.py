from __future__ import annotations

import streamlit as st

from frontend_app.api_client import ApiError, create_employee, login
from frontend_app.formatting import clean_payload, show_api_error


def render_login_tab() -> None:
    with st.form("login_form"):
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        submitted = st.form_submit_button("Sign in", use_container_width=True)

    if submitted:
        if not email.strip() or not password:
            st.warning("Please enter email and password.")
            return
        try:
            login(email.strip(), password)
            st.success("Signed in successfully.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Sign in failed", exc)



def render_register_tab() -> None:
    with st.form("register_form"):
        col1, col2 = st.columns(2)
        with col1:
            email = st.text_input("Email", key="register_email")
            password = st.text_input("Password", type="password", key="register_password")
            password_confirm = st.text_input(
                "Confirm password",
                type="password",
                key="register_password_confirm",
            )
            full_name = st.text_input("Full name", key="register_full_name")
            phone = st.text_input("Phone", key="register_phone")
        with col2:
            avatar_url = st.text_input("Avatar URL", key="register_avatar")
            headline = st.text_input("Headline", key="register_headline")
            years_of_experience = st.number_input(
                "Years of experience",
                min_value=0,
                step=1,
                key="register_years",
            )
            current_location = st.text_input("Current location", key="register_location")
        summary = st.text_area("Profile summary", key="register_summary")
        submitted = st.form_submit_button("Create employee account", use_container_width=True)

    if submitted:
        if not email.strip() or not password:
            st.warning("Email and password are required.")
            return
        if password != password_confirm:
            st.warning("Password confirmation does not match.")
            return

        payload = clean_payload(
            {
                "email": email,
                "password": password,
                "full_name": full_name,
                "phone": phone,
                "avatar_url": avatar_url,
                "headline": headline,
                "summary": summary,
                "years_of_experience": int(years_of_experience),
                "current_location": current_location,
            }
        )

        try:
            create_employee(payload)
            login(email.strip(), password)
            st.success("Account created and signed in.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Registration failed", exc)



def render_auth_page() -> None:
    st.title("Employee Portal")
    st.caption("Sign in or create an employee account to manage your profile.")

    login_tab, register_tab = st.tabs(["Sign in", "Register"])
    with login_tab:
        render_login_tab()
    with register_tab:
        render_register_tab()

