from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import MatchJDRequest, BatchMatchRequest, MatchJDResponse
from app.services.matching import match_user_to_jd, batch_match_user_to_jds

router = APIRouter()


@router.post(
    "/match/jd/{jd_id}",
    response_model=MatchJDResponse,
    summary="Match user skills với 1 JD",
    description="""
    Tính **JD Coverage %** — bao nhiêu % skills của JD được cover bởi user skills.

    **Logic:** Với mỗi JD skill, tìm user skill gần nhất (cosine similarity).  
    Nếu similarity >= threshold → JD skill đó được "covered".

    **Response:**
    - `score.jd_coverage` — primary score (0.0 → 1.0)
    - `covered_skills` — các JD skills user đã đáp ứng được
    - `missing_skills` — các JD skills user còn thiếu (để gợi ý upskill)
        """,
)
async def match_to_jd(
    jd_id: int = Path(..., description="ID trong bảng job_descriptions"),
    body: MatchJDRequest = ...,
    db: AsyncSession = Depends(get_db),
):
    result = await match_user_to_jd(
        db=db,
        user_skills=body.user_skills,
        jd_id=jd_id,
        threshold=body.threshold,
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy JD id={jd_id}")
    if not result.jd_skills:
        raise HTTPException(
            status_code=422,
            detail=f"JD {jd_id} chưa có extracted skills trong bảng job_skills",
        )
    return result.to_dict()


@router.post(
    "/match/jds/batch",
    summary="Xếp hạng nhiều JDs theo JD Coverage",
    description="""
Match user skills với nhiều JDs, trả về danh sách **sorted theo jd_coverage** (cao → thấp).

User skills chỉ được embed **1 lần duy nhất**, reuse cho tất cả JDs trong batch.

**Use case:**
- Tìm JD phù hợp nhất cho 1 user profile
- Hiển thị "% match" trên danh sách job listing
    """,
)
async def batch_match(
    body: BatchMatchRequest,
    db: AsyncSession = Depends(get_db),
):
    results = await batch_match_user_to_jds(
        db=db,
        user_skills=body.user_skills,
        jd_ids=body.jd_ids,
        threshold=body.threshold,
    )
    return {
        "user_skills": body.user_skills,
        "threshold": body.threshold,
        "total_matched": len(results),
        "results": results,
    }
