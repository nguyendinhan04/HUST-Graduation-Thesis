from __future__ import annotations

import os
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

    top_left, top_right = st.columns([1, 3])
    with top_left:
        avatar_url = nullable_text(profile.get("avatar_url")).strip()
        if avatar_url:
            st.image(avatar_url, width=120)
        else:
            st.info("Chưa có avatar")
    with top_right:
        st.subheader(profile.get("full_name") or "Chưa cập nhật họ tên")
        st.caption(profile.get("email") or "")
        st.write(employee.get("headline") or "Chưa cập nhật headline")

        c1, c2, c3 = st.columns(3)
        c1.metric("Kinh nghiệm", employee.get("years_of_experience") or 0)
        c2.metric("Địa điểm", employee.get("current_location") or "N/A")
        c3.metric("Role", profile.get("role") or "employee")

    with st.container(border=True):
        st.write("**Thông tin chung**")
        col1, col2 = st.columns(2)
        col1.write(f"**Số điện thoại:** {profile.get('phone') or 'Chưa cập nhật'}")
        col2.write(f"**Cập nhật:** {profile.get('updated_at') or 'Chưa có'}")
        st.write("**Tóm tắt**")
        st.write(employee.get("summary") or "Chưa cập nhật tóm tắt hồ sơ.")


def render_profile_edit(profile: dict[str, Any]) -> None:
    if st.button("Sửa thông tin chung"):
        st.session_state["editing_profile"] = not st.session_state.get(
            "editing_profile",
            False,
        )

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


def render_experiences(profile: dict[str, Any]) -> None:
    st.subheader("Experience")
    experiences = profile.get("experiences") or []

    with st.expander("Thêm experience"):
        payload, submitted = experience_payload_form("create_experience_form")
        if submitted:
            try:
                create_experience(payload)
                refresh_profile()
                st.success("Đã thêm experience.")
                st.rerun()
            except ApiError as exc:
                show_api_error("Không thêm được experience", exc)

    if not experiences:
        st.info("Chưa có experience.")
        return

    for index, item in enumerate(experiences, start=1):
        title = item.get("title") or f"Experience #{index}"
        company = item.get("company_name") or "Chưa cập nhật công ty"
        with st.expander(f"{title} - {company}"):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**Loại công việc:** {item.get('employment_type') or 'N/A'}")
                st.write(f"**Địa điểm:** {item.get('location') or 'N/A'}")
                st.write(f"**Hình thức:** {item.get('location_type') or 'N/A'}")
                st.write(
                    f"**Thời gian:** {item.get('start_date') or 'N/A'} - "
                    f"{item.get('end_date') or 'Hiện tại'}"
                )
                st.write(item.get("description") or "Chưa có mô tả.")
                render_skill_chips(item.get("skills"))
            with col2:
                if st.button(
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

            st.divider()
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
    st.subheader("Education")
    educations = profile.get("educations") or []

    with st.expander("Thêm education"):
        payload, submitted = education_payload_form("create_education_form")
        if submitted:
            try:
                create_education(payload)
                refresh_profile()
                st.success("Đã thêm education.")
                st.rerun()
            except ApiError as exc:
                show_api_error("Không thêm được education", exc)

    if not educations:
        st.info("Chưa có education.")
        return

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
    st.subheader("Skill")
    skills = profile.get("skills") or []

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
                st.success("Đã thêm skill.")
                st.rerun()
            except ApiError as exc:
                show_api_error("Không thêm được skill", exc)

    if not skills:
        st.info("Chưa có standalone skill.")
        return

    for skill in skills:
        col1, col2 = st.columns([4, 1])
        col1.write(f"`{skill.get('skill_name')}`")
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
    st.title("Profile Employee")

    if st.session_state.get("profile") is None:
        try:
            refresh_profile()
        except ApiError as exc:
            show_api_error("Không tải được profile", exc)
            return

    profile = st.session_state["profile"]
    render_profile_summary(profile)
    render_profile_edit(profile)

    profile_tab, experience_tab, education_tab, skill_tab = st.tabs(
        ["Tổng quan", "Experience", "Education", "Skill"],
    )
    with profile_tab:
        render_skill_chips(profile.get("skills"))
    with experience_tab:
        render_experiences(profile)
    with education_tab:
        render_educations(profile)
    with skill_tab:
        render_standalone_skills(profile)


def main() -> None:
    st.set_page_config(
        page_title="Employee Profile",
        page_icon="E",
        layout="wide",
    )
    init_session_state()
    sidebar()

    if st.session_state.get("access_token"):
        render_profile_page()
    else:
        render_auth_page()


if __name__ == "__main__":
    main()
