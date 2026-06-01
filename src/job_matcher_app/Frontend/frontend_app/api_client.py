from __future__ import annotations

from typing import Any

import requests
import streamlit as st

from frontend_app.state import api_base_url, auth_headers


class ApiError(Exception):
    """Raised when the backend returns an unsuccessful response."""



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
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    auth: bool = False,
) -> Any:
    headers = auth_headers() if auth else {}
    try:
        response = requests.request(
            method,
            f"{api_base_url()}{path}",
            params=params,
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


def get_recommended_jobs(top_k: int = 20) -> Any:
    return request_json(
        "GET",
        f"/recommendations/me/jobs?top_k={top_k}",
        auth=True,
    )


def search_jobs(
    query: str | None = None,
    location: str | None = None,
    employment_type: str | None = None,
    max_experience: int | None = None,
    limit: int = 30,
) -> Any:
    params: dict[str, Any] = {"limit": limit}
    if query:
        params["q"] = query
    if location:
        params["location"] = location
    if employment_type:
        params["employment_type"] = employment_type
    if max_experience is not None:
        params["max_experience"] = max_experience
    return request_json("GET", "/jobs", params=params, auth=True)


def get_job_detail(job_id: int) -> Any:
    return request_json("GET", f"/jobs/{job_id}", auth=True)


def apply_job(job_id: int) -> Any:
    return request_json("POST", f"/jobs/{job_id}/apply", auth=True)

