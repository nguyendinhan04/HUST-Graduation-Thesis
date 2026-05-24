from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user
from config import get_settings
from db import get_async_db
from models import User
from services import JobRecommendationService


router = APIRouter(prefix="/jobs", tags=["jobs"])
settings = get_settings()


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
    db: AsyncSession = Depends(get_async_db),
):
    service = JobRecommendationService()

    try:
        return await service.get_job_detail(db=db, job_id=job_id)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
