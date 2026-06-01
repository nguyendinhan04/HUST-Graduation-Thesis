from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import streamlit as st

from frontend_app.api_client import ApiError, apply_job, get_job_detail
from frontend_app.formatting import html_or_empty, show_api_error
from frontend_app.loading import form_loading
from frontend_app.state import navigate_to


def _to_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _compact_decimal(value: Decimal) -> str:
    normalized = value.quantize(Decimal("0.1")) if value != value.to_integral() else value
    return f"{normalized.normalize():f}"


def _format_salary(job: dict[str, Any]) -> str:
    salary_min = _to_decimal(job.get("salary_min"))
    salary_max = _to_decimal(job.get("salary_max"))
    currency = (job.get("salary_currency") or "").upper()
    if salary_min is None and salary_max is None:
        return "Thỏa thuận"

    divisor = (
        Decimal("1000000")
        if currency in {"VND", "VNĐ"} and max(salary_min or 0, salary_max or 0) >= Decimal("1000000")
        else Decimal("1")
    )
    suffix = " triệu" if currency in {"VND", "VNĐ"} else f" {currency}".rstrip()
    if salary_min is not None and salary_max is not None:
        return f"{_compact_decimal(salary_min / divisor)} - {_compact_decimal(salary_max / divisor)}{suffix}"
    if salary_min is not None:
        return f"Từ {_compact_decimal(salary_min / divisor)}{suffix}"
    return f"Đến {_compact_decimal(salary_max / divisor)}{suffix}"


def _format_deadline(value: str | None) -> str:
    if not value:
        return "Không giới hạn"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    return parsed.strftime("%d/%m/%Y")


def _format_experience(value: Any) -> str:
    if value in (None, ""):
        return "Không yêu cầu"
    return f"{value} năm"


def _text_to_bullets(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        return '<div class="job-detail-empty">Chưa có thông tin.</div>'

    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip().lstrip("-•* ").strip()
        if line:
            lines.append(line)

    if len(lines) <= 1:
        return f'<div class="job-detail-paragraph">{html_or_empty(text)}</div>'
    return "<ul>" + "".join(f"<li>{html_or_empty(line)}</li>" for line in lines) + "</ul>"


def _skills_markup(skills: list[dict[str, Any]] | None) -> str:
    if not skills:
        return ""
    items = []
    for skill in skills:
        name = skill.get("skill_name")
        if name:
            items.append(f'<span class="job-detail-skill">{html_or_empty(name)}</span>')
    if not items:
        return ""
    return f'<div class="job-detail-skills">{"".join(items)}</div>'


def _render_job_summary(job: dict[str, Any]) -> None:
    company = job.get("company") or {}
    location = job.get("location") or job.get("location_type") or company.get("location") or "Chưa cập nhật"
    st.markdown(
        f"""
        <div class="job-detail-hero">
            <div class="job-detail-title-row">
                <div class="job-detail-title">{html_or_empty(job.get("title"), "Untitled job")} <span class="job-detail-verified">✓</span></div>
                <div class="job-detail-company">{html_or_empty(company.get("name"), "No company yet")}</div>
            </div>
            <div class="job-detail-stat-grid">
                <div class="job-detail-stat">
                    <div class="job-detail-icon">₫</div>
                    <div>
                        <div class="job-detail-stat-label">Mức lương</div>
                        <div class="job-detail-stat-value">{html_or_empty(_format_salary(job))}</div>
                    </div>
                </div>
                <div class="job-detail-stat">
                    <div class="job-detail-icon">⌖</div>
                    <div>
                        <div class="job-detail-stat-label">Địa điểm</div>
                        <div class="job-detail-stat-value">{html_or_empty(location)}</div>
                    </div>
                </div>
                <div class="job-detail-stat">
                    <div class="job-detail-icon">↻</div>
                    <div>
                        <div class="job-detail-stat-label">Kinh nghiệm</div>
                        <div class="job-detail-stat-value">{html_or_empty(_format_experience(job.get("experience_required")))}</div>
                    </div>
                </div>
            </div>
            <div class="job-detail-deadline">Hạn nộp hồ sơ: {_format_deadline(job.get("deadline"))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_section(title: str, body_markup: str) -> None:
    st.markdown(
        f"""
        <section class="job-detail-section">
            <div class="job-detail-section-title">{html_or_empty(title)}</div>
            <div class="job-detail-section-body">{body_markup}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _load_job_detail(job_id: int) -> dict[str, Any] | None:
    cache_key = f"job_detail_{job_id}"
    if cache_key not in st.session_state:
        try:
            with form_loading("Loading job detail..."):
                st.session_state[cache_key] = get_job_detail(job_id)
        except ApiError as exc:
            show_api_error("Could not load job detail", exc)
            return None
    return st.session_state.get(cache_key)


def _handle_apply(job_id: int) -> None:
    try:
        with form_loading("Submitting application..."):
            apply_job(job_id)
        st.session_state[f"job_apply_success_{job_id}"] = True
    except ApiError as exc:
        message = str(exc)
        if "already applied" in message.lower():
            st.warning("Bạn đã ứng tuyển công việc này.")
        else:
            show_api_error("Could not apply for this job", exc)


def render_job_detail_page() -> None:
    job_id = st.session_state.get("selected_job_id")
    if not job_id:
        st.warning("Chưa chọn công việc để xem chi tiết.")
        if st.button("Quay lại danh sách", key="job_detail_missing_back"):
            navigate_to("recommendations")
            st.rerun()
        return

    back_col, _ = st.columns([1.4, 8])
    if back_col.button("← Quay lại", key="job_detail_back", use_container_width=True):
        navigate_to("recommendations")
        st.rerun()

    job = _load_job_detail(int(job_id))
    if not job:
        return

    _render_job_summary(job)

    apply_col, save_col = st.columns([6.8, 1.6], gap="small")
    if apply_col.button("Ứng tuyển ngay", key=f"job_apply_{job_id}", type="primary", use_container_width=True):
        _handle_apply(int(job_id))
    if save_col.button("♡ Lưu tin", key=f"job_save_{job_id}", use_container_width=True):
        st.info("Tính năng lưu tin chưa được backend hỗ trợ.")

    if st.session_state.get(f"job_apply_success_{job_id}"):
        st.success("Ứng tuyển thành công. Hồ sơ của bạn đã được gửi tới nhà tuyển dụng.")

    _render_section("Mô tả công việc", _text_to_bullets(job.get("description")))
    _render_section("Yêu cầu ứng viên", _text_to_bullets(job.get("requirement")) + _skills_markup(job.get("skills")))
    _render_section("Quyền lợi", _text_to_bullets(job.get("benefit")))
