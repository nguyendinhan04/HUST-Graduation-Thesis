from __future__ import annotations

import streamlit as st

from frontend_app.api_client import (
    ApiError,
    create_employee,
    create_employer,
    login,
    login_employer,
)
from frontend_app.formatting import clean_payload, show_api_error
from frontend_app.loading import form_loading


def render_login_tab() -> None:
    with st.form("employee_login_form"):
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        submitted = st.form_submit_button("Sign in", use_container_width=True)

    if submitted:
        if not email.strip() or not password:
            st.warning("Please enter email and password.")
            return
        try:
            with form_loading("Signing in..."):
                login(email.strip(), password)
            st.success("Signed in successfully.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Sign in failed", exc)


def render_register_tab() -> None:
    with st.form("employee_register_form"):
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
            with form_loading("Creating account..."):
                create_employee(payload)
                login(email.strip(), password)
            st.success("Account created and signed in.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Registration failed", exc)


def render_employer_login_tab() -> None:
    with st.form("employer_login_form"):
        email = st.text_input("Email", key="employer_login_email")
        password = st.text_input("Password", type="password", key="employer_login_password")
        submitted = st.form_submit_button("Sign in as employer", use_container_width=True)

    if submitted:
        if not email.strip() or not password:
            st.warning("Please enter email and password.")
            return
        try:
            with form_loading("Signing in..."):
                login_employer(email.strip(), password)
            st.success("Signed in successfully.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Employer sign in failed", exc)


def render_employer_register_tab() -> None:
    with st.form("employer_register_form"):
        st.markdown('<div class="auth-form-section-title">Account</div>', unsafe_allow_html=True)
        account_col, profile_col = st.columns(2)
        with account_col:
            email = st.text_input("Email", key="employer_register_email")
            password = st.text_input(
                "Password",
                type="password",
                key="employer_register_password",
            )
            password_confirm = st.text_input(
                "Confirm password",
                type="password",
                key="employer_register_password_confirm",
            )
        with profile_col:
            full_name = st.text_input("Full name", key="employer_register_full_name")
            phone = st.text_input("Phone", key="employer_register_phone")
            position = st.text_input("Position", key="employer_register_position")

        st.markdown('<div class="auth-form-section-title">Company</div>', unsafe_allow_html=True)
        company_col, detail_col = st.columns(2)
        with company_col:
            company_name = st.text_input("Company name", key="employer_register_company_name")
            website = st.text_input("Website", key="employer_register_website")
            industry = st.text_input("Industry", key="employer_register_industry")
            company_size = st.text_input("Company size", key="employer_register_company_size")
        with detail_col:
            location = st.text_input("Location", key="employer_register_location")
            address = st.text_input("Address", key="employer_register_address")
            logo_url = st.text_input("Logo URL", key="employer_register_logo_url")
            avatar_url = st.text_input("Avatar URL", key="employer_register_avatar_url")
        description = st.text_area("Company description", key="employer_register_description")
        submitted = st.form_submit_button("Create employer account", use_container_width=True)

    if submitted:
        if not email.strip() or not password or not company_name.strip():
            st.warning("Email, password, and company name are required.")
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
                "position": position,
                "company_name": company_name,
                "description": description,
                "website": website,
                "logo_url": logo_url,
                "industry": industry,
                "company_size": company_size,
                "address": address,
                "location": location,
            }
        )

        try:
            with form_loading("Creating employer account..."):
                create_employer(payload)
                login_employer(email.strip(), password)
            st.success("Employer account created and signed in.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Employer registration failed", exc)


def render_employee_auth() -> None:
    login_tab, register_tab = st.tabs(["Sign in", "Register"])
    with login_tab:
        render_login_tab()
    with register_tab:
        render_register_tab()


def render_employer_auth() -> None:
    login_tab, register_tab = st.tabs(["Sign in", "Register"])
    with login_tab:
        render_employer_login_tab()
    with register_tab:
        render_employer_register_tab()


def render_auth_page() -> None:
    st.title("Job Matcher")
    st.caption("Sign in or create an account for your workspace.")

    role = st.radio(
        "Account type",
        ["Employee", "Employer"],
        horizontal=True,
        key="auth_role",
    )
    if role == "Employer":
        render_employer_auth()
    else:
        render_employee_auth()
