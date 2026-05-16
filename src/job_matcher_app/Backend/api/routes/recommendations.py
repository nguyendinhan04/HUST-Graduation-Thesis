from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

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



