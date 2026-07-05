from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import streamlit as st

from frontend_app.api_client import ApiError, apply_job, get_job_detail, get_job_skill_gap, get_my_applications
from frontend_app.formatting import html_or_empty, show_api_error
from frontend_app.loading import form_loading
from frontend_app.state import navigate_to


JOB_APPLY_EXPIRED_MESSAGE = "Job đã quá hạn ứng tuyển."


@st.dialog("Ứng tuyển không thành công", dismissible=True)
def job_apply_error_dialog() -> None:
    message = st.session_state.get("job_apply_error_message") or "Không thể ứng tuyển công việc này."
    st.markdown(
        f"""
        <div class="job-apply-error-dialog">
            <div class="job-apply-error-title">Không thể ứng tuyển</div>
            <div class="job-apply-error-message">{html_or_empty(message)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _, close_col = st.columns([4, 1.4])
    if close_col.button("Đóng", key="job_apply_error_close", type="primary", use_container_width=True):
        st.session_state.pop("job_apply_error_message", None)
        st.rerun()


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


def _parse_deadline(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_application_expired(job: dict[str, Any]) -> bool:
    deadline = _parse_deadline(job.get("deadline"))
    if deadline is None:
        return False
    now = datetime.now(deadline.tzinfo) if deadline.tzinfo else datetime.now()
    return deadline < now


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


def _missing_skill_chips(skills: list[dict[str, Any]] | None) -> str:
    if not skills:
        return '<div class="skill-gap-complete">Bạn đã cover toàn bộ kỹ năng yêu cầu.</div>'

    chips = []
    for skill in skills:
        name = skill.get("job_skill_name")
        if name:
            chips.append(f'<span class="skill-gap-missing-chip">{html_or_empty(name)}</span>')
    if not chips:
        return '<div class="skill-gap-complete">Bạn đã cover toàn bộ kỹ năng yêu cầu.</div>'
    return f'<div class="skill-gap-chip-row">{"".join(chips)}</div>'


def _coverage_width(value: Any) -> int:
    try:
        coverage = float(value)
    except (TypeError, ValueError):
        coverage = 0.0
    return max(0, min(int(round(coverage * 100)), 100))


def _skill_gap_error_message(message: str | None) -> str:
    lower_message = (message or "").lower()
    if "no skills in job_skills" in lower_message:
        return "Công việc này chưa có dữ liệu kỹ năng để tính skill gap."
    if "profile has no skills" in lower_message:
        return "Hồ sơ của bạn chưa có kỹ năng để tính skill gap."
    return "Chưa thể tải skill gap cho công việc này."


def _render_job_summary(job: dict[str, Any]) -> None:
    company = job.get("company") or {}
    location = job.get("location") or job.get("location_type") or company.get("location") or "Chưa cập nhật"
    st.markdown(
        f"""
        <div class="job-detail-hero">
            <div class="job-detail-title-row">
                <div class="job-detail-title">{html_or_empty(job.get("title"), "Untitled job")}</div>
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


def _recommendation_context_cache_suffix(recommendation_context: dict[str, Any] | None) -> str:
    if not recommendation_context:
        return "direct"
    request_id = recommendation_context.get("recommendation_request_id") or "unknown"
    rank = recommendation_context.get("recommendation_rank") or "none"
    return f"rec_{request_id}_{rank}"


def _selected_recommendation_context() -> dict[str, Any] | None:
    context = st.session_state.get("selected_job_recommendation_context")
    return context if isinstance(context, dict) and context else None


def _load_job_detail(job_id: int, recommendation_context: dict[str, Any] | None = None) -> dict[str, Any] | None:
    cache_key = f"job_detail_{job_id}_{_recommendation_context_cache_suffix(recommendation_context)}"
    if cache_key not in st.session_state:
        try:
            with form_loading("Loading job detail..."):
                st.session_state[cache_key] = get_job_detail(job_id, recommendation_context=recommendation_context)
        except ApiError as exc:
            show_api_error("Could not load job detail", exc)
            return None
    return st.session_state.get(cache_key)


def _load_job_skill_gap(job_id: int) -> dict[str, Any] | None:
    cache_key = f"job_skill_gap_{job_id}"
    error_key = f"job_skill_gap_error_{job_id}"
    if cache_key not in st.session_state and error_key not in st.session_state:
        try:
            with form_loading("Loading skill gap..."):
                st.session_state[cache_key] = get_job_skill_gap(job_id)
        except ApiError as exc:
            st.session_state[error_key] = str(exc)
            return None
    return st.session_state.get(cache_key)


def _render_skill_gap(job_id: int) -> None:
    gap = _load_job_skill_gap(job_id)
    if gap is None:
        error = st.session_state.get(f"job_skill_gap_error_{job_id}")
        _render_section(
            "Skill gap",
            f'<div class="skill-gap-info">{html_or_empty(_skill_gap_error_message(error))}</div>',
        )
        return

    score = gap.get("score") or {}
    coverage_display = score.get("coverage_display") or "0.0%"
    coverage_width = _coverage_width(score.get("coverage"))
    covered_count = score.get("covered_skill_count") or 0
    related_count = score.get("related_skill_count") or 0
    missing_count = score.get("missing_skill_count") or 0
    total_count = score.get("total_job_skill_count") or 0

    _render_section(
        "Skill gap",
        f"""
        <div class="skill-gap-summary">
            <div>
                <div class="skill-gap-label">Profile coverage</div>
                <div class="skill-gap-score">{html_or_empty(coverage_display)}</div>
            </div>
            <div class="skill-gap-count-grid">
                <div class="skill-gap-count"><span>{html_or_empty(covered_count)}</span> Covered</div>
                <div class="skill-gap-count"><span>{html_or_empty(related_count)}</span> Related</div>
                <div class="skill-gap-count"><span>{html_or_empty(missing_count)}</span> Missing</div>
                <div class="skill-gap-count"><span>{html_or_empty(total_count)}</span> Required</div>
            </div>
        </div>
        <div class="skill-gap-progress" aria-label="Skill gap coverage">
            <div class="skill-gap-progress-fill" style="width: {coverage_width}%"></div>
        </div>
        <div class="skill-gap-missing-title">Kỹ năng còn thiếu</div>
        {_missing_skill_chips(gap.get("missing_skills"))}
        """,
    )


def _handle_apply(job_id: int, recommendation_context: dict[str, Any] | None = None) -> None:
    try:
        with form_loading("Submitting application..."):
            apply_job(job_id, recommendation_context=recommendation_context)
        st.session_state[f"job_apply_success_{job_id}"] = True
        st.session_state.pop("my_applications", None)
        st.rerun()
    except ApiError as exc:
        message = str(exc)
        if "already applied" in message.lower():
            st.session_state[f"job_apply_success_{job_id}"] = True
            st.session_state.pop("my_applications", None)
            st.rerun()
        elif "deadline has passed" in message.lower() or "quá hạn" in message.lower():
            st.session_state["job_apply_error_message"] = JOB_APPLY_EXPIRED_MESSAGE
        else:
            show_api_error("Could not apply for this job", exc)


def _has_user_applied(job_id: int) -> bool:
    if st.session_state.get("user_role") != "employee":
        return False

    if st.session_state.get(f"job_apply_success_{job_id}"):
        return True

    debug_logs = []
    has_applied = False

    try:
        fresh_apps = get_my_applications()
        debug_logs.append(f"**Target job_id:** `{job_id}` (type: `{type(job_id).__name__}`)")
        debug_logs.append(f"**Fetched applications type:** `{type(fresh_apps).__name__}`")
        
        if isinstance(fresh_apps, list):
            debug_logs.append(f"**Total applications found:** `{len(fresh_apps)}`")
            for app in fresh_apps:
                app_job_id = app.get("job_id")
                if not app_job_id:
                    job = app.get("job") or {}
                    app_job_id = job.get("job_id") or job.get("id")
                    
                debug_logs.append(f"- Checking `app_job_id`: `{app_job_id}` (type: `{type(app_job_id).__name__}`) against `{job_id}`")
                
                if str(app_job_id) == str(job_id):
                    debug_logs.append("✅ **MATCH FOUND!**")
                    has_applied = True
                    break
        else:
            debug_logs.append(f"**RAW RESPONSE:** `{fresh_apps}`")
            
        if not has_applied:
            debug_logs.append("❌ **NO MATCH FOUND.**")
            
    except ApiError as e:
        debug_logs.append(f"❌ **API ERROR:** `{e}`")

    # Hiển thị log ra thanh sidebar bên trái của giao diện web
    with st.sidebar.expander("🛠️ DEBUG: Kiểm tra ứng tuyển", expanded=True):
        for log in debug_logs:
            st.markdown(log)

    return has_applied


def render_job_detail_page() -> None:
    job_id = st.session_state.get("selected_job_id")
    return_page = st.session_state.get("selected_job_return_page") or "recommendations"
    if not job_id:
        st.warning("Chưa chọn công việc để xem chi tiết.")
        if st.button("Quay lại danh sách", key="job_detail_missing_back"):
            navigate_to(return_page)
            st.rerun()
        return

    back_col, _ = st.columns([1.4, 8])
    if back_col.button("← Quay lại", key="job_detail_back", use_container_width=True):
        navigate_to(return_page)
        st.rerun()

    recommendation_context = _selected_recommendation_context()
    job = _load_job_detail(int(job_id), recommendation_context=recommendation_context)
    if not job:
        return

    _render_job_summary(job)

    is_expired = _is_application_expired(job)
    has_applied = _has_user_applied(int(job_id))
    
    apply_col, _ = st.columns([3, 5], gap="small")
    
    button_text = "Ứng tuyển ngay"
    button_disabled = False
    
    if has_applied:
        button_text = "Đã ứng tuyển"
        button_disabled = True
    elif is_expired:
        button_text = "Đã quá hạn ứng tuyển"
        button_disabled = True
        
    if apply_col.button(
        button_text,
        key=f"job_apply_{job_id}",
        type="primary",
        use_container_width=True,
        disabled=button_disabled,
    ):
        _handle_apply(int(job_id), recommendation_context=recommendation_context)
        
    if has_applied:
        pass
    elif is_expired:
        st.caption("Job đã quá hạn ứng tuyển.")

    if st.session_state.get(f"job_apply_success_{job_id}"):
        st.success("Ứng tuyển thành công. Hồ sơ của bạn đã được gửi tới nhà tuyển dụng.")
    if st.session_state.get("job_apply_error_message"):
        job_apply_error_dialog()

    skill_gap_placeholder = st.empty()

    _render_section("Mô tả công việc", _text_to_bullets(job.get("description")))
    _render_section("Yêu cầu ứng viên", _text_to_bullets(job.get("requirement")) + _skills_markup(job.get("skills")))
    _render_section("Quyền lợi", _text_to_bullets(job.get("benefit")))

    with skill_gap_placeholder.container():
        _render_skill_gap(int(job_id))
