from fastapi import APIRouter, Depends, HTTPException, Path, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_async_db
from services import JobRecommendationService, UserService


router = APIRouter(prefix="/users", tags=["users"])


class UserProfileUpdateRequest(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    headline: str | None = None
    summary: str | None = None
    years_of_experience: int | None = None
    current_location: str | None = None
    skills: list[str] | None = None


def _fields_set(payload: BaseModel) -> set[str]:
    return getattr(payload, "model_fields_set", getattr(payload, "__fields_set__", set()))


def _payload_data(payload: BaseModel) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    return payload.dict()


@router.patch("/{user_id}/profile")
async def update_user_profile(
    payload: UserProfileUpdateRequest,
    request: Request,
    user_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_async_db),
):
    data = _payload_data(payload)
    skills_provided = "skills" in _fields_set(payload)
    skills = data.pop("skills", None)

    embedding_service = JobRecommendationService(
        skill_embedding_model=getattr(request.app.state, "skill_embedding_model", None),
        tfidf_model=getattr(request.app.state, "tfidf_model", None),
    )

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
