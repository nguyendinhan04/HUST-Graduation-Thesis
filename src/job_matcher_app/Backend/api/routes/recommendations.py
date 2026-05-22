from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_async_db
from services import JobRecommendationService


router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class RecommendRequest(BaseModel):
    query: str = Field(..., min_length=1)


@router.post("/demo")
async def demo_recommendation(payload: RecommendRequest):
    service = JobRecommendationService()

    try:
        return await service.demo_recommendation_async(payload.query)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc



@router.get("/users/{user_id}/jobs")
async def get_recommendations(
    user_id: int = Path(..., ge=1),
    top_k: int = Query(20, ge=1),
    db: AsyncSession = Depends(get_async_db),
):
    service = JobRecommendationService()

    try:
        job_ids = await service.recommend_jobs_2_phase(
            db=db,
            user_id=user_id,
            top_k=top_k,
        )
        return await service.get_recommended_job_details(db, job_ids)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
