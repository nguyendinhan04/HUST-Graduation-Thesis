from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from services import JobRecommendationService


router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class RecommendRequest(BaseModel):
    query: str = Field(..., min_length=1)
    model: str = Field("tfidf", pattern="^(tfidf|bert)$")


@router.post("/demo")
async def demo_recommendation(payload: RecommendRequest, request: Request):
    service = JobRecommendationService(
        tfidf_model=request.app.state.tfidf_model,
    )

    try:
        return await service.demo_recommendation_async(payload.query, payload.model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
