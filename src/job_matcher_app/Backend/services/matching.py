"""
Core matching service.

Score duy nhất: JD Coverage %
  = số JD skills có ít nhất 1 user skill match >= threshold
    / tổng số JD skills

Flow:
  user skills (text)
    → embed on-the-fly (sentence-transformers local)
    → cosine similarity vs JD skill embeddings (pre-computed trong bảng skills)
    → tính coverage %
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.embedder import embed_texts
from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SkillCoverage:
    """Kết quả coverage của 1 JD skill."""
    jd_skill: str
    best_user_skill: str        # user skill gần nhất với JD skill này
    best_similarity: float
    is_covered: bool            # similarity >= threshold


@dataclass
class MatchResult:
    """
    Kết quả matching giữa user skills và 1 JD.
    Primary metric: jd_coverage (%).
    """
    jd_id: int
    jd_title: str | None
    jd_skills: list[str]
    user_skills: list[str]
    coverages: list[SkillCoverage]
    threshold: float

    # JD metadata (optional, từ schema thực tế)
    detail_salary: str | None = None
    detail_location: str | None = None
    detail_experience: str | None = None

    @property
    def covered_count(self) -> int:
        return sum(1 for c in self.coverages if c.is_covered)

    @property
    def jd_coverage_pct(self) -> float:
        """
        % JD skills được cover bởi user.
        Đây là primary score — cao hơn = user phù hợp hơn với JD.
        Range: [0.0, 1.0]
        """
        if not self.coverages:
            return 0.0
        return round(self.covered_count / len(self.coverages), 4)

    @property
    def avg_similarity(self) -> float:
        """Secondary metric: trung bình similarity của best match cho mỗi JD skill."""
        if not self.coverages:
            return 0.0
        return round(float(np.mean([c.best_similarity for c in self.coverages])), 4)

    def to_dict(self) -> dict:
        covered = [c for c in self.coverages if c.is_covered]
        missing = [c for c in self.coverages if not c.is_covered]
        return {
            "jd_id": self.jd_id,
            "jd_title": self.jd_title,
            "jd_info": {
                "salary": self.detail_salary,
                "location": self.detail_location,
                "experience": self.detail_experience,
            },
            "score": {
                "jd_coverage": self.jd_coverage_pct,          # primary
                "jd_coverage_pct_display": f"{self.jd_coverage_pct * 100:.1f}%",
                "covered_skill_count": self.covered_count,
                "total_jd_skill_count": len(self.coverages),
                "avg_similarity": self.avg_similarity,         # secondary
                "threshold": self.threshold,
            },
            "covered_skills": [
                {
                    "jd_skill": c.jd_skill,
                    "matched_by": c.best_user_skill,
                    "similarity": c.best_similarity,
                }
                for c in sorted(covered, key=lambda x: x.best_similarity, reverse=True)
            ],
            "missing_skills": [
                {
                    "jd_skill": c.jd_skill,
                    "closest_user_skill": c.best_user_skill,
                    "similarity": c.best_similarity,
                }
                for c in sorted(missing, key=lambda x: x.best_similarity, reverse=True)
            ],
        }


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

async def _fetch_jd(db: AsyncSession, jd_id: int) -> dict | None:
    """Lấy thông tin JD từ bảng jobs theo schema thực tế."""
    row = (await db.execute(
        text("""
            SELECT id, title, salary_min, salary_max, salary_currency, address, experience_required
            FROM jobs
            WHERE id = :id
        """),
        {"id": jd_id},
    )).fetchone()
    if not row:
        return None
        
    salary = None
    if row.salary_min is not None or row.salary_max is not None:
        salary = f"{row.salary_min or '0'} - {row.salary_max or 'Up'} {row.salary_currency or ''}".strip()
        
    return {
        "id": row.id,
        "title": row.title,
        "salary": salary,
        "location": row.address,
        "experience": str(row.experience_required) if row.experience_required is not None else None,
    }


async def _fetch_jd_skills(db: AsyncSession, jd_id: int) -> list[str]:
    """
    Lấy danh sách skills của JD từ bảng job_skills và skills.
    """
    rows = (await db.execute(
        text("""
            SELECT s.name 
            FROM job_skills js
            JOIN skills s ON js.skill_id = s.id 
            WHERE js.job_id = :jd_id
        """),
        {"jd_id": jd_id},
    )).fetchall()
    if rows:
        return [row.name for row in rows]
    return []


async def _fetch_skill_embeddings(
    db: AsyncSession,
    skill_names: list[str],
) -> dict[str, list[float]]:
    """
    Lấy pre-computed embeddings từ bảng skill_embeddings.
    Skills nào không có trong bảng → thiếu key trong dict trả về.
    """
    if not skill_names:
        return {}
    rows = (await db.execute(
        text("""
            SELECT s.name AS skill_name, se.embedding::text
            FROM skills s
            JOIN skill_embeddings se ON se.skill_id = s.id
            WHERE s.name = ANY(:names)
        """),
        {"names": skill_names},
    )).fetchall()
    result: dict[str, list[float]] = {}
    for row in rows:
        vec = [float(x) for x in row.embedding.strip("[]").split(",")]
        result[row.skill_name] = vec
    return result


# ---------------------------------------------------------------------------
# Core: tính coverage theo chiều JD → User
# ---------------------------------------------------------------------------

def _compute_coverage(
    jd_skills: list[str],
    jd_embs: list[list[float]],
    user_skills: list[str],
    user_embs: list[list[float]],
    threshold: float,
) -> list[SkillCoverage]:
    """
    Với MỖI JD skill, tìm user skill gần nhất.
    → JD skill được "covered" nếu similarity >= threshold.

    Ma trận: (n_jd × n_user) — chiều ngược lại so với user-centric approach.
    """
    J = np.array(jd_embs)    # (n_jd, dim)
    U = np.array(user_embs)  # (n_user, dim)
    sim_matrix = J @ U.T      # (n_jd, n_user)

    coverages = []
    for j_idx, jd_skill in enumerate(jd_skills):
        best_u_idx = int(np.argmax(sim_matrix[j_idx]))
        best_sim = round(float(sim_matrix[j_idx, best_u_idx]), 4)
        coverages.append(SkillCoverage(
            jd_skill=jd_skill,
            best_user_skill=user_skills[best_u_idx],
            best_similarity=best_sim,
            is_covered=best_sim >= threshold,
        ))
    return coverages


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def match_user_to_jd(
    db: AsyncSession,
    user_skills: list[str],
    jd_id: int,
    threshold: float = settings.DEFAULT_THRESHOLD,
) -> MatchResult | None:
    """
    Tính JD Coverage % giữa user skills và 1 JD.
    Returns None nếu jd_id không tồn tại.
    """
    jd_info = await _fetch_jd(db, jd_id)
    if jd_info is None:
        return None

    jd_skills = await _fetch_jd_skills(db, jd_id)
    if not jd_skills:
        logger.warning(f"JD {jd_id} chưa có extracted skills")
        return MatchResult(
            jd_id=jd_id, jd_title=jd_info["title"],
            jd_skills=[], user_skills=user_skills,
            coverages=[], threshold=threshold,
            detail_salary=jd_info["salary"],
            detail_location=jd_info["location"],
            detail_experience=jd_info["experience"],
        )

    # Embed user skills on-the-fly
    user_embs = embed_texts(user_skills)

    # Lấy JD skill embeddings (pre-computed), fallback embed nếu thiếu
    db_emb_map = await _fetch_skill_embeddings(db, jd_skills)
    missing = [s for s in jd_skills if s not in db_emb_map]
    if missing:
        logger.info(f"JD {jd_id}: embed on-the-fly {len(missing)} skills chưa có trong DB")
        for skill, emb in zip(missing, embed_texts(missing)):
            db_emb_map[skill] = emb

    jd_embs = [db_emb_map[s] for s in jd_skills]

    coverages = _compute_coverage(jd_skills, jd_embs, user_skills, user_embs, threshold)

    return MatchResult(
        jd_id=jd_id,
        jd_title=jd_info["title"],
        jd_skills=jd_skills,
        user_skills=user_skills,
        coverages=coverages,
        threshold=threshold,
        detail_salary=jd_info["salary"],
        detail_location=jd_info["location"],
        detail_experience=jd_info["experience"],
    )


async def batch_match_user_to_jds(
    db: AsyncSession,
    user_skills: list[str],
    jd_ids: list[int],
    threshold: float = settings.DEFAULT_THRESHOLD,
) -> list[dict]:
    """
    Match 1 user với nhiều JDs, trả về list sorted theo jd_coverage (cao nhất trước).
    User skills chỉ được embed 1 lần duy nhất.
    """
    user_embs = embed_texts(user_skills)   # embed 1 lần, reuse

    results = []
    for jd_id in jd_ids:
        jd_info = await _fetch_jd(db, jd_id)
        if jd_info is None:
            continue

        jd_skills = await _fetch_jd_skills(db, jd_id)
        if not jd_skills:
            continue

        db_emb_map = await _fetch_skill_embeddings(db, jd_skills)
        missing = [s for s in jd_skills if s not in db_emb_map]
        if missing:
            for skill, emb in zip(missing, embed_texts(missing)):
                db_emb_map[skill] = emb

        jd_embs = [db_emb_map[s] for s in jd_skills]
        coverages = _compute_coverage(jd_skills, jd_embs, user_skills, user_embs, threshold)

        result = MatchResult(
            jd_id=jd_id, jd_title=jd_info["title"],
            jd_skills=jd_skills, user_skills=user_skills,
            coverages=coverages, threshold=threshold,
            detail_salary=jd_info["salary"],
            detail_location=jd_info["location"],
            detail_experience=jd_info["experience"],
        )
        results.append(result.to_dict())

    results.sort(key=lambda r: r["score"]["jd_coverage"], reverse=True)
    return results



async def search_best_jobs_in_db(
    db: AsyncSession,
    user_skills: list[str],
    user_embs: list[list[float]],
    threshold: float = settings.DEFAULT_THRESHOLD,
    limit: int = 100
) -> list[int]:
    """
    Match User (embs) với TOÀN BỘ Jobs trong Database bằng pgvector.
    Cực kỳ nhanh vì không cần kéo bất kì text/vector nào từ DB lên RAM.
    Phiên bản hiệu năng cao: Chỉ trả về danh sách job_id.
    """
    if not user_skills:
        return []

    # 1. Khởi tạo danh sách tham số để đưa vào SQL (User Vectors)
    values_placeholders = ", ".join([
        f"(:name_{i}, :emb_{i}::vector)" for i in range(len(user_skills))
    ])
    
    params = {"threshold": threshold, "limit": limit}
    for i, (name, emb) in enumerate(zip(user_skills, user_embs)):
        params[f"name_{i}"] = name
        params[f"emb_{i}"] = f"[{','.join(map(str, emb))}]"

    # 2. Câu SQL tính toán toàn bộ logic coverage
    # Đã bỏ phần JOIN với bảng `jobs` để SQL chạy nhanh hơn
    query = text(f"""
        -- Bảng tạm chứa User Skills
        WITH user_skills(name, embedding) AS (
            SELECT * FROM (VALUES {values_placeholders}) AS v(name, embedding)
        ),
        -- Tính toán độ tương đồng cho TỪNG SKILL CỦA JOB so với tất cả kĩ năng user
        jd_skill_sims AS (
            SELECT 
                js.job_id,
                s.name as jd_skill,
                MAX(1 - (s.embedding <=> u.embedding)) as best_sim 
            FROM job_skills js
            JOIN skills s ON js.skill_id = s.id
            CROSS JOIN user_skills u
            WHERE s.embedding IS NOT NULL
            GROUP BY js.job_id, s.name
        ),
        -- Gom nhóm theo từng JOB để tính ra JD Coverage %
        job_scores AS (
            SELECT
                job_id,
                COUNT(*) as total_skills,
                SUM(CASE WHEN best_sim >= :threshold THEN 1 ELSE 0 END) as covered_skills,
                AVG(best_sim) as avg_sim
            FROM jd_skill_sims
            GROUP BY job_id
        )
        -- Query cuối cùng: Chỉ lấy job_id và tính toán trực tiếp trên ORDER BY
        SELECT 
            job_id
        FROM job_scores
        WHERE total_skills > 0
        ORDER BY (covered_skills::numeric / total_skills) DESC, avg_sim DESC
        LIMIT :limit;
    """)

    # 3. Yêu cầu Database tính toán và trả kết quả
    rows = (await db.execute(query, params)).fetchall()

    # 4. Trả về trực tiếp một mảng bao gồm các id (ví dụ: [12, 45, 9, 310])
    return [row.job_id for row in rows]













# async def search_best_jobs_in_db(
#     db: AsyncSession,
#     user_skills: list[str],
#     user_embs: list[list[float]],
#     threshold: float = settings.DEFAULT_THRESHOLD,
#     limit: int = 100
# ) -> list[dict]:
#     """
#     Match User (embs) với TOÀN BỘ Jobs trong Database bằng pgvector.
#     Cực kỳ nhanh vì không cần kéo bất kì text/vector nào từ DB lên RAM.
#     """
#     if not user_skills:
#         return []

