from __future__ import annotations

import re
import os
import asyncio
import numpy as np
from redis import Redis
from rq import Queue
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config import get_settings
from models import (
    Education,
    EducationSkill,
    Employee,
    EmployeeSkill,
    Experience,
    ExperienceSkill,
    Skill,
)


class JobRecommendationService:
    def __init__(self):
        # Redis & RQ setup để push task embedding sang Worker
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", 6379))
        self.redis_db = int(os.getenv("REDIS_DB", 0))
        self.redis_password = os.getenv("REDIS_PASSWORD", None)
        
        self.redis_conn = Redis(
            host=self.redis_host, 
            port=self.redis_port, 
            db=self.redis_db, 
            password=self.redis_password
        )
        self.skill_queue = Queue("skill-embedding-queue", connection=self.redis_conn)
        self.tfidf_queue = Queue(
            os.getenv("TFIDF_QUEUE_NAME", "profile-tfidf-queue"),
            connection=self.redis_conn,
        )

    @staticmethod
    def _to_pgvector_literal(vector) -> str:
        if hasattr(vector, "tolist"):
            vector = vector.tolist()

        vector = np.asarray(vector).reshape(-1)
        return "[" + ",".join(str(float(value)) for value in vector) + "]"

    async def demo_recommendation_async(self, query: str):
        embeddings = await self.embed_bert_texts([query])
        vector = np.asarray(embeddings)
        return {
            "model": "bert",
            "query": query,
            "vector_shape": list(vector.shape),
            "status": "ok",
        }

    async def _wait_for_job(self, job, failure_message: str):
        while not job.is_finished:
            if job.is_failed:
                raise Exception(f"{failure_message}: {job.exc_info}")
            await asyncio.sleep(0.5)
            job.refresh()

        return job.result

    async def embed_bert_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        job = self.skill_queue.enqueue(
            "job_matcher_app.skill_worker.embed_bert_texts_task",
            texts,
            job_timeout="10m",
        )
        return await self._wait_for_job(job, "BERT Embedding Job in RQ worker failed")

    async def embed_bert_documents(
        self,
        texts: list[str],
        max_words_per_chunk: int = 300,
    ) -> list[list[float]]:
        if not texts:
            return []

        job = self.skill_queue.enqueue(
            "job_matcher_app.skill_worker.embed_bert_documents_task",
            texts,
            max_words_per_chunk,
            job_timeout="10m",
        )
        return await self._wait_for_job(
            job,
            "BERT Document Embedding Job in RQ worker failed",
        )

    async def embed_bert_experience(self, experience: dict) -> list[float]:
        job = self.skill_queue.enqueue(
            "job_matcher_app.skill_worker.embed_bert_experience_task",
            experience,
            job_timeout="10m",
        )
        return await self._wait_for_job(
            job,
            "BERT Experience Embedding Job in RQ worker failed",
        )

    def enqueue_experience_embedding_update(
        self,
        *,
        user_id: int,
        employee_id: int,
        experience_id: int,
        experience: dict,
    ) -> str:
        job = self.skill_queue.enqueue(
            "job_matcher_app.skill_worker.process_user_experience_embedding_task",
            {
                "user_id": user_id,
                "employee_id": employee_id,
                "experience_id": experience_id,
                "experience": experience,
            },
            job_timeout="10m",
        )
        return job.id

    def enqueue_experience_embedding_delete(
        self,
        *,
        user_id: int,
        employee_id: int,
        experience_id: int,
    ) -> str:
        job = self.skill_queue.enqueue(
            "job_matcher_app.skill_worker.process_user_experience_delete_task",
            {
                "user_id": user_id,
                "employee_id": employee_id,
                "experience_id": experience_id,
            },
            job_timeout="10m",
        )
        return job.id

    async def embed_bert_education(self, education: dict) -> list[float]:
        job = self.skill_queue.enqueue(
            "job_matcher_app.skill_worker.embed_bert_education_task",
            education,
            job_timeout="10m",
        )
        return await self._wait_for_job(
            job,
            "BERT Education Embedding Job in RQ worker failed",
        )

    def enqueue_education_embedding_update(
        self,
        *,
        user_id: int,
        employee_id: int,
        education_id: int,
        education: dict,
    ) -> str:
        job = self.skill_queue.enqueue(
            "job_matcher_app.skill_worker.process_user_education_embedding_task",
            {
                "user_id": user_id,
                "employee_id": employee_id,
                "education_id": education_id,
                "education": education,
            },
            job_timeout="10m",
        )
        return job.id

    def enqueue_education_embedding_delete(
        self,
        *,
        user_id: int,
        employee_id: int,
        education_id: int,
    ) -> str:
        job = self.skill_queue.enqueue(
            "job_matcher_app.skill_worker.process_user_education_delete_task",
            {
                "user_id": user_id,
                "employee_id": employee_id,
                "education_id": education_id,
            },
            job_timeout="10m",
        )
        return job.id

    async def embed_skills(
        self,
        db: AsyncSession,
        skill_names: list[str],
    ) -> int:
        if not skill_names:
            return 0

        result = await db.execute(
            text(
                """
                SELECT s.id, s.name, s.embedding_status, se.embedding::text AS embedding
                FROM skills s
                LEFT JOIN skill_embeddings se ON se.skill_id = s.id
                WHERE s.name = ANY(:names)
                """
            ),
            {"names": skill_names},
        )
        rows = result.fetchall()
        skills_by_name = {row.name: row for row in rows}
        missing = [name for name in skill_names if name not in skills_by_name]
        if missing:
            raise ValueError(
                "Missing skills in database: " + ", ".join(sorted(missing))
            )

        pending_rows = [
            row for row in rows
            if row.embedding_status != "done" or row.embedding is None
        ]
        if not pending_rows:
            return 0

        pending_names = [row.name for row in pending_rows]
        
        # Đẩy công việc vào Redis Queue (thông qua RQ) cho Container Worker xử lý
        job = self.skill_queue.enqueue(
            "job_matcher_app.skill_worker.embed_skills_task", 
            pending_names, 
            job_timeout="10m"
        )

        embeddings_result = await self._wait_for_job(
            job,
            "Skill Embedding Job in RQ worker failed",
        )

        update_rows = []
        for i, row in enumerate(pending_rows):
            embedding_literal = self._to_pgvector_literal(embeddings_result[i])
            update_rows.append(
                {
                    "skill_id": row.id,
                    "embedding": embedding_literal,
                }
            )

        await db.execute(
            text(
                """
                DELETE FROM skill_embeddings
                WHERE skill_id = ANY(:skill_ids)
                """
            ),
            {"skill_ids": [row.id for row in pending_rows]},
        )
        await db.execute(
            text(
                """
                INSERT INTO skill_embeddings (skill_id, embedding)
                VALUES (:skill_id, CAST(:embedding AS vector))
                """
            ),
            update_rows,
        )
        await db.execute(
            text(
                """
                UPDATE skills
                SET embedding_status = :status
                WHERE id = ANY(:skill_ids)
                """
            ),
            {
                "status": "done",
                "skill_ids": [row.id for row in pending_rows],
            },
        )
        await db.commit()
        return len(update_rows)

    async def get_skill_embeddings(
        self,
        db: AsyncSession,
        skill_names: list[str],
    ) -> dict[str, str]:
        if not skill_names:
            return {}

        result = await db.execute(
            text(
                """
                SELECT s.name, s.embedding_status, se.embedding::text AS embedding
                FROM skills s
                LEFT JOIN skill_embeddings se ON se.skill_id = s.id
                WHERE s.name = ANY(:names)
                """
            ),
            {"names": skill_names},
        )
        rows = result.fetchall()
        skills_by_name = {row.name: row for row in rows}
        missing = [name for name in skill_names if name not in skills_by_name]
        if missing:
            raise ValueError(
                "Missing skills in database: " + ", ".join(sorted(missing))
            )

        pending = [
            row.name for row in rows
            if row.embedding_status != "done" or row.embedding is None
        ]
        if pending:
            raise ValueError(
                "Skill embeddings are not ready yet for: " + ", ".join(sorted(pending))
            )

        return {row.name: row.embedding for row in rows}

    async def get_user_profile(self, db: AsyncSession, user_id: int) -> dict:
        """
        Retrieve user profile including education, experience, and skills from database.
        """
        stmt = (
            select(Employee)
            .options(
                selectinload(Employee.educations)
                .selectinload(Education.education_skills)
                .selectinload(EducationSkill.skill),
                selectinload(Employee.experiences)
                .selectinload(Experience.experience_skills)
                .selectinload(ExperienceSkill.skill),
                selectinload(Employee.employee_skills).selectinload(EmployeeSkill.skill),
            )
            .where(Employee.user_id == user_id)
        )
        result = await db.execute(stmt)
        employee = result.scalars().first()

        if not employee:
            raise ValueError(f"Employee with user_id {user_id} not found")

        educations = []
        if employee.educations:
            for edu in employee.educations:
                edu_skills = []
                if edu.education_skills:
                    edu_skills = [
                        {"skill_id": es.skill_id, "skill_name": es.skill.name}
                        for es in edu.education_skills
                    ]
                educations.append({
                    "education_id": edu.id,
                    "school": edu.school,
                    "degree": edu.degree,
                    "field_of_study": edu.field_of_study,
                    "Field of study": edu.field_of_study,
                    "description": edu.description,
                    "Description": edu.description,
                    "start_date": edu.start_date.isoformat() if edu.start_date else None,
                    "end_date": edu.end_date.isoformat() if edu.end_date else None,
                    "Start-end time": f"{edu.start_date.strftime('%m/%Y') if edu.start_date else ''} - {edu.end_date.strftime('%m/%Y') if edu.end_date else 'Present'}",
                    "skills": edu_skills,
                    "Skill": ", ".join(s["skill_name"] for s in edu_skills),
                })

        experiences = []
        if employee.experiences:
            for exp in employee.experiences:
                exp_skills = []
                if exp.experience_skills:
                    exp_skills = [
                        {"skill_id": es.skill_id, "skill_name": es.skill.name}
                        for es in exp.experience_skills
                    ]
                experiences.append({
                    "experience_id": exp.id,
                    "title": exp.title,
                    "Title": exp.title,
                    "company_name": exp.company_name,
                    "employment_type": exp.employment_type,
                    "location": exp.location,
                    "location_type": exp.location_type,
                    "description": exp.description,
                    "Description": exp.description,
                    "start_date": exp.start_date.isoformat() if exp.start_date else None,
                    "end_date": exp.end_date.isoformat() if exp.end_date else None,
                    "Start-end time": f"{exp.start_date.strftime('%m/%Y') if exp.start_date else ''} - {exp.end_date.strftime('%m/%Y') if exp.end_date else 'Present'}",
                    "skills": exp_skills,
                    "skill": ", ".join(s["skill_name"] for s in exp_skills),
                })

        skills = []
        if employee.employee_skills:
            skills = [
                {"skill_id": es.skill_id, "skill_name": es.skill.name}
                for es in employee.employee_skills
            ]

        return {
            "employee_id": employee.id,
            "user_id": employee.user_id,
            "headline": employee.headline,
            "summary": employee.summary,
            "years_of_experience": employee.years_of_experience,
            "current_location": employee.current_location,
            "Education": educations,
            "Experiences": experiences,
            "educations": educations,
            "experiences": experiences,
            "skills": skills,
        }
    
    async def search_best_jobs_in_db_by_skill_embeddings(
        self,
        db: AsyncSession,
        user_skills: list[str],
        threshold: float = get_settings().DEFAULT_THRESHOLD,
        limit: int = 100,
    ) -> list[int]:
        """
        Match User (embs) với TOÀN BỘ Jobs trong Database bằng pgvector.
        Cực kỳ nhanh vì không cần kéo bất kì text/vector nào từ DB lên RAM.
        Phiên bản hiệu năng cao: Chỉ trả về danh sách job_id.
        """
        if not user_skills:
            return []

        embedding_map = await self.get_skill_embeddings(db, user_skills)

        # 1. Khởi tạo danh sách tham số để đưa vào SQL (User Vectors)
        values_placeholders = ", ".join([
            f"(:name_{i}, :emb_{i}::vector)" for i in range(len(user_skills))
        ])
        
        params = {"threshold": threshold, "limit": limit}
        for i, skill in enumerate(user_skills):
            params[f"name_{i}"] = skill
            embedding_literal = embedding_map.get(skill)
            if embedding_literal is None:
                raise ValueError(
                    "Missing embedding for skill: " + skill
                )
            params[f"emb_{i}"] = embedding_literal

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


    @staticmethod
    def clean_text(text: str) -> str:
        return re.sub(r"\s+", " ", str(text or "")).strip()

    @staticmethod
    def _normalize_to_list(value):
        if not value:
            return []
        return value if isinstance(value, list) else [value]

    @staticmethod
    def _append_tfidf_fields(parts: list[str], item: dict, keys: list[str]) -> None:
        for key in keys:
            value = item.get(key)
            if not value:
                continue
            if isinstance(value, list):
                parts.append(" ".join(map(str, value)))
            else:
                parts.append(str(value))

    @staticmethod
    def _build_profile_tfidf_query_text(profile: dict) -> str:
        parts: list[str] = []

        educations = JobRecommendationService._normalize_to_list(
            profile.get("Educations")
            or profile.get("educations")
            or profile.get("Education")
            or profile.get("education")
        )
        for education in educations:
            if isinstance(education, dict):
                JobRecommendationService._append_tfidf_fields(
                    parts,
                    education,
                    [
                        "Field of study",
                        "Field of Study",
                        "field_of_study",
                        "Major",
                        "major",
                        "Degree",
                        "degree",
                        "Description",
                        "description",
                        "Skill",
                        "skill",
                        "Skills",
                        "skills",
                    ],
                )
            elif education:
                parts.append(str(education))

        experiences = JobRecommendationService._normalize_to_list(
            profile.get("Experiences")
            or profile.get("experiences")
            or profile.get("Experience")
            or profile.get("experience")
        )
        for experience in experiences:
            if isinstance(experience, dict):
                JobRecommendationService._append_tfidf_fields(
                    parts,
                    experience,
                    [
                        "Position",
                        "position",
                        "Company name",
                        "company_name",
                        "Description",
                        "description",
                        "Title",
                        "title",
                        "Skill",
                        "skill",
                        "Skills",
                        "skills",
                    ],
                )
            elif experience:
                parts.append(str(experience))

        profile_skills = profile.get("Skills") or profile.get("skills")
        if profile_skills:
            if isinstance(profile_skills, list):
                parts.append(" ".join(map(str, profile_skills)))
            else:
                parts.append(str(profile_skills))

        return " ".join(parts)

    @staticmethod
    def _has_profile_tfidf_text(profile: dict) -> bool:
        query_text = JobRecommendationService._build_profile_tfidf_query_text(profile)
        query_text = str(query_text or "").lower()
        query_text = re.sub(r"<[^>]+>", " ", query_text)
        query_text = re.sub(r"[^\w\s]", " ", query_text)
        return bool(" ".join(query_text.split()))

    def calculate_recency_weight(self,end_time_str, current_year=2026):
        """
        Hàm tính trọng số decay theo thời gian. Mới nhất -> weight cao hơn.
        """
        if not end_time_str or end_time_str.lower() in ['hiện tại', 'nay', 'now', 'present']:
            return 1.0
        
        try:
            # Trích xuất năm từ chuỗi (vd: '02/2026' -> 2026)
            years = re.findall(r'\d{4}', end_time_str)
            if years:
                end_year = int(years[-1])
                diff = current_year - end_year
                # Decay factor = 0.8 mỗi năm cách biệt, tối đa giảm về 0.3
                return max(0.3, 0.8 ** diff)
        except:
            pass
        return 0.5 # Default weight nếu không parse được thời gian
    


    async def process_user_profile_multimodal(self, profile):
        """
        Trả về bộ vector profile do worker RQ tính toán.
        """
        job = self.skill_queue.enqueue(
            "job_matcher_app.skill_worker.process_user_profile_multimodal_task",
            profile,
            job_timeout="10m",
        )
        return await self._wait_for_job(
            job,
            "User Profile Vector Job in RQ worker failed",
        )

    async def process_user_profile_tfidf(self, profile: dict) -> list[float]:
        """
        Trả về vector TF-IDF + SVD cho user profile do worker TF-IDF tính toán.
        """
        if not self._has_profile_tfidf_text(profile):
            return []

        job = self.tfidf_queue.enqueue(
            "job_matcher_app.skill_worker_tfidf.process_user_profile_tfidf_task",
            profile,
            job_timeout="10m",
        )
        return await self._wait_for_job(
            job,
            "User Profile TF-IDF Vector Job in RQ worker failed",
        )

    def enqueue_user_profile_tfidf_update(
        self,
        *,
        user_id: int,
        employee_id: int,
        profile: dict,
    ) -> str:
        job = self.tfidf_queue.enqueue(
            "job_matcher_app.skill_worker_tfidf.process_user_profile_tfidf_update_task",
            {
                "user_id": user_id,
                "employee_id": employee_id,
                "profile": profile,
            },
            job_timeout="10m",
        )
        return job.id

    async def upsert_user_profile_tfidf_embedding(
        self,
        db: AsyncSession,
        employee_id: int,
        profile_vector: list[float],
    ) -> None:
        tfidf_vec = self._to_pgvector_literal(profile_vector)

        await db.execute(
            text(
                """
                INSERT INTO user_profile_embedding (
                    employee_id,
                    vector_tfidf
                )
                VALUES (
                    :employee_id,
                    CAST(:vector_tfidf AS vector)
                )
                ON CONFLICT (employee_id) DO UPDATE
                SET vector_tfidf = EXCLUDED.vector_tfidf
                """
            ),
            {
                "employee_id": employee_id,
                "vector_tfidf": tfidf_vec,
            },
        )

    async def update_user_profile_tfidf_vector(
        self,
        db: AsyncSession,
        user_id: int,
        profile: dict,
    ) -> dict:
        result = await db.execute(
            select(Employee.id).where(Employee.user_id == user_id)
        )
        employee_id = result.scalar_one_or_none()
        if employee_id is None:
            raise ValueError(f"Employee with user_id {user_id} not found")

        if not self._has_profile_tfidf_text(profile):
            return {
                "user_id": user_id,
                "employee_id": employee_id,
                "vector_tfidf_enqueued": False,
                "vector_tfidf_updated": False,
                "status": "skipped",
                "reason": "empty_profile",
            }

        self.enqueue_user_profile_tfidf_update(
            user_id=user_id,
            employee_id=employee_id,
            profile=profile,
        )

        return {
            "user_id": user_id,
            "employee_id": employee_id,
            "vector_tfidf_enqueued": True,
            "status": "queued",
        }

    async def search_best_jobs_in_db_by_tfidf(
        self,
        db: AsyncSession,
        user_id: int,
        limit: int = 100,
    ) -> list[int]:
        """
        Search top jobs by comparing stored user TF-IDF vector with job TF-IDF vectors.
        """
        if limit <= 0:
            raise ValueError("limit must be greater than 0")

        lock_key = f"user:{user_id}:tfidf_embedding_lock"
        if self.redis_conn.exists(lock_key):
            raise ValueError("Profile TF-IDF vector is currently being updated. Please try again later.")

        employee_result = await db.execute(
            select(Employee.id).where(Employee.user_id == user_id)
        )
        employee_id = employee_result.scalar_one_or_none()
        if employee_id is None:
            raise ValueError(f"Employee with user_id {user_id} not found")

        profile_vector_result = await db.execute(
            text(
                """
                SELECT vector_tfidf::text AS vector_tfidf
                FROM user_profile_embedding
                WHERE employee_id = :employee_id
                """
            ),
            {"employee_id": employee_id},
        )
        profile_vector = profile_vector_result.scalar_one_or_none()
        if profile_vector is None:
            raise ValueError("User TF-IDF vector is not ready yet")

        rows = (
            await db.execute(
                text(
                    """
                    SELECT id
                    FROM job_embeddings_tfidf
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> CAST(:vector_tfidf AS vector)
                    LIMIT :limit
                    """
                ),
                {
                    "vector_tfidf": profile_vector,
                    "limit": limit,
                },
            )
        ).fetchall()

        return [row.id for row in rows]

    # async def upsert_user_profile_embedding(
    #     self,
    #     db: AsyncSession,
    #     employee_id: int,
    #     profile_vectors: dict,
    # ) -> None:
    #     experience_vec = self._to_pgvector_literal(
    #         profile_vectors["experience_vec_384"]
    #     )
    #     education_vec = self._to_pgvector_literal(
    #         profile_vectors["education_vec_384"]
    #     )
    #     tfidf_vec = self._to_pgvector_literal(
    #         profile_vectors["tfidf_vec"]
    #     )

    #     await db.execute(
    #         text(
    #             """
    #             INSERT INTO user_profile_embedding (
    #                 employee_id,
    #                 experience_vec,
    #                 education_vec,
    #                 vector_tfidf
    #             )
    #             VALUES (
    #                 :employee_id,
    #                 CAST(:experience_vec AS vector),
    #                 CAST(:education_vec AS vector),
    #                 CAST(:vector_tfidf AS vector)
    #             )
    #             ON CONFLICT (employee_id) DO UPDATE
    #             SET experience_vec = EXCLUDED.experience_vec,
    #                 education_vec = EXCLUDED.education_vec,
    #                 vector_tfidf = EXCLUDED.vector_tfidf
    #             """
    #         ),
    #         {
    #             "employee_id": employee_id,
    #             "experience_vec": experience_vec,
    #             "education_vec": education_vec,
    #             "vector_tfidf": tfidf_vec,
    #         },
    #     )

    async def search_best_jobs_in_db_by_bert(
        self,
        db: AsyncSession,
        user_id: int,
        threshold: float = get_settings().DEFAULT_THRESHOLD,
        limit: int = 100,
    ):
        lock_edu = f"user:{user_id}:education_embedding_lock"
        lock_exp = f"user:{user_id}:experience_embedding_lock"
        if self.redis_conn.exists(lock_edu) or self.redis_conn.exists(lock_exp):
            raise ValueError("Profile BERT vectors are currently being updated. Please try again later.")

        employee_result = await db.execute(
            select(Employee.id).where(Employee.user_id == user_id)
        )
        employee_id = employee_result.scalar_one_or_none()
        if employee_id is None:
            raise ValueError(f"Employee with user_id {user_id} not found")

        vectors_result = await db.execute(
            text(
                """
                SELECT 
                    experience_vec::text AS experience_vec,
                    education_vec::text AS education_vec
                FROM user_profile_embedding
                WHERE employee_id = :employee_id
                """
            ),
            {"employee_id": employee_id},
        )
        row = vectors_result.mappings().first()

        if not row:
            raise ValueError("User BERT vectors are not ready yet")

        def _parse_pgvector(val: str | None) -> np.ndarray:
            if not val:
                return np.zeros(384)
            return np.asarray([float(v) for v in val.strip("[]").split(",") if v.strip()], dtype=float)

        experience_vec = _parse_pgvector(row.get("experience_vec"))
        education_vec = _parse_pgvector(row.get("education_vec"))

        W_EXP = 0.7
        W_EDU = 0.3
        combined_query_384 = (W_EXP * experience_vec + W_EDU * education_vec) / (W_EXP + W_EDU)

        norm = np.linalg.norm(combined_query_384)
        if norm > 0: 
            combined_query_384 = combined_query_384 / norm
        else:
            return []

        query_vector = self._to_pgvector_literal(combined_query_384)
        search_query = text("""
        SELECT
            job_id,
            1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
        FROM job_embeddings_bert
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :limit;
        """)

        records = (
            await db.execute(
                search_query,
                {"embedding": query_vector, "limit": limit},
            )
        ).fetchall()
        return [
            record.job_id
            for record in records
            if record.similarity is not None and record.similarity >= threshold
        ]

    @staticmethod
    def calculate_rrf(*rankings, k=60):
        """
        Tính RRF Score cho danh sách các bảng xếp hạng (rankings).
        - rankings: List các Dataframe hoặc Series chứa ID công việc đã được rank từ cao xuống thấp.
        - k: Hằng số smoothing (thường dùng chuẩn là 60).
        """
        rrf_scores = {}
        
        for ranking in rankings:
            # Lặp qua từng kết quả của 1 model
            for rank, job_id in enumerate(ranking):
                if job_id not in rrf_scores:
                    rrf_scores[job_id] = 0.0
                
                # Công thức RRF: 1 / (k + rank) -> rank ở đây tính từ 1
                rrf_scores[job_id] += 1.0 / (k + rank + 1)

        # Sắp xếp công việc theo điểm RRF từ cao xuống thấp
        sorted_jobs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_jobs

    async def rerank_job_candidates(
        self,
        db: AsyncSession,
        user_id: int,
        candidate_ids: list[int],
        rrf_score_map: dict[int, float],
        top_k: int,
    ) -> list[int]:
        if not candidate_ids:
            return []

        user_profile = await self.get_user_profile(db, user_id)
        user_skills = [
            skill["skill_name"]
            for skill in user_profile.get("skills", [])
            if skill.get("skill_name")
        ]
        current_location = self.clean_text(user_profile.get("current_location")) or None

        skill_scores: dict[int, dict[str, float]] = {}
        if user_skills:
            embedding_map = await self.get_skill_embeddings(db, user_skills)
            values_placeholders = ", ".join(
                f"(:name_{i}, CAST(:emb_{i} AS vector))"
                for i in range(len(user_skills))
            )
            params = {
                "candidate_ids": candidate_ids,
                "threshold": get_settings().DEFAULT_THRESHOLD,
            }
            for i, skill in enumerate(user_skills):
                params[f"name_{i}"] = skill
                params[f"emb_{i}"] = embedding_map[skill]

            skill_query = text(f"""
                WITH user_skills(name, embedding) AS (
                    SELECT * FROM (VALUES {values_placeholders}) AS v(name, embedding)
                ),
                jd_skill_sims AS (
                    SELECT
                        js.job_id,
                        s.name AS jd_skill,
                        MAX(1 - (se.embedding <=> u.embedding)) AS best_sim
                    FROM job_skills js
                    JOIN skills s ON js.skill_id = s.id
                    JOIN skill_embeddings se ON se.skill_id = s.id
                    CROSS JOIN user_skills u
                    WHERE js.job_id = ANY(CAST(:candidate_ids AS INTEGER[]))
                    GROUP BY js.job_id, s.name
                )
                SELECT
                    job_id,
                    COUNT(*) AS total_skills,
                    SUM(CASE WHEN best_sim >= :threshold THEN 1 ELSE 0 END) AS covered_skills,
                    AVG(best_sim) AS avg_sim
                FROM jd_skill_sims
                GROUP BY job_id
            """)
            rows = (await db.execute(skill_query, params)).fetchall()
            for row in rows:
                total_skills = int(row.total_skills or 0)
                covered_skills = int(row.covered_skills or 0)
                skill_coverage = (
                    covered_skills / total_skills
                    if total_skills > 0
                    else 0.0
                )
                avg_sim = float(row.avg_sim or 0.0)
                skill_scores[row.job_id] = {
                    "skill_score": 0.7 * skill_coverage + 0.3 * avg_sim,
                }

        job_rows = (
            await db.execute(
                text(
                    """
                    WITH candidate_jobs AS (
                        SELECT
                            id,
                            address,
                            COALESCE(salary_max, salary_min, 0) AS salary_value
                        FROM jobs
                        WHERE id = ANY(CAST(:candidate_ids AS INTEGER[]))
                    ),
                    salary_stats AS (
                        SELECT MAX(salary_value) AS max_salary
                        FROM candidate_jobs
                    )
                    SELECT
                        cj.id AS job_id,
                        CASE
                            WHEN CAST(:current_location AS TEXT) IS NOT NULL
                                 AND cj.address ILIKE ('%' || CAST(:current_location AS TEXT) || '%')
                            THEN 1.0
                            ELSE 0.0
                        END AS location_score,
                        CASE
                            WHEN ss.max_salary IS NOT NULL AND ss.max_salary > 0
                            THEN cj.salary_value / ss.max_salary
                            ELSE 0.0
                        END AS salary_score
                    FROM candidate_jobs cj
                    CROSS JOIN salary_stats ss
                    """
                ),
                {
                    "candidate_ids": candidate_ids,
                    "current_location": current_location,
                },
            )
        ).fetchall()

        max_rrf = max(rrf_score_map.values()) if rrf_score_map else 0.0
        reranked = []
        for row in job_rows:
            job_id = row.job_id
            normalized_rrf = (
                rrf_score_map.get(job_id, 0.0) / max_rrf
                if max_rrf > 0
                else 0.0
            )
            skill_score = skill_scores.get(job_id, {}).get("skill_score", 0.0)
            location_score = float(row.location_score or 0.0)
            salary_score = float(row.salary_score or 0.0)
            final_score = (
                0.20 * normalized_rrf
                + 0.55 * skill_score
                + 0.15 * location_score
                + 0.10 * salary_score
            )
            reranked.append((job_id, final_score))

        reranked.sort(key=lambda item: item[1], reverse=True)
        return [job_id for job_id, _ in reranked[:top_k]]

    async def get_recommended_job_details(
        self,
        db: AsyncSession,
        job_ids: list[int],
    ) -> list[dict]:
        if not job_ids:
            return []

        rows = (
            await db.execute(
                text(
                    """
                    SELECT
                        id,
                        title,
                        salary_min,
                        salary_max,
                        salary_currency,
                        address,
                        location_type
                    FROM jobs
                    WHERE id = ANY(:job_ids)
                    """
                ),
                {"job_ids": job_ids},
            )
        ).fetchall()
        jobs_by_id = {row.id: row for row in rows}

        result = []
        for job_id in job_ids:
            job = jobs_by_id.get(job_id)
            if job is None:
                continue
            result.append(
                {
                    "id": job.id,
                    "title": job.title,
                    "salary_min": str(job.salary_min) if job.salary_min is not None else None,
                    "salary_max": str(job.salary_max) if job.salary_max is not None else None,
                    "salary_currency": job.salary_currency,
                    "location": job.address,
                    "location_type": job.location_type,
                }
            )

        return result

    async def get_job_detail(
        self,
        db: AsyncSession,
        job_id: int,
    ) -> dict:
        job_row = (
            await db.execute(
                text(
                    """
                    SELECT
                        j.id,
                        j.title,
                        j.description,
                        j.requirement,
                        j.benefit,
                        j.salary_min,
                        j.salary_max,
                        j.salary_currency,
                        j.experience_required,
                        j.employment_type,
                        j.working_time,
                        j.location_type,
                        j.address,
                        j.deadline,
                        j.status,
                        j.created_at,
                        c.id AS company_id,
                        c.name AS company_name,
                        c.logo_url AS company_logo_url,
                        c.industry AS company_industry,
                        c.location AS company_location
                    FROM jobs j
                    JOIN companies c ON j.company_id = c.id
                    WHERE j.id = :job_id
                    """
                ),
                {"job_id": job_id},
            )
        ).mappings().first()
        if job_row is None:
            raise ValueError(f"Job with id {job_id} not found")

        skill_rows = (
            await db.execute(
                text(
                    """
                    SELECT
                        s.id,
                        s.name,
                        js.is_required
                    FROM job_skills js
                    JOIN skills s ON js.skill_id = s.id
                    WHERE js.job_id = :job_id
                    ORDER BY s.name
                    """
                ),
                {"job_id": job_id},
            )
        ).mappings().all()

        return {
            "id": job_row["id"],
            "title": job_row["title"],
            "description": job_row["description"],
            "requirement": job_row["requirement"],
            "benefit": job_row["benefit"],
            "salary_min": str(job_row["salary_min"]) if job_row["salary_min"] is not None else None,
            "salary_max": str(job_row["salary_max"]) if job_row["salary_max"] is not None else None,
            "salary_currency": job_row["salary_currency"],
            "experience_required": job_row["experience_required"],
            "employment_type": job_row["employment_type"],
            "working_time": job_row["working_time"],
            "location_type": job_row["location_type"],
            "location": job_row["address"],
            "deadline": job_row["deadline"].isoformat() if job_row["deadline"] else None,
            "status": job_row["status"],
            "created_at": job_row["created_at"].isoformat() if job_row["created_at"] else None,
            "company": {
                "id": job_row["company_id"],
                "name": job_row["company_name"],
                "logo_url": job_row["company_logo_url"],
                "industry": job_row["company_industry"],
                "location": job_row["company_location"],
            },
            "skills": [
                {
                    "skill_id": row["id"],
                    "skill_name": row["name"],
                    "is_required": row["is_required"],
                }
                for row in skill_rows
            ],
        }


    async def recommend_jobs_2_phase(
        self, db: AsyncSession, user_id: int, top_k: int = 20
    ):
        """
        Recommend top-k jobs for a user based on their skills and profile.
        """

        #Phase 1: Sử dụng skill embeddings để nhanh chóng lọc ra top 5x job candidates có độ tương đồng skill cao nhất.
        top_job_tfidf = await self.search_best_jobs_in_db_by_tfidf(db, user_id, limit=top_k*5)

        top_job_bert = await self.search_best_jobs_in_db_by_bert(db, user_id, limit=top_k*5)

        # Kết hợp kết quả từ cả 2 phương pháp bằng RRF
        combined_rankings = self.calculate_rrf(top_job_tfidf, top_job_bert, k=top_k*5)

        if not combined_rankings:
            return []

        candidate_ids = [job_id for job_id, _ in combined_rankings]
        rrf_score_map = {job_id: score for job_id, score in combined_rankings}

        # Phase 2: rerank candidate set theo skill overlap, location và salary heuristic.
        return await self.rerank_job_candidates(
            db=db,
            user_id=user_id,
            candidate_ids=candidate_ids,
            rrf_score_map=rrf_score_map,
            top_k=top_k,
        )

