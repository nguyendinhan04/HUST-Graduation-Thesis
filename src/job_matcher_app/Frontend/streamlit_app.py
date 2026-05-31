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
    st.session_state.setdefault("editing_profile", False)
    st.session_state.setdefault("show_add_experience", False)
    st.session_state.setdefault("show_edit_experiences", False)
    st.session_state.setdefault("show_add_education", False)
    st.session_state.setdefault("show_edit_educations", False)
    st.session_state.setdefault("show_add_skill", False)
    st.session_state.setdefault("show_edit_skills", False)


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
        raise ApiError(f"Không kết nối được backend: {exc}") from exc

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
    st.session_state["editing_profile"] = False


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
        f"Có {label.lower()}",
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
            margin: 0 0 14px;
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
        }

        div.stButton > button:hover {
            background: #ebebeb;
            color: #191919;
            border: 0;
        }

        div[data-testid="stExpander"] {
            background: #ffffff;
            border: 1px solid #d7d3cc;
            border-radius: 8px;
            margin-bottom: 10px;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0;
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
        st.header("Cấu hình")
        api_url = st.text_input("API backend", value=api_base_url())
        normalized_url = api_url.strip().rstrip("/") or DEFAULT_API_BASE_URL
        if normalized_url != st.session_state["api_base_url"]:
            st.session_state["api_base_url"] = normalized_url
            st.session_state["profile"] = None

        if st.session_state.get("access_token"):
            profile = st.session_state.get("profile") or {}
            st.divider()
            st.caption("Đang đăng nhập")
            st.write(profile.get("email", "Employee"))
            if st.button("Làm mới profile", use_container_width=True):
                try:
                    refresh_profile()
                    st.success("Đã tải lại profile.")
                except ApiError as exc:
                    show_api_error("Không tải được profile", exc)
            if st.button("Đăng xuất", use_container_width=True):
                logout()
                st.rerun()


def render_login_tab() -> None:
    with st.form("login_form"):
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Mật khẩu", type="password", key="login_password")
        submitted = st.form_submit_button("Đăng nhập", use_container_width=True)

    if submitted:
        if not email.strip() or not password:
            st.warning("Vui lòng nhập email và mật khẩu.")
            return
        try:
            login(email.strip(), password)
            st.success("Đăng nhập thành công.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Đăng nhập thất bại", exc)


def render_register_tab() -> None:
    with st.form("register_form"):
        col1, col2 = st.columns(2)
        with col1:
            email = st.text_input("Email", key="register_email")
            password = st.text_input("Mật khẩu", type="password", key="register_password")
            password_confirm = st.text_input(
                "Nhập lại mật khẩu",
                type="password",
                key="register_password_confirm",
            )
            full_name = st.text_input("Họ tên", key="register_full_name")
            phone = st.text_input("Số điện thoại", key="register_phone")
        with col2:
            avatar_url = st.text_input("Avatar URL", key="register_avatar")
            headline = st.text_input("Headline", key="register_headline")
            years_of_experience = st.number_input(
                "Số năm kinh nghiệm",
                min_value=0,
                step=1,
                key="register_years",
            )
            current_location = st.text_input("Địa điểm hiện tại", key="register_location")
        summary = st.text_area("Tóm tắt hồ sơ", key="register_summary")
        submitted = st.form_submit_button("Đăng ký employee", use_container_width=True)

    if submitted:
        if not email.strip() or not password:
            st.warning("Email và mật khẩu là bắt buộc.")
            return
        if password != password_confirm:
            st.warning("Mật khẩu nhập lại không khớp.")
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
            st.success("Đăng ký và đăng nhập thành công.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Đăng ký thất bại", exc)


def render_auth_page() -> None:
    st.title("Employee Portal")
    st.caption("Đăng nhập hoặc đăng ký tài khoản employee để quản lý profile.")

    login_tab, register_tab = st.tabs(["Đăng nhập", "Đăng ký"])
    with login_tab:
        render_login_tab()
    with register_tab:
        render_register_tab()


def render_skill_chips(skills: list[dict[str, Any]] | None) -> None:
    if not skills:
        st.caption("Chưa có skill.")
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

    summary = employee.get("summary") or "Chưa cập nhật tóm tắt hồ sơ."
    st.markdown(
        f"""
        <div class="linkedin-card">
            <div class="profile-cover"></div>
            <div class="profile-body">
                {avatar_markup}
                <div class="profile-name">{html_or_empty(profile.get("full_name"), "Chưa cập nhật họ tên")}</div>
                <div class="profile-headline">{html_or_empty(employee.get("headline"), "Chưa cập nhật headline")}</div>
                <div class="muted">{html_or_empty(employee.get("current_location"), "Chưa cập nhật địa điểm")} · {html_or_empty(profile.get("email"))}</div>
                <div class="muted">{html_or_empty(profile.get("phone"), "Chưa cập nhật số điện thoại")} · {employee.get("years_of_experience") or 0} năm kinh nghiệm</div>
                <div class="entity-desc">{html_or_empty(summary)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_profile_edit(profile: dict[str, Any]) -> None:
    action_cols = st.columns([1, 1, 8])
    if action_cols[0].button("✎", key="toggle_profile_edit", help="Sửa thông tin chung"):
        st.session_state["editing_profile"] = not st.session_state.get(
            "editing_profile",
            False,
        )
    if action_cols[1].button("↻", key="refresh_profile_top", help="Làm mới profile"):
        try:
            refresh_profile()
            st.success("Đã tải lại profile.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Không tải được profile", exc)

    if not st.session_state.get("editing_profile"):
        return

    employee = profile.get("employee_profile") or {}
    with st.form("profile_edit_form"):
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Họ tên", value=nullable_text(profile.get("full_name")))
            phone = st.text_input("Số điện thoại", value=nullable_text(profile.get("phone")))
            avatar_url = st.text_input(
                "Avatar URL",
                value=nullable_text(profile.get("avatar_url")),
            )
        with col2:
            headline = st.text_input("Headline", value=nullable_text(employee.get("headline")))
            years_of_experience = st.number_input(
                "Số năm kinh nghiệm",
                min_value=0,
                step=1,
                value=int(employee.get("years_of_experience") or 0),
            )
            current_location = st.text_input(
                "Địa điểm hiện tại",
                value=nullable_text(employee.get("current_location")),
            )
        summary = st.text_area("Tóm tắt", value=nullable_text(employee.get("summary")))
        submitted = st.form_submit_button("Lưu thông tin chung", use_container_width=True)

    if submitted:
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
        try:
            update_profile(payload)
            refresh_profile()
            st.session_state["editing_profile"] = False
            st.success("Đã cập nhật thông tin chung.")
            st.rerun()
        except ApiError as exc:
            show_api_error("Không cập nhật được profile", exc)


def experience_payload_form(
    form_key: str,
    item: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bool]:
    item = item or {}
    with st.form(form_key):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Chức danh", value=nullable_text(item.get("title")))
            company_name = st.text_input(
                "Công ty",
                value=nullable_text(item.get("company_name")),
            )
            employment_type = st.text_input(
                "Loại công việc",
                value=nullable_text(item.get("employment_type")),
            )
            location = st.text_input("Địa điểm", value=nullable_text(item.get("location")))
        with col2:
            location_type = st.text_input(
                "Hình thức làm việc",
                value=nullable_text(item.get("location_type")),
            )
            start_date = optional_date_input(
                "Ngày bắt đầu",
                f"{form_key}_start",
                item.get("start_date"),
            )
            end_date = optional_date_input(
                "Ngày kết thúc",
                f"{form_key}_end",
                item.get("end_date"),
            )
            skills = st.text_input("Skills", value=skills_to_text(item.get("skills")))
        description = st.text_area(
            "Mô tả",
            value=nullable_text(item.get("description")),
        )
        submitted = st.form_submit_button("Lưu experience", use_container_width=True)

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
    return payload, submitted


def education_payload_form(
    form_key: str,
    item: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bool]:
    item = item or {}
    with st.form(form_key):
        col1, col2 = st.columns(2)
        with col1:
            school = st.text_input("Trường", value=nullable_text(item.get("school")))
            degree = st.text_input("Bằng cấp", value=nullable_text(item.get("degree")))
            field_of_study = st.text_input(
                "Ngành học",
                value=nullable_text(item.get("field_of_study")),
            )
        with col2:
            start_date = optional_date_input(
                "Ngày bắt đầu",
                f"{form_key}_start",
                item.get("start_date"),
            )
            end_date = optional_date_input(
                "Ngày kết thúc",
                f"{form_key}_end",
                item.get("end_date"),
            )
            skills = st.text_input("Skills", value=skills_to_text(item.get("skills")))
        description = st.text_area("Mô tả", value=nullable_text(item.get("description")))
        submitted = st.form_submit_button("Lưu education", use_container_width=True)

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
    return payload, submitted


def render_experience_item(item: dict[str, Any]) -> None:
    title = item.get("title") or "Chưa cập nhật chức danh"
    company = item.get("company_name") or "Chưa cập nhật công ty"
    employment = item.get("employment_type") or "Chưa cập nhật loại công việc"
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
    school = item.get("school") or "Chưa cập nhật trường"
    degree = item.get("degree") or "Chưa cập nhật bằng cấp"
    field_of_study = item.get("field_of_study") or "Chưa cập nhật ngành học"
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
        header_left, add_col, edit_col = st.columns([8, 1, 1])
        header_left.markdown('<div class="section-title">Experience</div>', unsafe_allow_html=True)
        if add_col.button("+", key="toggle_add_experience", help="Thêm experience"):
            st.session_state["show_add_experience"] = not st.session_state.get(
                "show_add_experience",
                False,
            )
        if edit_col.button("✎", key="toggle_edit_experiences", help="Sửa experience"):
            st.session_state["show_edit_experiences"] = not st.session_state.get(
                "show_edit_experiences",
                False,
            )

        if st.session_state.get("show_add_experience"):
            st.markdown("**Thêm experience**")
            payload, submitted = experience_payload_form("create_experience_form")
            if submitted:
                try:
                    create_experience(payload)
                    refresh_profile()
                    st.session_state["show_add_experience"] = False
                    st.success("Đã thêm experience.")
                    st.rerun()
                except ApiError as exc:
                    show_api_error("Không thêm được experience", exc)

        if not experiences:
            st.markdown('<div class="empty-state">Chưa có experience.</div>', unsafe_allow_html=True)
            return

        for item in experiences:
            render_experience_item(item)

    if not st.session_state.get("show_edit_experiences"):
        return

    st.markdown("#### Sửa Experience")
    for index, item in enumerate(experiences, start=1):
        title = item.get("title") or f"Experience #{index}"
        company = item.get("company_name") or "Chưa cập nhật công ty"
        with st.expander(f"{title} - {company}"):
            delete_col, _ = st.columns([1, 5])
            if delete_col.button(
                "Xóa",
                key=f"delete_experience_{item['experience_id']}",
                use_container_width=True,
            ):
                try:
                    delete_experience(item["experience_id"])
                    refresh_profile()
                    st.success("Đã xóa experience.")
                    st.rerun()
                except ApiError as exc:
                    show_api_error("Không xóa được experience", exc)

            payload, submitted = experience_payload_form(
                f"edit_experience_form_{item['experience_id']}",
                item,
            )
            if submitted:
                try:
                    update_experience(item["experience_id"], payload)
                    refresh_profile()
                    st.success("Đã cập nhật experience.")
                    st.rerun()
                except ApiError as exc:
                    show_api_error("Không cập nhật được experience", exc)


def render_educations(profile: dict[str, Any]) -> None:
    educations = profile.get("educations") or []
    with st.container(border=True):
        header_left, add_col, edit_col = st.columns([8, 1, 1])
        header_left.markdown('<div class="section-title">Education</div>', unsafe_allow_html=True)
        if add_col.button("+", key="toggle_add_education", help="Thêm education"):
            st.session_state["show_add_education"] = not st.session_state.get(
                "show_add_education",
                False,
            )
        if edit_col.button("✎", key="toggle_edit_educations", help="Sửa education"):
            st.session_state["show_edit_educations"] = not st.session_state.get(
                "show_edit_educations",
                False,
            )

        if st.session_state.get("show_add_education"):
            st.markdown("**Thêm education**")
            payload, submitted = education_payload_form("create_education_form")
            if submitted:
                try:
                    create_education(payload)
                    refresh_profile()
                    st.session_state["show_add_education"] = False
                    st.success("Đã thêm education.")
                    st.rerun()
                except ApiError as exc:
                    show_api_error("Không thêm được education", exc)

        if not educations:
            st.markdown('<div class="empty-state">Chưa có education.</div>', unsafe_allow_html=True)
            return

        for item in educations:
            render_education_item(item)

    if not st.session_state.get("show_edit_educations"):
        return

    st.markdown("#### Sửa Education")
    for index, item in enumerate(educations, start=1):
        school = item.get("school") or f"Education #{index}"
        degree = item.get("degree") or "Chưa cập nhật bằng cấp"
        with st.expander(f"{school} - {degree}"):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**Ngành học:** {item.get('field_of_study') or 'N/A'}")
                st.write(
                    f"**Thời gian:** {item.get('start_date') or 'N/A'} - "
                    f"{item.get('end_date') or 'Hiện tại'}"
                )
                st.write(item.get("description") or "Chưa có mô tả.")
                render_skill_chips(item.get("skills"))
            with col2:
                if st.button(
                    "Xóa",
                    key=f"delete_education_{item['education_id']}",
                    use_container_width=True,
                ):
                    try:
                        delete_education(item["education_id"])
                        refresh_profile()
                        st.success("Đã xóa education.")
                        st.rerun()
                    except ApiError as exc:
                        show_api_error("Không xóa được education", exc)

            st.divider()
            payload, submitted = education_payload_form(
                f"edit_education_form_{item['education_id']}",
                item,
            )
            if submitted:
                try:
                    update_education(item["education_id"], payload)
                    refresh_profile()
                    st.success("Đã cập nhật education.")
                    st.rerun()
                except ApiError as exc:
                    show_api_error("Không cập nhật được education", exc)


def render_standalone_skills(profile: dict[str, Any]) -> None:
    skills = profile.get("skills") or []
    with st.container(border=True):
        header_left, add_col, edit_col = st.columns([8, 1, 1])
        header_left.markdown(
            f'<div class="section-title">Skills ({len(skills)})</div>',
            unsafe_allow_html=True,
        )
        if add_col.button("+", key="toggle_add_skill", help="Thêm skill"):
            st.session_state["show_add_skill"] = not st.session_state.get(
                "show_add_skill",
                False,
            )
        if edit_col.button("✎", key="toggle_edit_skills", help="Sửa skill"):
            st.session_state["show_edit_skills"] = not st.session_state.get(
                "show_edit_skills",
                False,
            )

        if st.session_state.get("show_add_skill"):
            with st.form("add_skill_form"):
                skill_name = st.text_input("Thêm skill")
                submitted = st.form_submit_button("Thêm skill", use_container_width=True)
            if submitted:
                if not skill_name.strip():
                    st.warning("Vui lòng nhập tên skill.")
                else:
                    try:
                        add_skill(skill_name.strip())
                        refresh_profile()
                        st.session_state["show_add_skill"] = False
                        st.success("Đã thêm skill.")
                        st.rerun()
                    except ApiError as exc:
                        show_api_error("Không thêm được skill", exc)

        if not skills:
            st.markdown('<div class="empty-state">Chưa có standalone skill.</div>', unsafe_allow_html=True)
            return

        visible_skills = skills if st.session_state.get("show_edit_skills") else skills[:5]
        for skill in visible_skills:
            st.markdown(
                f'<div class="skill-row">{html_or_empty(skill.get("skill_name"))}</div>',
                unsafe_allow_html=True,
            )

        if not st.session_state.get("show_edit_skills") and len(skills) > 5:
            st.caption(f"Show all {len(skills)} skills")

    if not st.session_state.get("show_edit_skills"):
        return

    st.markdown("#### Sửa Skills")
    for skill in skills:
        col1, col2 = st.columns([4, 1])
        col1.write(skill.get("skill_name") or "Unnamed skill")
        if col2.button(
            "Xóa",
            key=f"delete_skill_{skill['skill_id']}",
            use_container_width=True,
        ):
            try:
                delete_skill(skill["skill_id"])
                refresh_profile()
                st.success("Đã xóa skill.")
                st.rerun()
            except ApiError as exc:
                show_api_error("Không xóa được skill", exc)


def render_profile_page() -> None:
    if st.session_state.get("profile") is None:
        try:
            refresh_profile()
        except ApiError as exc:
            show_api_error("Không tải được profile", exc)
            return

    profile = st.session_state["profile"]
    render_profile_summary(profile)
    render_profile_edit(profile)
    render_experiences(profile)
    render_educations(profile)
    render_standalone_skills(profile)


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
