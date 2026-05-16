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
                SELECT id, name, embedding_status
                FROM skills
                WHERE name = ANY(:names)
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

        pending_rows = [row for row in rows if row.embedding_status != "done"]
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
                    "status": "done",
                }
            )

        await db.execute(
            text(
                """
                UPDATE skills
                SET embedding = :embedding::vector,
                    embedding_status = :status
                WHERE id = :skill_id
                """
            ),
            update_rows,
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
                SELECT name, embedding_status, embedding::text AS embedding
                FROM skills
                WHERE name = ANY(:names)
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

    async def upsert_user_profile_embedding(
        self,
        db: AsyncSession,
        employee_id: int,
        profile_vectors: dict,
    ) -> None:
        experience_vec = self._to_pgvector_literal(
            profile_vectors["experience_vec_384"]
        )
        education_vec = self._to_pgvector_literal(
            profile_vectors["education_vec_384"]
        )

        await db.execute(
            text(
                """
                INSERT INTO user_profile_embedding (
                    employee_id,
                    experience_vec,
                    education_vec
                )
                VALUES (
                    :employee_id,
                    CAST(:experience_vec AS vector),
                    CAST(:education_vec AS vector)
                )
                ON CONFLICT (employee_id) DO UPDATE
                SET experience_vec = EXCLUDED.experience_vec,
                    education_vec = EXCLUDED.education_vec
                """
            ),
            {
                "employee_id": employee_id,
                "experience_vec": experience_vec,
                "education_vec": education_vec,
            },
        )

    async def search_best_jobs_in_db_by_bert(self, db: AsyncSession, profile: dict, model=None, threshold: float = get_settings().DEFAULT_THRESHOLD, limit: int = 100):
        profile_vectors = await self.process_user_profile_multimodal(profile)
        W_EXP = 0.7
        W_EDU = 0.3
        experience_vec = np.asarray(profile_vectors["experience_vec_384"], dtype=float)
        education_vec = np.asarray(profile_vectors["education_vec_384"], dtype=float)
        combined_query_384 = (W_EXP * experience_vec + W_EDU * education_vec) / (W_EXP + W_EDU)

        norm = np.linalg.norm(combined_query_384)
        if norm > 0: combined_query_384 = combined_query_384 / norm

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

            

    async def recommend_jobs_2_phase(
        self, db: AsyncSession, user_id: int, top_k: int = 100
    ):
        """
        Recommend top-k jobs for a user based on their skills and profile.
        """
        user_profile = await self.get_user_profile(db, user_id)
        
        if not user_profile["skills"]:
            raise ValueError(f"User {user_id} has no skills in profile")

        skill_ids = [s["skill_id"] for s in user_profile["skills"] if s.get("skill_id")]
        result = await db.execute(
            select(Skill.id, Skill.name)
            .where(Skill.id.in_(skill_ids))
            .where(Skill.embedding_status != "done")
        )
        pending_rows = result.all()
        if pending_rows:
            pending_names = ", ".join(sorted({row.name for row in pending_rows}))
            raise ValueError(
                "Skill embeddings are not ready yet for: " + pending_names
            )

        skill_similiarity_results = await self.search_best_jobs_in_db_by_skill_embeddings(
            db=db,
            user_skills=[s["skill_name"] for s in user_profile["skills"]],
            limit=top_k,
        )

        return skill_similiarity_results



        