#     # 1. Khởi tạo danh sách tham số để đưa vào SQL (User Vectors)
#     # Cấu trúc: '(:name_0, :emb_0::vector), (:name_1, :emb_1::vector)...'
#     values_placeholders = ", ".join([
#         f"(:name_{i}, :emb_{i}::vector)" for i in range(len(user_skills))
#     ])
    
#     params = {"threshold": threshold, "limit": limit}
#     for i, (name, emb) in enumerate(zip(user_skills, user_embs)):
#         params[f"name_{i}"] = name
#         # pgvector trong PostgreSQL nhận định dạng string '[0.1, 0.2, ...]'
#         params[f"emb_{i}"] = f"[{','.join(map(str, emb))}]"

#     # 2. Câu SQL tính toán toàn bộ logic coverage
#     query = text(f"""
#         -- Bảng tạm chứa User Skills
#         WITH user_skills(name, embedding) AS (
#             SELECT * FROM (VALUES {values_placeholders}) AS v(name, embedding)
#         ),
#         -- Tính toán độ tương đồng cho TỪNG SKILL CỦA JOB so với tất cả kĩ năng user hiện có
#         jd_skill_sims AS (
#             SELECT 
#                 js.job_id,
#                 s.name as jd_skill,
#                 -- 1 - cosine_distance (<=>) = cosine_similarity
#                 MAX(1 - (s.embedding <=> u.embedding)) as best_sim 
#             FROM job_skills js
#             JOIN skills s ON js.skill_id = s.id
#             CROSS JOIN user_skills u
#             WHERE s.embedding IS NOT NULL
#             GROUP BY js.job_id, s.name
#         ),
#         -- Gom nhóm theo từng JOB để tính ra JD Coverage %
#         job_scores AS (
#             SELECT
#                 job_id,
#                 COUNT(*) as total_skills,
#                 SUM(CASE WHEN best_sim >= :threshold THEN 1 ELSE 0 END) as covered_skills,
#                 AVG(best_sim) as avg_sim
#             FROM jd_skill_sims
#             GROUP BY job_id
#         )
#         -- Join ngược lại bảng jobs để lấy thông tin trả về
#         SELECT 
#             j.id as job_id,
#             j.title,
#             j.salary_min, j.salary_max, j.salary_currency, j.address,
#             js.total_skills,
#             js.covered_skills,
#             (js.covered_skills::numeric / js.total_skills) as coverage_pct,
#             js.avg_sim
#         FROM job_scores js
#         JOIN jobs j ON js.job_id = j.id
#         WHERE js.total_skills > 0
#         ORDER BY coverage_pct DESC, avg_sim DESC
#         LIMIT :limit;
#     """)

#     # 3. Yêu cầu Database tính toán và trả kết quả
#     rows = (await db.execute(query, params)).fetchall()

#     # 4. Map kết quả trả về Front-End
#     results = []
#     for row in rows:
#         results.append({
#             "job_id": row.job_id,
#             "title": row.title,
#             "score": {
#                 "jd_coverage": round(float(row.coverage_pct), 4),
#                 "jd_coverage_pct_display": f"{float(row.coverage_pct) * 100:.1f}%",
#                 "covered_skill_count": int(row.covered_skills),
#                 "total_jd_skill_count": int(row.total_skills),
#                 "avg_similarity": round(float(row.avg_sim), 4),
#                 "threshold": threshold,
#             },
#             # Format thêm các trường như address, salary ...
#         })

#     return results
