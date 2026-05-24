from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user
from models import User
from db import get_async_db
from services import JobRecommendationService, RecommendationLockedError


router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class RecommendRequest(BaseModel):
    query: str = Field(..., min_length=1)


def _recommendation_locked_http_exception(exc: RecommendationLockedError) -> HTTPException:
    return HTTPException(
        status_code=423,
        detail={
            "code": exc.code,
            "status": "locked",
            "message": str(exc),
        },
    )


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



@router.get("/me/jobs")
async def get_recommendations(
    current_user: User = Depends(get_current_user),
    top_k: int = Query(20, ge=1),
    db: AsyncSession = Depends(get_async_db),
):
    user_id = current_user.id
    service = JobRecommendationService()

    try:
        job_ids = await service.recommend_jobs_2_phase(
            db=db,
            user_id=user_id,
            top_k=top_k,
        )
        return await service.get_recommended_job_details(db, job_ids)
    except RecommendationLockedError as exc:
        raise _recommendation_locked_http_exception(exc) from exc
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/me/jobs/tfidf")
async def get_tfidf_recommendation_ids(
    current_user: User = Depends(get_current_user),
    top_k: int = Query(20, ge=1),
    db: AsyncSession = Depends(get_async_db),
) -> list[int]:
    user_id = current_user.id
    service = JobRecommendationService()

    try:
        return await service.search_best_jobs_in_db_by_tfidf(
            db=db,
            user_id=user_id,
            limit=top_k,
        )
    except RecommendationLockedError as exc:
        raise _recommendation_locked_http_exception(exc) from exc
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/me/jobs/bert")
async def get_bert_recommendation_ids(
    current_user: User = Depends(get_current_user),
    top_k: int = Query(20, ge=1),
    db: AsyncSession = Depends(get_async_db),
) -> list[int]:
    user_id = current_user.id
    service = JobRecommendationService()

    try:
        return await service.search_best_jobs_in_db_by_bert(
            db=db,
            user_id=user_id,
            limit=top_k,
        )
    except RecommendationLockedError as exc:
        raise _recommendation_locked_http_exception(exc) from exc
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
