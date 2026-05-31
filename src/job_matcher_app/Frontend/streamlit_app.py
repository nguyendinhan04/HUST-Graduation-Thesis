from __future__ import annotations

import os
from html import escape
from datetime import date, datetime
from typing import Any

import requests
import streamlit as st


DEFAULT_API_BASE_URL = "http://localhost:8000"


class ApiError(Exception):
    """Raised when the backend returns an unsuccessful response."""


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


def parse_api_error(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text or f"HTTP {response.status_code}"

    detail = payload.get("detail", payload)
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        messages = []
        for item in detail:
            if isinstance(item, dict):
                loc = ".".join(str(part) for part in item.get("loc", []))
                msg = item.get("msg", item)
                messages.append(f"{loc}: {msg}" if loc else str(msg))
            else:
                messages.append(str(item))
        return "\n".join(messages)
    return str(detail)


def request_json(
    method: str,
    path: str,
    *,
    json: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    auth: bool = False,
) -> Any:
    headers = auth_headers() if auth else {}
    try:
        response = requests.request(
            method,
            f"{api_base_url()}{path}",
            json=json,
            data=data,
            headers=headers,
            timeout=20,
        )
    except requests.RequestException as exc:
        raise ApiError(f"Could not connect to backend: {exc}") from exc

    if response.status_code >= 400:
        raise ApiError(parse_api_error(response))
    if not response.content:
        return None
    return response.json()


def login(email: str, password: str) -> None:
    payload = request_json(
        "POST",
        "/auth/login",
        data={"username": email, "password": password},
    )
    st.session_state["access_token"] = payload["access_token"]
    st.session_state["token_type"] = payload.get("token_type", "bearer")
    refresh_profile()


def logout() -> None:
    st.session_state["access_token"] = None
    st.session_state["token_type"] = "bearer"
    st.session_state["profile"] = None
    st.session_state["active_dialog"] = None
    st.session_state["active_item_id"] = None
    st.session_state["current_page"] = "profile"


def refresh_profile() -> None:
    st.session_state["profile"] = request_json(
        "GET",
        "/users/me/employee_profile",
        auth=True,
    )


def create_employee(payload: dict[str, Any]) -> Any:
    return request_json("POST", "/users/employees", json=payload)


def update_profile(payload: dict[str, Any]) -> Any:
    return request_json("PATCH", "/users/me/profile", json=payload, auth=True)


def create_experience(payload: dict[str, Any]) -> Any:
    return request_json("POST", "/users/me/experiences", json=payload, auth=True)


def update_experience(experience_id: int, payload: dict[str, Any]) -> Any:
    return request_json(
        "PATCH",
        f"/users/me/experiences/{experience_id}",
        json=payload,
        auth=True,
    )


def delete_experience(experience_id: int) -> Any:
    return request_json("DELETE", f"/users/me/experiences/{experience_id}", auth=True)


def create_education(payload: dict[str, Any]) -> Any:
    return request_json("POST", "/users/me/educations", json=payload, auth=True)


def update_education(education_id: int, payload: dict[str, Any]) -> Any:
    return request_json(
        "PATCH",
        f"/users/me/educations/{education_id}",
        json=payload,
        auth=True,
    )


def delete_education(education_id: int) -> Any:
    return request_json("DELETE", f"/users/me/educations/{education_id}", auth=True)


def add_skill(skill_name: str) -> Any:
    return request_json(
        "POST",
        "/users/me/skills",
        json={"skill_name": skill_name},
        auth=True,
    )


def delete_skill(skill_id: int) -> Any:
    return request_json("DELETE", f"/users/me/skills/{skill_id}", auth=True)


def nullable_text(value: Any) -> str:
    return "" if value is None else str(value)


def split_skills(raw_value: str) -> list[str]:
    return [skill.strip() for skill in raw_value.split(",") if skill.strip()]


def skills_to_text(skills: list[dict[str, Any]] | None) -> str:
    if not skills:
        return ""
    return ", ".join(skill.get("skill_name", "") for skill in skills if skill)


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def date_to_api(value: date | None) -> str | None:
    return value.isoformat() if value else None


def optional_date_input(
    label: str,
    key_prefix: str,
    value: str | None = None,
) -> date | None:
    parsed_value = parse_iso_date(value)
    enabled = st.checkbox(
        f"Set {label.lower()}",
        value=parsed_value is not None,
        key=f"{key_prefix}_enabled",
    )
    if not enabled:
        return None
    return st.date_input(
        label,
        value=parsed_value or date.today(),
        key=f"{key_prefix}_date",
    )


def clean_payload(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned = {}
    for key, value in payload.items():
        if isinstance(value, str):
            cleaned[key] = value.strip() or None
        else:
            cleaned[key] = value
    return cleaned


def show_api_error(message: str, exc: ApiError) -> None:
    st.error(f"{message}: {exc}")


def open_dialog(name: str, item_id: int | None = None) -> None:
    st.session_state["active_dialog"] = name
    st.session_state["active_item_id"] = item_id


def close_dialog() -> None:
    st.session_state["active_dialog"] = None
    st.session_state["active_item_id"] = None


def navigate_to(page: str) -> None:
    st.session_state["current_page"] = page
    close_dialog()


def inject_linkedin_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: #f3f2ef;
            color: #191919;
        }

        .block-container {
            max-width: 980px;
            padding-top: 1.25rem;
            padding-bottom: 3rem;
        }

        div[data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid #d7d3cc;
        }

        .linkedin-card {
            background: #ffffff;
            border: 1px solid #d7d3cc;
            border-radius: 8px;
            margin: 0 0 8px 0;
            overflow: hidden;
        }

        .profile-cover {
            height: 96px;
            background: linear-gradient(135deg, #0a66c2 0%, #378fe9 56%, #dce6f1 100%);
        }

        .profile-body {
            padding: 0 24px 22px;
        }

        .profile-avatar {
            width: 128px;
            height: 128px;
            border-radius: 50%;
            border: 4px solid #ffffff;
            margin-top: -64px;
            background: #eef3f8;
            object-fit: cover;
            display: block;
        }

        .profile-avatar-placeholder {
            width: 128px;
            height: 128px;
            border-radius: 50%;
            border: 4px solid #ffffff;
            margin-top: -64px;
            background: #eef3f8;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #56687a;
            font-size: 42px;
            font-weight: 700;
        }

        .profile-name {
            margin: 12px 0 0;
            font-size: 26px;
            font-weight: 650;
            line-height: 1.2;
        }

        .profile-headline {
            margin-top: 4px;
            font-size: 16px;
            color: #191919;
        }

        .muted {
            color: #666666;
            font-size: 14px;
        }

        .section-title {
            font-size: 20px;
            font-weight: 650;
            margin: 2px 0 12px;
        }

        .entity-row {
            display: grid;
            grid-template-columns: 48px minmax(0, 1fr);
            gap: 12px;
            padding: 12px 0 14px;
            border-bottom: 1px solid #e8e4de;
        }

        .entity-logo {
            width: 48px;
            height: 48px;
            border-radius: 4px;
            background: #eef3f8;
            color: #56687a;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 13px;
            text-align: center;
        }

        .entity-title {
            font-weight: 650;
            line-height: 1.25;
            margin-bottom: 2px;
        }

        .entity-subtitle {
            color: #191919;
            line-height: 1.35;
            font-size: 14px;
        }

        .entity-meta {
            color: #666666;
            font-size: 13px;
            line-height: 1.35;
        }

        .entity-desc {
            margin-top: 8px;
            color: #191919;
            font-size: 14px;
            line-height: 1.45;
            white-space: pre-wrap;
        }

        .skill-line {
            margin-top: 8px;
            font-size: 13px;
            font-weight: 600;
        }

        .skill-row {
            padding: 13px 0;
            border-bottom: 1px solid #e8e4de;
            font-weight: 600;
        }

        .empty-state {
            color: #666666;
            padding: 4px 0 18px;
        }

        div.stButton > button {
            border-radius: 999px;
            border: 0;
            background: transparent;
            color: #191919;
            min-height: 36px;
            font-weight: 600;
            width: 100%;
        }

        div.stButton > button:hover {
            background: #ebebeb;
            color: #191919;
            border: 0;
        }

        button[kind="primary"],
        div[data-testid="stFormSubmitButton"] button[kind="primary"] {
            background: #0a66c2 !important;
            border: 1px solid #0a66c2 !important;
            color: #ffffff !important;
            box-shadow: none !important;
        }

        button[kind="primary"]:hover,
        div[data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
            background: #004182 !important;
            border: 1px solid #004182 !important;
            color: #ffffff !important;
        }

        div[data-testid="stExpander"] {
            background: #ffffff;
            border: 1px solid #d7d3cc;
            border-radius: 8px;
            margin-bottom: 10px;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
        }

        dialog[open]::backdrop {
            background: rgba(0, 0, 0, 0.58) !important;
            backdrop-filter: blur(1px);
        }

        .stApp:has([data-testid="stDialog"])::before,
        .stApp:has(dialog[open])::before,
        .stApp:has([role="dialog"])::before {
            content: "";
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.58);
            backdrop-filter: blur(1px);
            z-index: 999998;
            pointer-events: none;
        }

        [data-testid="stDialog"],
        dialog[open],
        [role="dialog"] {
            position: fixed !important;
            top: 50% !important;
            left: 50% !important;
            transform: translate(-50%, -50%) !important;
            width: min(720px, calc(100vw - 40px)) !important;
            max-width: min(720px, calc(100vw - 40px)) !important;
            max-height: min(86vh, 900px) !important;
            margin: 0 !important;
            padding: 0 !important;
            background: #ffffff !important;
            border: 1px solid #c8c2b8 !important;
            border-radius: 16px !important;
            box-shadow: 0 24px 80px rgba(0, 0, 0, 0.42) !important;
            outline: none !important;
            overflow: hidden !important;
            z-index: 999999 !important;
        }

        [data-testid="stDialog"] > div,
        dialog[open] > div,
        [role="dialog"] > div {
            background: #ffffff !important;
            border-radius: 16px !important;
            max-height: min(86vh, 900px) !important;
            overflow-y: auto !important;
        }

        [data-testid="stDialog"] div[data-testid="stVerticalBlock"],
        dialog[open] div[data-testid="stVerticalBlock"],
        [role="dialog"] div[data-testid="stVerticalBlock"] {
            gap: 0.75rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def initials(value: str | None, fallback: str = "IN") -> str:
    words = [word for word in nullable_text(value).replace(",", " ").split() if word]
    if not words:
        return fallback
    return "".join(word[0].upper() for word in words[:2])


def format_month_year(value: str | None) -> str:
    parsed = parse_iso_date(value)
    if not parsed:
        return ""
    return parsed.strftime("%b %Y")


def format_date_range(start: str | None, end: str | None) -> str:
    start_label = format_month_year(start)
    end_label = format_month_year(end) or "Present"
    if start_label:
        return f"{start_label} - {end_label}"
    return end_label


def summarize_skills(skills: list[dict[str, Any]] | None, visible_count: int = 2) -> str:
    names = [skill.get("skill_name", "") for skill in skills or [] if skill.get("skill_name")]
    if not names:
        return ""
    visible = ", ".join(names[:visible_count])
    hidden_count = len(names) - visible_count
    if hidden_count > 0:
        return f"{visible} and +{hidden_count} skills"
    return visible


def html_or_empty(value: Any, fallback: str = "") -> str:
    return escape(nullable_text(value) or fallback)


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
                    refresh_profile()
                    st.success("Profile refreshed.")
                except ApiError as exc:
                    show_api_error("Could not load profile", exc)
            if st.button("Sign out", use_container_width=True):
                logout()
                st.rerun()


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


def render_skill_chips(skills: list[dict[str, Any]] | None) -> None:
    if not skills:
        st.caption("No skills yet.")
        return

    names = [skill.get("skill_name", "") for skill in skills if skill.get("skill_name")]
    st.markdown(" ".join(f"`{name}`" for name in names))


def render_profile_summary(profile: dict[str, Any]) -> None:
    employee = profile.get("employee_profile") or {}
    avatar_url = nullable_text(profile.get("avatar_url")).strip()
    if avatar_url:
        avatar_markup = (
            f'<img class="profile-avatar" src="{escape(avatar_url)}" '
            f'alt="{html_or_empty(profile.get("full_name"), "Employee")}">'
        )
    else:
        avatar_markup = (
            f'<div class="profile-avatar-placeholder">'
            f'{escape(initials(profile.get("full_name"), "E"))}</div>'
        )

    summary = employee.get("summary") or "No profile summary yet."
    st.markdown(
        f"""
        <div class="linkedin-card">
            <div class="profile-cover"></div>
            <div class="profile-body">
                {avatar_markup}
                <div class="profile-name">{html_or_empty(profile.get("full_name"), "No name yet")}</div>
                <div class="profile-headline">{html_or_empty(employee.get("headline"), "No headline yet")}</div>
                <div class="muted">{html_or_empty(employee.get("current_location"), "No location yet")} · {html_or_empty(profile.get("email"))}</div>
                <div class="muted">{html_or_empty(profile.get("phone"), "No phone yet")} · {employee.get("years_of_experience") or 0} years of experience</div>
                <div class="entity-desc">{html_or_empty(summary)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_profile_actions() -> None:
    spacer, edit_col, refresh_col = st.columns([9, 0.55, 0.55], gap="small")
    if edit_col.button("✎", key="open_profile_dialog", help="Edit profile"):
        open_dialog("profile")
    if refresh_col.button("↻", key="refresh_profile_top", help="Refresh profile"):
        try:
            refresh_profile()
            st.success("Profile refreshed.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Could not load profile", exc)


def render_dialog_close(key: str) -> None:
    _, close_col = st.columns([9, 0.65], gap="small")
    if close_col.button("×", key=key, help="Discard changes"):
        close_dialog()
        st.rerun()


def profile_payload_form(form_key: str, profile: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    employee = profile.get("employee_profile") or {}
    with st.form(form_key):
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full name", value=nullable_text(profile.get("full_name")))
            phone = st.text_input("Phone", value=nullable_text(profile.get("phone")))
            avatar_url = st.text_input(
                "Avatar URL",
                value=nullable_text(profile.get("avatar_url")),
            )
        with col2:
            headline = st.text_input("Headline", value=nullable_text(employee.get("headline")))
            years_of_experience = st.number_input(
                "Years of experience",
                min_value=0,
                step=1,
                value=int(employee.get("years_of_experience") or 0),
            )
            current_location = st.text_input(
                "Current location",
                value=nullable_text(employee.get("current_location")),
            )
        summary = st.text_area("Summary", value=nullable_text(employee.get("summary")))
        _, save_col = st.columns([5, 1.25])
        save_submitted = save_col.form_submit_button(
            "Save",
            type="primary",
            use_container_width=True,
        )

    payload = clean_payload(
        {
            "full_name": full_name,
            "phone": phone,
            "avatar_url": avatar_url,
            "headline": headline,
            "summary": summary,
            "years_of_experience": int(years_of_experience),
            "current_location": current_location,
        }
    )
    action = "save" if save_submitted else None
    return payload, action


def experience_payload_form(
    form_key: str,
    item: dict[str, Any] | None = None,
    *,
    allow_delete: bool = False,
) -> tuple[dict[str, Any], str | None]:
    item = item or {}
    with st.form(form_key):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Title", value=nullable_text(item.get("title")))
            company_name = st.text_input(
                "Company",
                value=nullable_text(item.get("company_name")),
            )
            employment_type = st.text_input(
                "Employment type",
                value=nullable_text(item.get("employment_type")),
            )
            location = st.text_input("Location", value=nullable_text(item.get("location")))
        with col2:
            location_type = st.text_input(
                "Location type",
                value=nullable_text(item.get("location_type")),
            )
            start_date = optional_date_input(
                "Start date",
                f"{form_key}_start",
                item.get("start_date"),
            )
            end_date = optional_date_input(
                "End date",
                f"{form_key}_end",
                item.get("end_date"),
            )
            skills = st.text_input("Skills", value=skills_to_text(item.get("skills")))
        description = st.text_area(
            "Description",
            value=nullable_text(item.get("description")),
        )
        if allow_delete:
            delete_col, _, save_col = st.columns([1.3, 4.4, 1.3])
            delete_submitted = delete_col.form_submit_button(
                "Delete",
                use_container_width=True,
            )
            save_submitted = save_col.form_submit_button(
                "Save",
                type="primary",
                use_container_width=True,
            )
        else:
            delete_submitted = False
            _, save_col = st.columns([5, 1.25])
            save_submitted = save_col.form_submit_button(
                "Save",
                type="primary",
                use_container_width=True,
            )

    payload = clean_payload(
        {
            "title": title,
            "company_name": company_name,
            "employment_type": employment_type,
            "location": location,
            "location_type": location_type,
            "description": description,
            "start_date": date_to_api(start_date),
            "end_date": date_to_api(end_date),
            "skills": split_skills(skills),
        }
    )
    action = "delete" if delete_submitted else "save" if save_submitted else None
    return payload, action


def education_payload_form(
    form_key: str,
    item: dict[str, Any] | None = None,
    *,
    allow_delete: bool = False,
) -> tuple[dict[str, Any], str | None]:
    item = item or {}
    with st.form(form_key):
        col1, col2 = st.columns(2)
        with col1:
            school = st.text_input("School", value=nullable_text(item.get("school")))
            degree = st.text_input("Degree", value=nullable_text(item.get("degree")))
            field_of_study = st.text_input(
                "Field of study",
                value=nullable_text(item.get("field_of_study")),
            )
        with col2:
            start_date = optional_date_input(
                "Start date",
                f"{form_key}_start",
                item.get("start_date"),
            )
            end_date = optional_date_input(
                "End date",
                f"{form_key}_end",
                item.get("end_date"),
            )
            skills = st.text_input("Skills", value=skills_to_text(item.get("skills")))
        description = st.text_area("Description", value=nullable_text(item.get("description")))
        if allow_delete:
            delete_col, _, save_col = st.columns([1.3, 4.4, 1.3])
            delete_submitted = delete_col.form_submit_button(
                "Delete",
                use_container_width=True,
            )
            save_submitted = save_col.form_submit_button(
                "Save",
                type="primary",
                use_container_width=True,
            )
        else:
            delete_submitted = False
            _, save_col = st.columns([5, 1.25])
            save_submitted = save_col.form_submit_button(
                "Save",
                type="primary",
                use_container_width=True,
            )

    payload = clean_payload(
        {
            "school": school,
            "degree": degree,
            "field_of_study": field_of_study,
            "description": description,
            "start_date": date_to_api(start_date),
            "end_date": date_to_api(end_date),
            "skills": split_skills(skills),
        }
    )
    action = "delete" if delete_submitted else "save" if save_submitted else None
    return payload, action


def render_experience_item(item: dict[str, Any]) -> None:
    title = item.get("title") or "No title yet"
    company = item.get("company_name") or "No company yet"
    employment = item.get("employment_type") or "No employment type yet"
    location_bits = [
        value
        for value in [item.get("location"), item.get("location_type")]
        if value
    ]
    location = " · ".join(location_bits)
    date_range = format_date_range(item.get("start_date"), item.get("end_date"))
    description = item.get("description") or ""
    skill_summary = summarize_skills(item.get("skills"))
    skill_markup = (
        f'<div class="skill-line">{html_or_empty(skill_summary)}</div>'
        if skill_summary
        else ""
    )

    st.markdown(
        f"""
        <div class="entity-row">
            <div class="entity-logo">{escape(initials(company, "CO"))}</div>
            <div>
                <div class="entity-title">{html_or_empty(title)}</div>
                <div class="entity-subtitle">{html_or_empty(company)} · {html_or_empty(employment)}</div>
                <div class="entity-meta">{html_or_empty(date_range)}{(" · " + html_or_empty(location)) if location else ""}</div>
                <div class="entity-desc">{html_or_empty(description)}</div>
                {skill_markup}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_education_item(item: dict[str, Any]) -> None:
    school = item.get("school") or "No school yet"
    degree = item.get("degree") or "No degree yet"
    field_of_study = item.get("field_of_study") or "No field of study yet"
    date_range = format_date_range(item.get("start_date"), item.get("end_date"))
    description = item.get("description") or ""
    skill_summary = summarize_skills(item.get("skills"))
    skill_markup = (
        f'<div class="skill-line">{html_or_empty(skill_summary)}</div>'
        if skill_summary
        else ""
    )

    st.markdown(
        f"""
        <div class="entity-row">
            <div class="entity-logo">{escape(initials(school, "ED"))}</div>
            <div>
                <div class="entity-title">{html_or_empty(school)}</div>
                <div class="entity-subtitle">{html_or_empty(degree)}, {html_or_empty(field_of_study)}</div>
                <div class="entity-meta">{html_or_empty(date_range)}</div>
                <div class="entity-desc">{html_or_empty(description)}</div>
                {skill_markup}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_experiences(profile: dict[str, Any]) -> None:
    experiences = profile.get("experiences") or []
    with st.container(border=True):
        header_left, add_col, edit_col = st.columns([9, 0.55, 0.55], gap="small")
        header_left.markdown('<div class="section-title">Experience</div>', unsafe_allow_html=True)
        if add_col.button("+", key="add_experience", help="Add experience"):
            open_dialog("add_experience")
        if edit_col.button("✎", key="manage_experiences", help="Edit experience"):
            navigate_to("experiences")
            st.rerun()

        if not experiences:
            st.markdown('<div class="empty-state">No experience yet.</div>', unsafe_allow_html=True)
            return

        for item in experiences:
            render_experience_item(item)


def render_educations(profile: dict[str, Any]) -> None:
    educations = profile.get("educations") or []
    with st.container(border=True):
        header_left, add_col, edit_col = st.columns([9, 0.55, 0.55], gap="small")
        header_left.markdown('<div class="section-title">Education</div>', unsafe_allow_html=True)
        if add_col.button("+", key="add_education", help="Add education"):
            open_dialog("add_education")
        if edit_col.button("✎", key="manage_educations", help="Edit education"):
            navigate_to("educations")
            st.rerun()

        if not educations:
            st.markdown('<div class="empty-state">No education yet.</div>', unsafe_allow_html=True)
            return

        for item in educations:
            render_education_item(item)


def render_standalone_skills(profile: dict[str, Any]) -> None:
    skills = profile.get("skills") or []
    with st.container(border=True):
        header_left, add_col, edit_col = st.columns([9, 0.55, 0.55], gap="small")
        header_left.markdown(
            f'<div class="section-title">Skills ({len(skills)})</div>',
            unsafe_allow_html=True,
        )
        if add_col.button("+", key="add_skill", help="Add skill"):
            open_dialog("add_skill")
        if edit_col.button("✎", key="manage_skills", help="Edit skills"):
            navigate_to("skills")
            st.rerun()

        if not skills:
            st.markdown('<div class="empty-state">No standalone skills yet.</div>', unsafe_allow_html=True)
            return

        visible_skills = skills[:5]
        for skill in visible_skills:
            st.markdown(
                f'<div class="skill-row">{html_or_empty(skill.get("skill_name"))}</div>',
                unsafe_allow_html=True,
            )

        if len(skills) > 5:
            st.caption(f"Show all {len(skills)} skills")


@st.dialog("Edit profile")
def profile_dialog(profile: dict[str, Any]) -> None:
    render_dialog_close("discard_profile")

    payload, action = profile_payload_form("profile_edit_form", profile)
    if action == "save":
        try:
            update_profile(payload)
            refresh_profile()
            close_dialog()
            st.success("Profile updated.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Could not update profile", exc)


@st.dialog("Add experience")
def add_experience_dialog() -> None:
    render_dialog_close("discard_add_experience")

    payload, action = experience_payload_form("create_experience_form")
    if action == "save":
        try:
            create_experience(payload)
            refresh_profile()
            close_dialog()
            st.success("Experience added.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Could not add experience", exc)


@st.dialog("Edit experience")
def edit_experience_dialog(profile: dict[str, Any]) -> None:
    render_dialog_close("discard_edit_experience")

    experiences = profile.get("experiences") or []
    experience_id = st.session_state.get("active_item_id")
    item = next(
        (
            experience
            for experience in experiences
            if experience.get("experience_id") == experience_id
        ),
        None,
    )
    if item is None:
        st.info("Experience not found.")
        return

    payload, action = experience_payload_form(
        f"edit_experience_form_{item['experience_id']}",
        item,
        allow_delete=True,
    )
    if action == "delete":
        try:
            delete_experience(item["experience_id"])
            refresh_profile()
            close_dialog()
            st.success("Experience deleted.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Could not delete experience", exc)
    elif action == "save":
        try:
            update_experience(item["experience_id"], payload)
            refresh_profile()
            close_dialog()
            st.success("Experience updated.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Could not update experience", exc)


@st.dialog("Add education")
def add_education_dialog() -> None:
    render_dialog_close("discard_add_education")

    payload, action = education_payload_form("create_education_form")
    if action == "save":
        try:
            create_education(payload)
            refresh_profile()
            close_dialog()
            st.success("Education added.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Could not add education", exc)


@st.dialog("Edit education")
def edit_education_dialog(profile: dict[str, Any]) -> None:
    render_dialog_close("discard_edit_education")

    educations = profile.get("educations") or []
    education_id = st.session_state.get("active_item_id")
    item = next(
        (
            education
            for education in educations
            if education.get("education_id") == education_id
        ),
        None,
    )
    if item is None:
        st.info("Education not found.")
        return

    payload, action = education_payload_form(
        f"edit_education_form_{item['education_id']}",
        item,
        allow_delete=True,
    )
    if action == "delete":
        try:
            delete_education(item["education_id"])
            refresh_profile()
            close_dialog()
            st.success("Education deleted.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Could not delete education", exc)
    elif action == "save":
        try:
            update_education(item["education_id"], payload)
            refresh_profile()
            close_dialog()
            st.success("Education updated.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Could not update education", exc)


@st.dialog("Add skill")
def add_skill_dialog() -> None:
    render_dialog_close("discard_add_skill")

    with st.form("add_skill_form"):
        skill_name = st.text_input("Skill name")
        _, save_col = st.columns([5, 1.25])
        action = "save" if save_col.form_submit_button(
            "Save",
            type="primary",
            use_container_width=True,
        ) else None
    if action == "save":
        if not skill_name.strip():
            st.warning("Please enter a skill name.")
            return
        try:
            add_skill(skill_name.strip())
            refresh_profile()
            close_dialog()
            st.success("Skill added.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Could not add skill", exc)


@st.dialog("Edit skills")
def manage_skills_dialog(profile: dict[str, Any]) -> None:
    render_dialog_close("discard_manage_skills")

    skills = profile.get("skills") or []
    if not skills:
        st.info("No standalone skills yet.")
        return

    for skill in skills:
        col1, col2 = st.columns([3, 1])
        col1.write(skill.get("skill_name") or "Unnamed skill")
        if col2.button(
            "Delete",
            key=f"delete_skill_{skill['skill_id']}",
            use_container_width=True,
        ):
            try:
                delete_skill(skill["skill_id"])
                refresh_profile()
                close_dialog()
                st.success("Skill deleted.")
                st.rerun()
            except ApiError as exc:
                show_api_error("Could not delete skill", exc)


def render_management_header(title: str, add_dialog: str) -> None:
    with st.container(border=True):
        back_col, title_col, add_col = st.columns([0.65, 8.8, 0.55], gap="small")
        if back_col.button("←", key=f"back_{title}", help="Back to profile"):
            navigate_to("profile")
            st.rerun()
        title_col.markdown(f'<div class="section-title">{escape(title)}</div>', unsafe_allow_html=True)
        if add_col.button("+", key=f"add_from_{title}", help=f"Add {title.lower()}"):
            open_dialog(add_dialog)


def render_experience_management_page(profile: dict[str, Any]) -> None:
    render_management_header("Experience", "add_experience")
    experiences = profile.get("experiences") or []
    if not experiences:
        with st.container(border=True):
            st.markdown('<div class="empty-state">No experience yet.</div>', unsafe_allow_html=True)
        return

    with st.container(border=True):
        for index, item in enumerate(experiences, start=1):
            title = item.get("title") or f"Experience #{index}"
            company = item.get("company_name") or "No company yet"
            location_bits = [
                value
                for value in [item.get("location"), item.get("location_type")]
                if value
            ]
            location = " · ".join(location_bits)
            skill_summary = summarize_skills(item.get("skills"))
            logo_col, body_col, edit_col = st.columns([0.8, 8.6, 0.6], gap="small")
            logo_col.markdown(
                f'<div class="entity-logo">{escape(initials(company, "CO"))}</div>',
                unsafe_allow_html=True,
            )
            body_col.markdown(
                f"""
                <div class="entity-title">{html_or_empty(title)}</div>
                <div class="entity-subtitle">{html_or_empty(company)} · {html_or_empty(item.get("employment_type"), "No employment type yet")}</div>
                <div class="entity-meta">{html_or_empty(format_date_range(item.get("start_date"), item.get("end_date")))}{(" · " + html_or_empty(location)) if location else ""}</div>
                <div class="entity-desc">{html_or_empty(item.get("description"))}</div>
                {f'<div class="skill-line">{html_or_empty(skill_summary)}</div>' if skill_summary else ""}
                """,
                unsafe_allow_html=True,
            )
            if edit_col.button("✎", key=f"edit_experience_page_{item['experience_id']}", help="Edit experience"):
                open_dialog("edit_experience", item["experience_id"])
            if index < len(experiences):
                st.divider()


def render_education_management_page(profile: dict[str, Any]) -> None:
    render_management_header("Education", "add_education")
    educations = profile.get("educations") or []
    if not educations:
        with st.container(border=True):
            st.markdown('<div class="empty-state">No education yet.</div>', unsafe_allow_html=True)
        return

    with st.container(border=True):
        for index, item in enumerate(educations, start=1):
            school = item.get("school") or f"Education #{index}"
            degree = item.get("degree") or "No degree yet"
            skill_summary = summarize_skills(item.get("skills"))
            logo_col, body_col, edit_col = st.columns([0.8, 8.6, 0.6], gap="small")
            logo_col.markdown(
                f'<div class="entity-logo">{escape(initials(school, "ED"))}</div>',
                unsafe_allow_html=True,
            )
            body_col.markdown(
                f"""
                <div class="entity-title">{html_or_empty(school)}</div>
                <div class="entity-subtitle">{html_or_empty(degree)}, {html_or_empty(item.get("field_of_study"), "No field of study yet")}</div>
                <div class="entity-meta">{html_or_empty(format_date_range(item.get("start_date"), item.get("end_date")))}</div>
                <div class="entity-desc">{html_or_empty(item.get("description"))}</div>
                {f'<div class="skill-line">{html_or_empty(skill_summary)}</div>' if skill_summary else ""}
                """,
                unsafe_allow_html=True,
            )
            if edit_col.button("✎", key=f"edit_education_page_{item['education_id']}", help="Edit education"):
                open_dialog("edit_education", item["education_id"])
            if index < len(educations):
                st.divider()


def render_skill_management_page(profile: dict[str, Any]) -> None:
    render_management_header("Skills", "add_skill")
    skills = profile.get("skills") or []
    if not skills:
        with st.container(border=True):
            st.markdown('<div class="empty-state">No standalone skills yet.</div>', unsafe_allow_html=True)
        return

    with st.container(border=True):
        for index, skill in enumerate(skills, start=1):
            name_col, delete_col = st.columns([9.3, 0.7], gap="small")
            name_col.markdown(
                f'<div class="skill-row">{html_or_empty(skill.get("skill_name"), "Unnamed skill")}</div>',
                unsafe_allow_html=True,
            )
            if delete_col.button("×", key=f"delete_skill_page_{skill['skill_id']}", help="Delete skill"):
                try:
                    delete_skill(skill["skill_id"])
                    refresh_profile()
                    st.success("Skill deleted.")
                    st.rerun()
                except ApiError as exc:
                    show_api_error("Could not delete skill", exc)
            if index < len(skills):
                st.divider()


def render_active_dialog(profile: dict[str, Any]) -> None:
    active_dialog = st.session_state.get("active_dialog")
    if active_dialog == "profile":
        profile_dialog(profile)
    elif active_dialog == "add_experience":
        add_experience_dialog()
    elif active_dialog == "edit_experience":
        edit_experience_dialog(profile)
    elif active_dialog == "add_education":
        add_education_dialog()
    elif active_dialog == "edit_education":
        edit_education_dialog(profile)
    elif active_dialog == "add_skill":
        add_skill_dialog()
    elif active_dialog == "manage_skills":
        manage_skills_dialog(profile)


def render_profile_page() -> None:
    if st.session_state.get("profile") is None:
        try:
            refresh_profile()
        except ApiError as exc:
            show_api_error("Could not load profile", exc)
            return

    profile = st.session_state["profile"]
    current_page = st.session_state.get("current_page", "profile")
    if current_page == "experiences":
        render_experience_management_page(profile)
        render_active_dialog(profile)
        return
    if current_page == "educations":
        render_education_management_page(profile)
        render_active_dialog(profile)
        return
    if current_page == "skills":
        render_skill_management_page(profile)
        render_active_dialog(profile)
        return

    render_profile_summary(profile)
    render_profile_actions()
    render_experiences(profile)
    render_educations(profile)
    render_standalone_skills(profile)
    render_active_dialog(profile)


def main() -> None:
    st.set_page_config(
        page_title="Employee Profile",
        page_icon="E",
        layout="wide",
    )
    init_session_state()
    inject_linkedin_styles()
    sidebar()

    if st.session_state.get("access_token"):
        render_profile_page()
    else:
        render_auth_page()


if __name__ == "__main__":
    main()
