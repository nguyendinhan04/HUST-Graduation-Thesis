from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_async_db
from services import JobRecommendationService, UserService


router = APIRouter(prefix="/users", tags=["users"])


class CreateEmployeeUserRequest(BaseModel):
    email: str
    password: str
    full_name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    headline: str | None = None
    summary: str | None = None
    years_of_experience: int | None = Field(default=None, ge=0)
    current_location: str | None = None


class UserProfileUpdateRequest(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    headline: str | None = None
    summary: str | None = None
    years_of_experience: int | None = Field(default=None, ge=0)
    current_location: str | None = None
    skills: list[str] = Field(default_factory=list)


class CreateUserEducationRequest(BaseModel):
    school: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    skills: list[str] = Field(default_factory=list)


class UpdateUserEducationRequest(BaseModel):
    school: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    skills: list[str] = Field(default_factory=list)


class CreateUserExperienceRequest(BaseModel):
    title: str | None = None
    company_name: str | None = None
    employment_type: str | None = None
    location: str | None = None
    location_type: str | None = None
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    skills: list[str] = Field(default_factory=list)


class UpdateUserExperienceRequest(BaseModel):
    title: str | None = None
    company_name: str | None = None
    employment_type: str | None = None
    location: str | None = None
    location_type: str | None = None
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    skills: list[str] = Field(default_factory=list)


class UserProfileTfidfVectorRequest(BaseModel):
    Educations: list[dict[str, Any]] = Field(default_factory=list)
    Experiences: list[dict[str, Any]] = Field(default_factory=list)
    Skills: list[str] | str = Field(default_factory=list)


class EmployeeSkillRequest(BaseModel):
    skill_name: str = Field(..., min_length=1)


def _fields_set(payload: BaseModel) -> set[str]:
    return getattr(payload, "model_fields_set", getattr(payload, "__fields_set__", set()))


def _payload_data(payload: BaseModel) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    return payload.dict()


@router.post("/employees", status_code=201)
async def create_employee_user(
    payload: CreateEmployeeUserRequest,
    db: AsyncSession = Depends(get_async_db),
):
    data = _payload_data(payload)

    try:
        return await UserService.create_employee_user_async(
            db=db,
            **data,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 409 if "already exists" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/{user_id}/profile")
async def get_full_user_profile(
    user_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await UserService.get_full_user_profile_async(
            db=db,
            user_id=user_id,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/{user_id}/educations", status_code=201)
async def create_user_education(
    payload: CreateUserEducationRequest,
    user_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_async_db),
):
    data = _payload_data(payload)
    embedding_service = JobRecommendationService()

    try:
        return await UserService.create_user_education_async(
            db=db,
            user_id=user_id,
            embedding_service=embedding_service,
            **data,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/{user_id}/educations/timing", status_code=201)
async def create_user_education_with_timing(
    payload: CreateUserEducationRequest,
    user_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_async_db),
):
    data = _payload_data(payload)
    embedding_service = JobRecommendationService()

    try:
        return await UserService.create_user_education_with_timing_async(
            db=db,
            user_id=user_id,
            embedding_service=embedding_service,
            **data,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.patch("/{user_id}/educations/{education_id}")
async def update_user_education(
    payload: UpdateUserEducationRequest,
    user_id: int = Path(..., ge=1),
    education_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_async_db),
):
    data = _payload_data(payload)
    skills_provided = "skills" in _fields_set(payload)
    skills = data.pop("skills", None)
    embedding_service = JobRecommendationService()

    try:
        return await UserService.update_user_education_async(
            db=db,
            user_id=user_id,
            education_id=education_id,
            embedding_service=embedding_service,
            skills=skills,
            skills_provided=skills_provided,
            **data,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.delete("/{user_id}/educations/{education_id}")
async def delete_user_education(
    user_id: int = Path(..., ge=1),
    education_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_async_db),
):
    embedding_service = JobRecommendationService()

    try:
        return await UserService.delete_user_education_async(
            db=db,
            user_id=user_id,
            education_id=education_id,
            embedding_service=embedding_service,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/{user_id}/experiences", status_code=201)
async def create_user_experience(
    payload: CreateUserExperienceRequest,
    user_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_async_db),
):
    data = _payload_data(payload)
    embedding_service = JobRecommendationService()

    try:
        return await UserService.create_user_experience_async(
            db=db,
            user_id=user_id,
            embedding_service=embedding_service,
            **data,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.patch("/{user_id}/experiences/{experience_id}")
async def update_user_experience(
    payload: UpdateUserExperienceRequest,
    user_id: int = Path(..., ge=1),
    experience_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_async_db),
):
    data = _payload_data(payload)
    skills_provided = "skills" in _fields_set(payload)
    skills = data.pop("skills", None)
    embedding_service = JobRecommendationService()

    try:
        return await UserService.update_user_experience_async(
            db=db,
            user_id=user_id,
            experience_id=experience_id,
            embedding_service=embedding_service,
            skills=skills,
            skills_provided=skills_provided,
            **data,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.delete("/{user_id}/experiences/{experience_id}")
async def delete_user_experience(
    user_id: int = Path(..., ge=1),
    experience_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_async_db),
):
    embedding_service = JobRecommendationService()

    try:
        return await UserService.delete_user_experience_async(
            db=db,
            user_id=user_id,
            experience_id=experience_id,
            embedding_service=embedding_service,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/{user_id}/skills", status_code=201)
async def add_employee_skill(
    payload: EmployeeSkillRequest,
    user_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_async_db),
):
    embedding_service = JobRecommendationService()

    try:
        return await UserService.add_employee_skill_async(
            db=db,
            user_id=user_id,
            embedding_service=embedding_service,
            skill_name=payload.skill_name,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.delete("/{user_id}/skills/{skill_id}")
async def remove_employee_skill(
    user_id: int = Path(..., ge=1),
    skill_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await UserService.remove_employee_skill_async(
            db=db,
            user_id=user_id,
            skill_id=skill_id,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.patch("/{user_id}/profile")
async def update_user_profile(
    payload: UserProfileUpdateRequest,
    user_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_async_db),
):
    data = _payload_data(payload)
    skills_provided = "skills" in _fields_set(payload)
    skills = data.pop("skills", None)

    embedding_service = JobRecommendationService()

    try:
        return await UserService.update_user_profile_async(
            db=db,
            user_id=user_id,
            embedding_service=embedding_service,
            skills=skills,
            skills_provided=skills_provided,
            **data,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.patch("/{user_id}/tfidf-vector")
async def update_user_profile_tfidf_vector(
    payload: UserProfileTfidfVectorRequest,
    user_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_async_db),
):
    data = _payload_data(payload)
    embedding_service = JobRecommendationService()

    try:
        return await embedding_service.update_user_profile_tfidf_vector(
            db=db,
            user_id=user_id,
            profile=data,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
