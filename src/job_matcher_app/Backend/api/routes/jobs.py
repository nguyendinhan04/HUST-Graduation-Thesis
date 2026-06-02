from datetime import datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user
from config import get_settings
from db import get_async_db
from models import User
from services import JobRecommendationService, JobService


router = APIRouter(prefix="/jobs", tags=["jobs"])
settings = get_settings()


class CreateJobRequest(BaseModel):
    title: str = Field(..., min_length=1)
    description: str | None = None
    requirement: str | None = None
    benefit: str | None = None
    salary_min: Decimal | None = Field(default=None, ge=0)
    salary_max: Decimal | None = Field(default=None, ge=0)
    salary_currency: str | None = None
    experience_required: int | None = Field(default=None, ge=0)
    employment_type: str | None = None
    working_time: str | None = None
    location_type: str | None = None
    address: str | None = None
    deadline: datetime | None = None
    status: Literal["open", "closed", "draft"] = "open"


class UpdateJobRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    description: str | None = None
    requirement: str | None = None
    benefit: str | None = None
    salary_min: Decimal | None = Field(default=None, ge=0)
    salary_max: Decimal | None = Field(default=None, ge=0)
    salary_currency: str | None = None
    experience_required: int | None = Field(default=None, ge=0)
    employment_type: str | None = None
    working_time: str | None = None
    location_type: str | None = None
    address: str | None = None
    deadline: datetime | None = None
    status: Literal["open", "closed", "draft", "deleted"] | None = None


def _fields_set(payload: BaseModel) -> set[str]:
    return getattr(payload, "model_fields_set", getattr(payload, "__fields_set__", set()))


def _payload_data(payload: BaseModel) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    return payload.dict()


@router.post("", status_code=201)
async def create_job(
    payload: CreateJobRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    data = _payload_data(payload)
    embedding_service = JobRecommendationService()

    try:
        return await JobService.create_job_for_employer_async(
            db=db,
            current_user=current_user,
            embedding_service=embedding_service,
            **data,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("")
async def search_jobs(
    q: str | None = Query(default=None, max_length=100),
    location: str | None = Query(default=None, max_length=100),
    employment_type: str | None = Query(default=None, max_length=50),
    max_experience: int | None = Query(default=None, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await JobService.search_open_jobs_async(
            db=db,
            current_user=current_user,
            query=q,
            location=location,
            employment_type=employment_type,
            max_experience=max_experience,
            page=page,
            page_size=page_size,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.patch("/{job_id}")
async def update_job(
    payload: UpdateJobRequest,
    job_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    data = _payload_data(payload)
    fields_set = _fields_set(payload)
    embedding_service = JobRecommendationService()

    try:
        return await JobService.update_job_for_employer_async(
            db=db,
            current_user=current_user,
            embedding_service=embedding_service,
            job_id=job_id,
            fields_set=fields_set,
            **data,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/me/employer")
async def list_my_employer_jobs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await JobService.list_jobs_for_employer_async(
            db=db,
            current_user=current_user,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/{job_id}/apply", status_code=201)
async def apply_job(
    job_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await JobService.apply_job_for_employee_async(
            db=db,
            current_user=current_user,
            job_id=job_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        message = str(exc)
        lower_message = message.lower()
        if "already applied" in lower_message:
            status_code = 409
        elif "not found" in lower_message:
            status_code = 404
        else:
            status_code = 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/{job_id}/skill-gap")
async def get_job_skill_gap(
    job_id: int = Path(..., ge=1),
    threshold: float = Query(0.6, ge=0.0, le=1.0),
    related_threshold: float = Query(0.35, ge=0.0, le=1.0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    service = JobRecommendationService()

    try:
        return await service.get_job_skill_gap(
            db=db,
            job_id=job_id,
            user_id=current_user.id,
            threshold=threshold,
            related_threshold=related_threshold,
        )
    except ValueError as exc:
        message = str(exc)
        lower_message = message.lower()
        if "not found" in lower_message:
            status_code = 404
        elif "no skills in job_skills" in lower_message:
            status_code = 422
        else:
            status_code = 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/{job_id}")
async def get_job_detail(
    job_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    service = JobRecommendationService()

    try:
        return await service.get_job_detail(
            db=db,
            job_id=job_id,
            current_user=current_user,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
