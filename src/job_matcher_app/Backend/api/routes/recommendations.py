import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user
from models import User
from db import get_async_db
from services import JobRecommendationService, RecommendationLockedError

try:
    from job_matcher_app.event_outbox import create_event_outbox_in_session
except ImportError:
    from event_outbox import create_event_outbox_in_session  # type: ignore


router = APIRouter(prefix="/recommendations", tags=["recommendations"])
logger = logging.getLogger(__name__)
RECOMMENDATION_ALGORITHM_VERSION = "rrf_rerank_v1"


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


def _handle_value_error(exc: ValueError) -> HTTPException:
    message = str(exc)
    msg_lower = message.lower()
    is_missing_profile = "not found" in msg_lower and ("employee" in msg_lower or "profile" in msg_lower)
    is_missing_vectors = "bert vectors are not ready" in msg_lower
    
    if is_missing_profile or is_missing_vectors:
        return HTTPException(
            status_code=400,
            detail="Vui lòng tạo và cập nhật hồ sơ cá nhân (user profile) đầy đủ trước khi nhận gợi ý việc làm."
        )
    status_code = 404 if "not found" in msg_lower else 400
    return HTTPException(status_code=status_code, detail=message)


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
        recommendation_request_id = str(uuid.uuid4())
        job_ids = await service.recommend_jobs_2_phase(
            db=db,
            user_id=user_id,
            top_k=top_k,
        )
        details = await service.get_recommended_job_details(db, job_ids)
        for rank, item in enumerate(details, start=1):
            item["recommendation_request_id"] = recommendation_request_id
            item["recommendation_rank"] = rank
            item["algorithm_version"] = RECOMMENDATION_ALGORITHM_VERSION

        try:
            for rank, item in enumerate(details, start=1):
                job_id = int(item.get("id") or item.get("job_id"))
                await create_event_outbox_in_session(
                    db,
                    event_type="recommendation_impression",
                    entity_type="job",
                    entity_id=job_id,
                    user_id=user_id,
                    request_id=recommendation_request_id,
                    payload={
                        "recommendation_request_id": recommendation_request_id,
                        "algorithm_version": RECOMMENDATION_ALGORITHM_VERSION,
                        "rank": rank,
                        "job_id": job_id,
                        "top_k": top_k,
                        "source": "rrf_rerank",
                        "page_context": "recommendation_home",
                    },
                )
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception(
                "Failed to create recommendation impression events user_id=%s",
                user_id,
            )

        return details
    except RecommendationLockedError as exc:
        raise _recommendation_locked_http_exception(exc) from exc
    except ValueError as exc:
        raise _handle_value_error(exc) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/me/jobs/bm25")
async def get_bm25_recommendation_ids(
    current_user: User = Depends(get_current_user),
    top_k: int = Query(20, ge=1),
    db: AsyncSession = Depends(get_async_db),
) -> list[int]:
    user_id = current_user.id
    service = JobRecommendationService()

    try:
        return await service.search_best_jobs_in_db_by_bm25(
            db=db,
            user_id=user_id,
            limit=top_k,
        )
    except RecommendationLockedError as exc:
        raise _recommendation_locked_http_exception(exc) from exc
    except ValueError as exc:
        raise _handle_value_error(exc) from exc
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
        raise _handle_value_error(exc) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
