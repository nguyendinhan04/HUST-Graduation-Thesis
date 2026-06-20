from datetime import datetime
from decimal import Decimal
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user
from config import get_settings
from db import get_async_db
from models import User
from services import JobRecommendationService, JobService

try:
    from job_matcher_app.event_outbox import create_event_outbox_in_session
except ImportError:
    from event_outbox import create_event_outbox_in_session  # type: ignore


router = APIRouter(prefix="/jobs", tags=["jobs"])
settings = get_settings()
JobStatus = Literal["open", "closed", "draft", "deleted"]
logger = logging.getLogger(__name__)


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
    status: JobStatus = "open"


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
    status: JobStatus | None = None


def _fields_set(payload: BaseModel) -> set[str]:
    return getattr(payload, "model_fields_set", getattr(payload, "__fields_set__", set()))


def _payload_data(payload: BaseModel) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    return payload.dict()


async def _safe_create_event(
    db: AsyncSession,
    *,
    event_type: str,
    entity_type: str,
    entity_id: int | None,
    user_id: int | None,
    request_id: str | None = None,
    payload: dict | None = None,
) -> None:
    try:
        await create_event_outbox_in_session(
            db,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            request_id=request_id,
            payload=payload or {},
        )
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception(
            "Failed to create event_outbox event_type=%s entity_type=%s entity_id=%s",
            event_type,
            entity_type,
            entity_id,
        )


@router.post("", status_code=201)
async def create_job(
    payload: CreateJobRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    data = _payload_data(payload)
    embedding_service = JobRecommendationService()

    try:
        result = await JobService.create_job_for_employer_async(
            db=db,
            current_user=current_user,
            embedding_service=embedding_service,
            **data,
        )
        await _safe_create_event(
            db,
            event_type="job_created",
            entity_type="job",
            entity_id=result.get("job_id"),
            user_id=current_user.id,
            payload={
                "job_id": result.get("job_id"),
                "company_id": result.get("company_id"),
                "status": result.get("status"),
                "title": result.get("title"),
            },
        )
        return result
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
        result = await JobService.update_job_for_employer_async(
            db=db,
            current_user=current_user,
            embedding_service=embedding_service,
            job_id=job_id,
            fields_set=fields_set,
            **data,
        )
        await _safe_create_event(
            db,
            event_type="job_updated",
            entity_type="job",
            entity_id=job_id,
            user_id=current_user.id,
            payload={
                "job_id": job_id,
                "fields_changed": sorted(fields_set),
                "status": result.get("status"),
                "title": result.get("title"),
            },
        )
        return result
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


@router.get("/me/applications")
async def list_my_applications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await JobService.list_applications_for_employee_async(
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
    recommendation_request_id: str | None = Query(default=None, max_length=255),
    recommendation_rank: int | None = Query(default=None, ge=1),
    algorithm_version: str | None = Query(default=None, max_length=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    try:
        result = await JobService.apply_job_for_employee_async(
            db=db,
            current_user=current_user,
            job_id=job_id,
        )
        await _safe_create_event(
            db,
            event_type="job_application_created",
            entity_type="application",
            entity_id=result.get("application_id"),
            user_id=current_user.id,
            request_id=recommendation_request_id,
            payload={
                "application_id": result.get("application_id"),
                "job_id": job_id,
                "employee_id": result.get("employee_id"),
                "status": result.get("status"),
                "recommendation_request_id": recommendation_request_id,
                "recommendation_rank": recommendation_rank,
                "algorithm_version": algorithm_version,
                "page_context": "job_apply",
            },
        )
        return result
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


@router.get("/{job_id}/applications")
async def list_job_applications(
    job_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await JobService.list_applications_for_employer_job_async(
            db=db,
            current_user=current_user,
            job_id=job_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/{job_id}/skill-gap")
async def get_job_skill_gap(
    job_id: int = Path(..., ge=1),
    threshold: float = Query(0.9, ge=0.0, le=1.0),
    related_threshold: float = Query(0.7, ge=0.0, le=1.0),
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
    recommendation_request_id: str | None = Query(default=None, max_length=255),
    recommendation_rank: int | None = Query(default=None, ge=1),
    algorithm_version: str | None = Query(default=None, max_length=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    service = JobRecommendationService()

    try:
        result = await service.get_job_detail(
            db=db,
            job_id=job_id,
            current_user=current_user,
        )
        if recommendation_request_id:
            await _safe_create_event(
                db,
                event_type="recommendation_click",
                entity_type="job",
                entity_id=job_id,
                user_id=current_user.id,
                request_id=recommendation_request_id,
                payload={
                    "recommendation_request_id": recommendation_request_id,
                    "algorithm_version": algorithm_version,
                    "rank": recommendation_rank,
                    "job_id": job_id,
                    "source": "rrf_rerank",
                    "page_context": "job_detail",
                },
            )
        return result
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
