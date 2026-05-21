import logging
import time
from datetime import datetime
from typing import Any

import numpy as np
from passlib.context import CryptContext
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from models import (
    Education,
    EducationSkill,
    Employee,
    EmployeeSkill,
    Experience,
    ExperienceSkill,
    Skill,
    User,
)


password_context = CryptContext(
    schemes=["pbkdf2_sha256", "bcrypt_sha256", "bcrypt"],
    deprecated=["bcrypt_sha256", "bcrypt"],
)

logger = logging.getLogger(__name__)


class UserService:
    """Service for managing user information and profiles."""

    PROFILE_VECTOR_SIZE = 384

    @staticmethod
    def _normalize_skill_names(skill_names: list[str]) -> list[str]:
        normalized = []
        seen = set()

        for raw_name in skill_names:
            skill_name = raw_name.strip()
            if not skill_name:
                raise ValueError("Skill names must not be empty")

            key = skill_name.lower()
            if key in seen:
                continue

            seen.add(key)
            normalized.append(skill_name)

        return normalized

    @staticmethod
    async def _fetch_employee_with_skills(
        db: AsyncSession,
        user_id: int,
    ) -> Employee | None:
        result = await db.execute(
            select(Employee)
            .options(selectinload(Employee.employee_skills).selectinload(EmployeeSkill.skill))
            .where(Employee.user_id == user_id)
        )
        return result.scalars().first()

    @staticmethod
    async def _get_or_create_skills(
        db: AsyncSession,
        skill_names: list[str],
    ) -> tuple[list[Skill], set[str]]:
        if not skill_names:
            return [], set()

        skill_keys = [name.lower() for name in skill_names]
        result = await db.execute(
            select(Skill).where(func.lower(Skill.name).in_(skill_keys))
        )
        skills_by_key = {skill.name.lower(): skill for skill in result.scalars().all()}

        created_keys = set()
        for skill_name in skill_names:
            key = skill_name.lower()
            if key in skills_by_key:
                continue

            skill = Skill(name=skill_name, embedding_status="pending")
            db.add(skill)
            skills_by_key[key] = skill
            created_keys.add(key)

        if created_keys:
            await db.flush()

        return [skills_by_key[name.lower()] for name in skill_names], created_keys

    @staticmethod
    def _serialize_updated_profile(
        user: User,
        employee: Employee | None,
        skills: list[Skill],
        skills_changed: bool,
        embedded_skill_count: int,
        profile_embedding_updated: bool,
    ) -> dict:
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "role": user.role,
            "avatar_url": user.avatar_url,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "employee_profile": (
                {
                    "employee_id": employee.id,
                    "headline": employee.headline,
                    "summary": employee.summary,
                    "years_of_experience": employee.years_of_experience,
                    "current_location": employee.current_location,
                }
                if employee
                else None
            ),
            "skills": [
                {"skill_id": skill.id, "skill_name": skill.name}
                for skill in skills
            ],
            "skills_changed": skills_changed,
            "embedded_skill_count": embedded_skill_count,
            "profile_embedding_updated": profile_embedding_updated,
        }

    @staticmethod
    def _serialize_employee_user(user: User, employee: Employee) -> dict:
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "role": user.role,
            "avatar_url": user.avatar_url,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "employee_profile": {
                "employee_id": employee.id,
                "headline": employee.headline,
                "summary": employee.summary,
                "years_of_experience": employee.years_of_experience,
                "current_location": employee.current_location,
                "created_at": employee.created_at.isoformat() if employee.created_at else None,
            },
        }

    @staticmethod
    def _serialize_experience(experience: Experience, skills: list[Skill]) -> dict:
        return {
            "experience_id": experience.id,
            "employee_id": experience.employee_id,
            "title": experience.title,
            "company_name": experience.company_name,
            "employment_type": experience.employment_type,
            "location": experience.location,
            "location_type": experience.location_type,
            "description": experience.description,
            "start_date": experience.start_date.isoformat() if experience.start_date else None,
            "end_date": experience.end_date.isoformat() if experience.end_date else None,
            "skills": [
                {"skill_id": skill.id, "skill_name": skill.name}
                for skill in skills
            ],
        }

    @staticmethod
    def _serialize_education(education: Education, skills: list[Skill]) -> dict:
        return {
            "education_id": education.id,
            "employee_id": education.employee_id,
            "school": education.school,
            "degree": education.degree,
            "field_of_study": education.field_of_study,
            "description": education.description,
            "start_date": education.start_date.isoformat() if education.start_date else None,
            "end_date": education.end_date.isoformat() if education.end_date else None,
            "skills": [
                {"skill_id": skill.id, "skill_name": skill.name}
                for skill in skills
            ],
        }

    @staticmethod
    def _format_experience_time_range(experience: Experience) -> str:
        start = experience.start_date.strftime("%m/%Y") if experience.start_date else ""
        end = experience.end_date.strftime("%m/%Y") if experience.end_date else "Present"
        return f"{start} - {end}"

    @staticmethod
    def _build_experience_embedding_payload(
        experience: Experience,
        skills: list[Skill],
    ) -> dict:
        return {
            "Title": experience.title,
            "Description": experience.description,
            "skill": ", ".join(skill.name for skill in skills),
            "Start-end time": UserService._format_experience_time_range(experience),
        }

    @staticmethod
    def _build_education_embedding_payload(
        education: Education,
        skills: list[Skill],
    ) -> dict:
        return {
            "Field of study": education.field_of_study,
            "Description": education.description,
            "Skill": ", ".join(skill.name for skill in skills),
        }

    @staticmethod
    def _calculate_recency_weight(end_date, current_year: int | None = None) -> float:
        if end_date is None:
            return 1.0

        current_year = current_year or datetime.utcnow().year
        diff = current_year - end_date.year
        return max(0.3, 0.8 ** diff)

    @staticmethod
    def _parse_pgvector_text(vector_text: str) -> list[float]:
        return [
            float(value)
            for value in vector_text.strip("[]").split(",")
            if value.strip()
        ]

    @staticmethod
    def _to_pgvector_literal(vector) -> str:
        if hasattr(vector, "tolist"):
            vector = vector.tolist()

        vector = np.asarray(vector).reshape(-1)
        return "[" + ",".join(str(float(value)) for value in vector) + "]"

    @staticmethod
    async def _ensure_and_lock_profile_embedding_row(
        db: AsyncSession,
        employee_id: int,
    ) -> None:
        await db.execute(
            text(
                """
                INSERT INTO user_profile_embedding (employee_id)
                VALUES (:employee_id)
                ON CONFLICT (employee_id) DO NOTHING
                """
            ),
            {"employee_id": employee_id},
        )

        await db.execute(
            text(
                """
                SELECT employee_id
                FROM user_profile_embedding
                WHERE employee_id = :employee_id
                FOR UPDATE
                """
            ),
            {"employee_id": employee_id},
        )

    @staticmethod
    async def _lock_and_recompute_profile_experience_vector(
        db: AsyncSession,
        employee_id: int,
    ) -> None:
        await UserService._ensure_and_lock_profile_embedding_row(db, employee_id)

        result = await db.execute(
            text(
                """
                SELECT
                    e.id AS experience_id,
                    e.end_date,
                    ebe.experience_vec::text AS experience_vec
                FROM employee_experience_embedding ebe
                JOIN experiences e ON e.id = ebe.experience_id
                WHERE ebe.employee_id = :employee_id
                  AND ebe.experience_vec IS NOT NULL
                """
            ),
            {"employee_id": employee_id},
        )
        rows = result.fetchall()

        if not rows:
            await db.execute(
                text(
                    """
                    UPDATE user_profile_embedding
                    SET experience_vec = NULL
                    WHERE employee_id = :employee_id
                    """
                ),
                {"employee_id": employee_id},
            )
            return

        aggregate_vec = np.zeros(UserService.PROFILE_VECTOR_SIZE)
        total_weight = 0.0
        for row in rows:
            vector = np.asarray(
                UserService._parse_pgvector_text(row.experience_vec),
                dtype=float,
            )
            if vector.size != UserService.PROFILE_VECTOR_SIZE:
                raise ValueError(
                    f"Experience vector for experience_id {row.experience_id} "
                    f"has size {vector.size}, expected {UserService.PROFILE_VECTOR_SIZE}"
                )

            weight = UserService._calculate_recency_weight(row.end_date)
            aggregate_vec += vector * weight
            total_weight += weight

        aggregate_vec = aggregate_vec / total_weight
        norm = np.linalg.norm(aggregate_vec)
        if norm > 0:
            aggregate_vec = aggregate_vec / norm

        await db.execute(
            text(
                """
                UPDATE user_profile_embedding
                SET experience_vec = CAST(:experience_vec AS vector)
                WHERE employee_id = :employee_id
                """
            ),
            {
                "employee_id": employee_id,
                "experience_vec": UserService._to_pgvector_literal(aggregate_vec),
            },
        )

    @staticmethod
    async def _upsert_experience_embedding_and_recompute_profile_vector(
        db: AsyncSession,
        employee_id: int,
        experience_id: int,
        experience_vector: list[float],
        embedding_service: Any = None,
    ) -> None:
        experience_vector_literal = UserService._to_pgvector_literal(
            experience_vector
        )

        await UserService._ensure_and_lock_profile_embedding_row(db, employee_id)

        await db.execute(
            text(
                """
                INSERT INTO employee_experience_embedding (
                    employee_id,
                    experience_id,
                    experience_vec
                )
                VALUES (
                    :employee_id,
                    :experience_id,
                    CAST(:experience_vec AS vector)
                )
                ON CONFLICT (experience_id) DO UPDATE
                SET employee_id = EXCLUDED.employee_id,
                    experience_vec = EXCLUDED.experience_vec
                """
            ),
            {
                "employee_id": employee_id,
                "experience_id": experience_id,
                "experience_vec": experience_vector_literal,
            },
        )

        await UserService._lock_and_recompute_profile_experience_vector(
            db,
            employee_id,
        )

    @staticmethod
    async def _lock_and_recompute_profile_education_vector(
        db: AsyncSession,
        employee_id: int,
    ) -> None:
        await UserService._ensure_and_lock_profile_embedding_row(db, employee_id)

        result = await db.execute(
            text(
                """
                SELECT
                    education_id,
                    education_vec::text AS education_vec
                FROM employee_education_embedding
                WHERE employee_id = :employee_id
                  AND education_vec IS NOT NULL
                """
            ),
            {"employee_id": employee_id},
        )
        rows = result.fetchall()

        if not rows:
            await db.execute(
                text(
                    """
                    UPDATE user_profile_embedding
                    SET education_vec = NULL
                    WHERE employee_id = :employee_id
                    """
                ),
                {"employee_id": employee_id},
            )
            return

        education_vectors = []
        for row in rows:
            vector = np.asarray(
                UserService._parse_pgvector_text(row.education_vec),
                dtype=float,
            )
            if vector.size != UserService.PROFILE_VECTOR_SIZE:
                raise ValueError(
                    f"Education vector for education_id {row.education_id} "
                    f"has size {vector.size}, expected {UserService.PROFILE_VECTOR_SIZE}"
                )
            education_vectors.append(vector)

        aggregate_vec = np.mean(education_vectors, axis=0)
        norm = np.linalg.norm(aggregate_vec)
        if norm > 0:
            aggregate_vec = aggregate_vec / norm

        await db.execute(
            text(
                """
                UPDATE user_profile_embedding
                SET education_vec = CAST(:education_vec AS vector)
                WHERE employee_id = :employee_id
                """
            ),
            {
                "employee_id": employee_id,
                "education_vec": UserService._to_pgvector_literal(aggregate_vec),
            },
        )

    @staticmethod
    async def _upsert_education_embedding_and_recompute_profile_vector(
        db: AsyncSession,
        employee_id: int,
        education_id: int,
        education_vector: list[float],
        embedding_service: Any = None,
    ) -> None:
        education_vector_literal = UserService._to_pgvector_literal(
            education_vector
        )

        await UserService._ensure_and_lock_profile_embedding_row(db, employee_id)

        await db.execute(
            text(
                """
                INSERT INTO employee_education_embedding (
                    employee_id,
                    education_id,
                    education_vec
                )
                VALUES (
                    :employee_id,
                    :education_id,
                    CAST(:education_vec AS vector)
                )
                ON CONFLICT (education_id) DO UPDATE
                SET employee_id = EXCLUDED.employee_id,
                    education_vec = EXCLUDED.education_vec
                """
            ),
            {
                "employee_id": employee_id,
                "education_id": education_id,
                "education_vec": education_vector_literal,
            },
        )

        await UserService._lock_and_recompute_profile_education_vector(
            db,
            employee_id,
        )

    @staticmethod
    async def create_employee_user_async(
        db: AsyncSession,
        email: str,
        password: str,
        full_name: str = None,
        phone: str = None,
        avatar_url: str = None,
        headline: str = None,
        summary: str = None,
        years_of_experience: int = None,
        current_location: str = None,
    ) -> dict:
        """Create a user with employee role and an employee profile."""
        normalized_email = email.strip().lower()
        if not normalized_email:
            raise ValueError("email must not be empty")
        if not password:
            raise ValueError("password must not be empty")

        existing_user = await db.execute(
            select(User.id).where(func.lower(User.email) == normalized_email)
        )
        if existing_user.scalar_one_or_none() is not None:
            raise ValueError(f"User with email {normalized_email} already exists")

        user = User(
            email=normalized_email,
            password_hash=password_context.hash(password),
            full_name=full_name,
            phone=phone,
            role="employee",
            avatar_url=avatar_url,
        )

        try:
            db.add(user)
            await db.flush()

            employee = Employee(
                user_id=user.id,
                headline=headline,
                summary=summary,
                years_of_experience=years_of_experience,
                current_location=current_location,
            )
            db.add(employee)
            await db.flush()

            await db.commit()
            await db.refresh(user)
            await db.refresh(employee)
        except IntegrityError as exc:
            await db.rollback()
            raise ValueError(f"Failed to create employee user: {exc}") from exc
        except Exception:
            await db.rollback()
            raise

        return UserService._serialize_employee_user(user, employee)

    # @staticmethod
    # async def update_user_profile_async(
    #     db: AsyncSession,
    #     user_id: int,
    #     embedding_service: Any,
    #     full_name: str = None,
    #     phone: str = None,
    #     avatar_url: str = None,
    #     headline: str = None,
    #     summary: str = None,
    #     years_of_experience: int = None,
    #     current_location: str = None,
    #     skills: list[str] | None = None,
    #     skills_provided: bool = False,
    #     educations: list[dict] | None = None,
    #     experiences: list[dict] | None = None,
    # ) -> dict:
    #     """Update user/employee profile and embed new or pending skills."""
    #     user = await db.get(User, user_id)
    #     if not user:
    #         raise ValueError(f"User with id {user_id} not found")

    #     employee_fields = {
    #         "headline": headline,
    #         "summary": summary,
    #         "years_of_experience": years_of_experience,
    #         "current_location": current_location,
    #     }
    #     needs_employee = skills_provided or any(
    #         value is not None for value in employee_fields.values()
    #     )

    #     employee = await UserService._fetch_employee_with_skills(db, user_id)
    #     if needs_employee and not employee:
    #         raise ValueError(f"Employee profile not found for user_id {user_id}")

    #     skills_changed = False
    #     embedded_skill_count = 0
    #     profile_embedding_updated = False
    #     response_skills = [
    #         employee_skill.skill
    #         for employee_skill in employee.employee_skills
    #     ] if employee else []

    #     try:
    #         user_profile_changed = False
    #         if full_name is not None:
    #             user.full_name = full_name
    #             user_profile_changed = True
    #         if phone is not None:
    #             user.phone = phone
    #             user_profile_changed = True
    #         if avatar_url is not None:
    #             user.avatar_url = avatar_url
    #             user_profile_changed = True

    #         employee_profile_changed = False
    #         if employee:
    #             for field_name, value in employee_fields.items():
    #                 if value is not None:
    #                     setattr(employee, field_name, value)
    #                     employee_profile_changed = True

    #         skills_to_embed = []
    #         if skills_provided:
    #             if skills is None:
    #                 raise ValueError("skills must be a list when provided")

    #             normalized_skill_names = UserService._normalize_skill_names(skills or [])
    #             desired_skills, created_skill_keys = await UserService._get_or_create_skills(
    #                 db,
    #                 normalized_skill_names,
    #             )

    #             current_skill_ids = {
    #                 employee_skill.skill_id
    #                 for employee_skill in employee.employee_skills
    #             }
    #             desired_skill_ids = {skill.id for skill in desired_skills}
    #             skills_changed = current_skill_ids != desired_skill_ids

    #             if skills_changed:
    #                 skill_ids_to_remove = current_skill_ids - desired_skill_ids
    #                 if skill_ids_to_remove:
    #                     await db.execute(
    #                         delete(EmployeeSkill).where(
    #                             EmployeeSkill.employee_id == employee.id,
    #                             EmployeeSkill.skill_id.in_(skill_ids_to_remove),
    #                         )
    #                     )

    #                 skill_ids_to_add = desired_skill_ids - current_skill_ids
    #                 for skill_id in skill_ids_to_add:
    #                     db.add(
    #                         EmployeeSkill(
    #                             employee_id=employee.id,
    #                             skill_id=skill_id,
    #                         )
    #                     )

    #             response_skills = desired_skills
    #             skills_to_embed = [
    #                 skill.name
    #                 for skill in desired_skills
    #                 if skill.name.lower() in created_skill_keys
    #                 or skill.embedding_status != "done"
    #             ]

    #         if user_profile_changed or employee_profile_changed or skills_changed:
    #             user.updated_at = datetime.utcnow()

    #         profile_embedding_should_update = (
    #             employee is not None
    #             and (employee_profile_changed or skills_changed)
    #         )
    #         if (skills_to_embed or profile_embedding_should_update) and embedding_service is None:
    #             raise RuntimeError("embedding service is not ready")

    #         await db.flush()

    #         if skills_to_embed:
    #             if embedding_service is None:
    #                 raise RuntimeError("skill embedding service is not ready")

    #             embedded_skill_count = await embedding_service.embed_skills(
    #                 db,
    #                 skills_to_embed,
    #             )

    #         if profile_embedding_should_update:
    #             profile = await embedding_service.get_user_profile(db, user_id)
    #             profile_vector_tfidf = await embedding_service.process_user_profile_tfidf(
    #                 profile
    #             )
    #             profile_vector = await embedding_service.process_user_profile_multimodal(
    #                 profile
    #             )
    #             profile_vector["tfidf_vec"] = profile_vector_tfidf
    #             await embedding_service.upsert_user_profile_embedding(
    #                 db,
    #                 employee.id,
    #                 profile_vector,
    #             )
    #             profile_embedding_updated = True

    #         await db.commit()

    #     except IntegrityError as exc:
    #         await db.rollback()
    #         raise ValueError(f"Failed to update user profile: {exc}") from exc
    #     except Exception:
    #         await db.rollback()
    #         raise

    #     return UserService._serialize_updated_profile(
    #         user=user,
    #         employee=employee,
    #         skills=response_skills,
    #         skills_changed=skills_changed,
    #         embedded_skill_count=embedded_skill_count,
    #         profile_embedding_updated=profile_embedding_updated,
    #     )

    @staticmethod
    async def create_user_education_async(
        db: AsyncSession,
        user_id: int,
        embedding_service: Any,
        school: str = None,
        degree: str = None,
        field_of_study: str = None,
        description: str = None,
        start_date=None,
        end_date=None,
        skills: list[str] | None = None,
    ) -> dict:
        """Create an education record for an employee user."""
        if embedding_service is None:
            raise RuntimeError("embedding service is not ready")

        user = await db.get(User, user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")

        employee_result = await db.execute(
            select(Employee).where(Employee.user_id == user_id)
        )
        employee = employee_result.scalars().first()
        if not employee:
            raise ValueError(f"Employee profile not found for user_id {user_id}")

        if start_date and end_date and end_date < start_date:
            raise ValueError("end_date must be greater than or equal to start_date")

        normalized_skill_names = UserService._normalize_skill_names(skills or [])
        education_skills: list[Skill] = []

        try:
            education = Education(
                employee_id=employee.id,
                school=school,
                degree=degree,
                field_of_study=field_of_study,
                description=description,
                start_date=start_date,
                end_date=end_date,
            )
            db.add(education)
            await db.flush()

            if normalized_skill_names:
                education_skills, _ = await UserService._get_or_create_skills(
                    db,
                    normalized_skill_names,
                )
                for skill in education_skills:
                    db.add(
                        EducationSkill(
                            education_id=education.id,
                            skill_id=skill.id,
                        )
                    )

            education_payload = UserService._build_education_embedding_payload(
                education,
                education_skills,
            )

            user.updated_at = datetime.utcnow()

            await db.commit()
            await db.refresh(education)
        except IntegrityError as exc:
            await db.rollback()
            raise ValueError(f"Failed to create education: {exc}") from exc
        except Exception:
            await db.rollback()
            raise

        try:
            embedding_service.enqueue_education_embedding_update(
                user_id=user_id,
                employee_id=employee.id,
                education_id=education.id,
                education=education_payload,
            )
        except Exception:
            logger.exception(
                "Failed to enqueue education embedding update for user_id=%s, "
                "education_id=%s",
                user_id,
                education.id,
            )

        return UserService._serialize_education(education, education_skills)

    @staticmethod
    async def create_user_education_with_timing_async(
        db: AsyncSession,
        user_id: int,
        embedding_service: Any,
        school: str = None,
        degree: str = None,
        field_of_study: str = None,
        description: str = None,
        start_date=None,
        end_date=None,
        skills: list[str] | None = None,
    ) -> dict:
        """Create an education record and return timing for each processing step."""
        started_at = time.perf_counter()
        timings: dict[str, float] = {}

        def mark(step_name: str, step_started_at: float) -> None:
            timings[step_name] = round((time.perf_counter() - step_started_at) * 1000, 3)

        step_started_at = time.perf_counter()
        if embedding_service is None:
            raise RuntimeError("embedding service is not ready")
        mark("validate_embedding_service", step_started_at)

        step_started_at = time.perf_counter()
        user = await db.get(User, user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")
        mark("fetch_user", step_started_at)

        step_started_at = time.perf_counter()
        employee_result = await db.execute(
            select(Employee).where(Employee.user_id == user_id)
        )
        employee = employee_result.scalars().first()
        if not employee:
            raise ValueError(f"Employee profile not found for user_id {user_id}")
        mark("fetch_employee_profile", step_started_at)

        step_started_at = time.perf_counter()
        if start_date and end_date and end_date < start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        normalized_skill_names = UserService._normalize_skill_names(skills or [])
        education_skills: list[Skill] = []
        mark("validate_dates_and_normalize_skills", step_started_at)

        try:
            step_started_at = time.perf_counter()
            education = Education(
                employee_id=employee.id,
                school=school,
                degree=degree,
                field_of_study=field_of_study,
                description=description,
                start_date=start_date,
                end_date=end_date,
            )
            db.add(education)
            await db.flush()
            mark("create_education_and_flush", step_started_at)

            step_started_at = time.perf_counter()
            if normalized_skill_names:
                education_skills, _ = await UserService._get_or_create_skills(
                    db,
                    normalized_skill_names,
                )
                for skill in education_skills:
                    db.add(
                        EducationSkill(
                            education_id=education.id,
                            skill_id=skill.id,
                        )
                    )
            mark("create_or_link_skills", step_started_at)

            step_started_at = time.perf_counter()
            education_payload = UserService._build_education_embedding_payload(
                education,
                education_skills,
            )
            mark("build_embedding_payload", step_started_at)

            step_started_at = time.perf_counter()
            user.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(education)
            mark("commit_and_refresh", step_started_at)
        except IntegrityError as exc:
            await db.rollback()
            raise ValueError(f"Failed to create education: {exc}") from exc
        except Exception:
            await db.rollback()
            raise

        step_started_at = time.perf_counter()
        try:
            embedding_service.enqueue_education_embedding_update(
                user_id=user_id,
                employee_id=employee.id,
                education_id=education.id,
                education=education_payload,
            )
        except Exception:
            logger.exception(
                "Failed to enqueue education embedding update for user_id=%s, "
                "education_id=%s",
                user_id,
                education.id,
            )
        mark("enqueue_education_embedding_task", step_started_at)

        step_started_at = time.perf_counter()
        education_data = UserService._serialize_education(education, education_skills)
        mark("serialize_response", step_started_at)

        total_ms = round((time.perf_counter() - started_at) * 1000, 3)
        return {
            "data": education_data,
            "timing": {
                "unit": "ms",
                "steps": timings,
                "total": total_ms,
            },
        }

    @staticmethod
    async def update_user_education_async(
        db: AsyncSession,
        user_id: int,
        education_id: int,
        embedding_service: Any,
        school: str = None,
        degree: str = None,
        field_of_study: str = None,
        description: str = None,
        start_date=None,
        end_date=None,
        skills: list[str] | None = None,
        skills_provided: bool = False,
    ) -> dict:
        """Update an education record that belongs to an employee user."""
        if embedding_service is None:
            raise RuntimeError("embedding service is not ready")

        user = await db.get(User, user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")

        result = await db.execute(
            select(Education)
            .join(Employee, Education.employee_id == Employee.id)
            .options(selectinload(Education.education_skills).selectinload(EducationSkill.skill))
            .where(
                Employee.user_id == user_id,
                Education.id == education_id,
            )
        )
        education = result.scalars().first()
        if not education:
            raise ValueError(
                f"Education with id {education_id} not found for user_id {user_id}"
            )

        next_start_date = start_date if start_date is not None else education.start_date
        next_end_date = end_date if end_date is not None else education.end_date
        if next_start_date and next_end_date and next_end_date < next_start_date:
            raise ValueError("end_date must be greater than or equal to start_date")

        response_skills = [
            education_skill.skill
            for education_skill in education.education_skills
        ]

        try:
            fields = {
                "school": school,
                "degree": degree,
                "field_of_study": field_of_study,
                "description": description,
                "start_date": start_date,
                "end_date": end_date,
            }
            for field_name, value in fields.items():
                if value is not None:
                    setattr(education, field_name, value)

            if skills_provided:
                if skills is None:
                    raise ValueError("skills must be a list when provided")

                normalized_skill_names = UserService._normalize_skill_names(skills or [])
                response_skills, _ = await UserService._get_or_create_skills(
                    db,
                    normalized_skill_names,
                )

                current_skill_ids = {
                    education_skill.skill_id
                    for education_skill in education.education_skills
                }
                desired_skill_ids = {skill.id for skill in response_skills}

                skill_ids_to_remove = current_skill_ids - desired_skill_ids
                if skill_ids_to_remove:
                    await db.execute(
                        delete(EducationSkill).where(
                            EducationSkill.education_id == education.id,
                            EducationSkill.skill_id.in_(skill_ids_to_remove),
                        )
                    )

                skill_ids_to_add = desired_skill_ids - current_skill_ids
                for skill_id in skill_ids_to_add:
                    db.add(
                        EducationSkill(
                            education_id=education.id,
                            skill_id=skill_id,
                        )
                    )

            await db.flush()

            education_payload = UserService._build_education_embedding_payload(
                education,
                response_skills,
            )

            user.updated_at = datetime.utcnow()

            await db.commit()
            await db.refresh(education)
        except IntegrityError as exc:
            await db.rollback()
            raise ValueError(f"Failed to update education: {exc}") from exc
        except Exception:
            await db.rollback()
            raise

        try:
            embedding_service.enqueue_education_embedding_update(
                user_id=user_id,
                employee_id=education.employee_id,
                education_id=education.id,
                education=education_payload,
            )
        except Exception:
            logger.exception(
                "Failed to enqueue education embedding update for user_id=%s, "
                "education_id=%s",
                user_id,
                education.id,
            )

        return UserService._serialize_education(education, response_skills)

    @staticmethod
    async def delete_user_education_async(
        db: AsyncSession,
        user_id: int,
        education_id: int,
        embedding_service: Any,
    ) -> dict:
        """Delete an education record that belongs to an employee user."""
        if embedding_service is None:
            raise RuntimeError("embedding service is not ready")

        user = await db.get(User, user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")

        result = await db.execute(
            select(Education)
            .join(Employee, Education.employee_id == Employee.id)
            .where(
                Employee.user_id == user_id,
                Education.id == education_id,
            )
        )
        education = result.scalars().first()
        if not education:
            raise ValueError(
                f"Education with id {education_id} not found for user_id {user_id}"
            )

        employee_id = education.employee_id

        try:
            await db.execute(
                delete(EducationSkill).where(
                    EducationSkill.education_id == education_id
                )
            )
            await db.delete(education)
            await db.flush()

            user.updated_at = datetime.utcnow()

            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise ValueError(f"Failed to delete education: {exc}") from exc
        except Exception:
            await db.rollback()
            raise

        try:
            embedding_service.enqueue_education_embedding_delete(
                user_id=user_id,
                employee_id=employee_id,
                education_id=education_id,
            )
        except Exception:
            logger.exception(
                "Failed to enqueue education embedding delete for user_id=%s, "
                "education_id=%s",
                user_id,
                education_id,
            )

        return {
            "education_id": education_id,
            "deleted": True,
        }

    @staticmethod
    async def create_user_experience_async(
        db: AsyncSession,
        user_id: int,
        embedding_service: Any,
        title: str = None,
        company_name: str = None,
        employment_type: str = None,
        location: str = None,
        location_type: str = None,
        description: str = None,
        start_date=None,
        end_date=None,
        skills: list[str] | None = None,
    ) -> dict:
        """Create a work experience for an employee user."""
        if embedding_service is None:
            raise RuntimeError("embedding service is not ready")

        user = await db.get(User, user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")

        employee_result = await db.execute(
            select(Employee).where(Employee.user_id == user_id)
        )
        employee = employee_result.scalars().first()
        if not employee:
            raise ValueError(f"Employee profile not found for user_id {user_id}")

        if start_date and end_date and end_date < start_date:
            raise ValueError("end_date must be greater than or equal to start_date")

        normalized_skill_names = UserService._normalize_skill_names(skills or [])
        experience_skills: list[Skill] = []

        try:
            experience = Experience(
                employee_id=employee.id,
                title=title,
                company_name=company_name,
                employment_type=employment_type,
                location=location,
                location_type=location_type,
                description=description,
                start_date=start_date,
                end_date=end_date,
            )
            db.add(experience)
            await db.flush()

            if normalized_skill_names:
                experience_skills, _ = await UserService._get_or_create_skills(
                    db,
                    normalized_skill_names,
                )
                for skill in experience_skills:
                    db.add(
                        ExperienceSkill(
                            experience_id=experience.id,
                            skill_id=skill.id,
                        )
                    )

            experience_payload = UserService._build_experience_embedding_payload(
                experience,
                experience_skills,
            )

            user.updated_at = datetime.utcnow()

            await db.commit()
            await db.refresh(experience)
        except IntegrityError as exc:
            await db.rollback()
            raise ValueError(f"Failed to create experience: {exc}") from exc
        except Exception:
            await db.rollback()
            raise

        try:
            embedding_service.enqueue_experience_embedding_update(
                user_id=user_id,
                employee_id=employee.id,
                experience_id=experience.id,
                experience=experience_payload,
            )
        except Exception:
            logger.exception(
                "Failed to enqueue experience embedding update for user_id=%s, "
                "experience_id=%s",
                user_id,
                experience.id,
            )

        return UserService._serialize_experience(experience, experience_skills)

    @staticmethod
    async def update_user_experience_async(
        db: AsyncSession,
        user_id: int,
        experience_id: int,
        embedding_service: Any,
        title: str = None,
        company_name: str = None,
        employment_type: str = None,
        location: str = None,
        location_type: str = None,
        description: str = None,
        start_date=None,
        end_date=None,
        skills: list[str] | None = None,
        skills_provided: bool = False,
    ) -> dict:
        """Update a work experience that belongs to an employee user."""
        if embedding_service is None:
            raise RuntimeError("embedding service is not ready")

        user = await db.get(User, user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")

        result = await db.execute(
            select(Experience)
            .join(Employee, Experience.employee_id == Employee.id)
            .options(selectinload(Experience.experience_skills).selectinload(ExperienceSkill.skill))
            .where(
                Employee.user_id == user_id,
                Experience.id == experience_id,
            )
        )
        experience = result.scalars().first()
        if not experience:
            raise ValueError(
                f"Experience with id {experience_id} not found for user_id {user_id}"
            )

        next_start_date = start_date if start_date is not None else experience.start_date
        next_end_date = end_date if end_date is not None else experience.end_date
        if next_start_date and next_end_date and next_end_date < next_start_date:
            raise ValueError("end_date must be greater than or equal to start_date")

        response_skills = [
            experience_skill.skill
            for experience_skill in experience.experience_skills
        ]

        try:
            fields = {
                "title": title,
                "company_name": company_name,
                "employment_type": employment_type,
                "location": location,
                "location_type": location_type,
                "description": description,
                "start_date": start_date,
                "end_date": end_date,
            }
            for field_name, value in fields.items():
                if value is not None:
                    setattr(experience, field_name, value)

            if skills_provided:
                if skills is None:
                    raise ValueError("skills must be a list when provided")

                normalized_skill_names = UserService._normalize_skill_names(skills or [])
                response_skills, _ = await UserService._get_or_create_skills(
                    db,
                    normalized_skill_names,
                )

                current_skill_ids = {
                    experience_skill.skill_id
                    for experience_skill in experience.experience_skills
                }
                desired_skill_ids = {skill.id for skill in response_skills}

                skill_ids_to_remove = current_skill_ids - desired_skill_ids
                if skill_ids_to_remove:
                    await db.execute(
                        delete(ExperienceSkill).where(
                            ExperienceSkill.experience_id == experience.id,
                            ExperienceSkill.skill_id.in_(skill_ids_to_remove),
                        )
                    )

                skill_ids_to_add = desired_skill_ids - current_skill_ids
                for skill_id in skill_ids_to_add:
                    db.add(
                        ExperienceSkill(
                            experience_id=experience.id,
                            skill_id=skill_id,
                        )
                    )

            await db.flush()

            experience_payload = UserService._build_experience_embedding_payload(
                experience,
                response_skills,
            )

            user.updated_at = datetime.utcnow()

            await db.commit()
            await db.refresh(experience)
        except IntegrityError as exc:
            await db.rollback()
            raise ValueError(f"Failed to update experience: {exc}") from exc
        except Exception:
            await db.rollback()
            raise

        try:
            embedding_service.enqueue_experience_embedding_update(
                user_id=user_id,
                employee_id=experience.employee_id,
                experience_id=experience.id,
                experience=experience_payload,
            )
        except Exception:
            logger.exception(
                "Failed to enqueue experience embedding update for user_id=%s, "
                "experience_id=%s",
                user_id,
                experience.id,
            )

        return UserService._serialize_experience(experience, response_skills)

    @staticmethod
    async def delete_user_experience_async(
        db: AsyncSession,
        user_id: int,
        experience_id: int,
        embedding_service: Any,
    ) -> dict:
        """Delete a work experience that belongs to an employee user."""
        if embedding_service is None:
            raise RuntimeError("embedding service is not ready")

        user = await db.get(User, user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")

        result = await db.execute(
            select(Experience)
            .join(Employee, Experience.employee_id == Employee.id)
            .where(
                Employee.user_id == user_id,
                Experience.id == experience_id,
            )
        )
        experience = result.scalars().first()
        if not experience:
            raise ValueError(
                f"Experience with id {experience_id} not found for user_id {user_id}"
            )

        employee_id = experience.employee_id

        try:
            await db.execute(
                delete(ExperienceSkill).where(
                    ExperienceSkill.experience_id == experience_id
                )
            )
            await db.delete(experience)
            await db.flush()

            user.updated_at = datetime.utcnow()

            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise ValueError(f"Failed to delete experience: {exc}") from exc
        except Exception:
            await db.rollback()
            raise

        try:
            embedding_service.enqueue_experience_embedding_delete(
                user_id=user_id,
                employee_id=employee_id,
                experience_id=experience_id,
            )
        except Exception:
            logger.exception(
                "Failed to enqueue experience embedding delete for user_id=%s, "
                "experience_id=%s",
                user_id,
                experience_id,
            )

        return {
            "experience_id": experience_id,
            "deleted": True,
        }

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> dict:
        """Retrieve user information by user_id."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User with id {user_id} not found")

        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "role": user.role,
            "avatar_url": user.avatar_url,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        }

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> dict:
        """Retrieve user information by email."""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise ValueError(f"User with email {email} not found")

        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "role": user.role,
            "avatar_url": user.avatar_url,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        }

    @staticmethod
    def update_user_profile(
        db: Session,
        user_id: int,
        full_name: str = None,
        phone: str = None,
        avatar_url: str = None,
    ) -> dict:
        """Update user profile information."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User with id {user_id} not found")

        if full_name is not None:
            user.full_name = full_name
        if phone is not None:
            user.phone = phone
        if avatar_url is not None:
            user.avatar_url = avatar_url

        user.updated_at = datetime.utcnow()

        try:
            db.commit()
            db.refresh(user)
        except IntegrityError as exc:
            db.rollback()
            raise ValueError(f"Failed to update user profile: {exc}") from exc

        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "role": user.role,
            "avatar_url": user.avatar_url,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        }

    @staticmethod
    def create_employee_profile(
        db: Session,
        user_id: int,
        headline: str = None,
        summary: str = None,
        years_of_experience: int = 0,
        current_location: str = None,
    ) -> dict:
        """Create an employee profile for a user."""
        existing_employee = db.query(Employee).filter(Employee.user_id == user_id).first()
        if existing_employee:
            raise ValueError(f"Employee profile already exists for user_id {user_id}")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User with id {user_id} not found")

        employee = Employee(
            user_id=user_id,
            headline=headline,
            summary=summary,
            years_of_experience=years_of_experience,
            current_location=current_location,
        )

        try:
            db.add(employee)
            db.commit()
            db.refresh(employee)
        except IntegrityError as exc:
            db.rollback()
            raise ValueError(f"Failed to create employee profile: {exc}") from exc

        return {
            "employee_id": employee.id,
            "user_id": employee.user_id,
            "headline": employee.headline,
            "summary": employee.summary,
            "years_of_experience": employee.years_of_experience,
            "current_location": employee.current_location,
            "created_at": employee.created_at.isoformat() if employee.created_at else None,
        }

    @staticmethod
    def update_employee_profile(
        db: Session,
        user_id: int,
        headline: str = None,
        summary: str = None,
        years_of_experience: int = None,
        current_location: str = None,
    ) -> dict:
        """Update an employee profile."""
        employee = db.query(Employee).filter(Employee.user_id == user_id).first()
        if not employee:
            raise ValueError(f"Employee profile not found for user_id {user_id}")

        if headline is not None:
            employee.headline = headline
        if summary is not None:
            employee.summary = summary
        if years_of_experience is not None:
            employee.years_of_experience = years_of_experience
        if current_location is not None:
            employee.current_location = current_location

        try:
            db.commit()
            db.refresh(employee)
        except IntegrityError as exc:
            db.rollback()
            raise ValueError(f"Failed to update employee profile: {exc}") from exc

        return {
            "employee_id": employee.id,
            "user_id": employee.user_id,
            "headline": employee.headline,
            "summary": employee.summary,
            "years_of_experience": employee.years_of_experience,
            "current_location": employee.current_location,
        }

    @staticmethod
    async def add_employee_skill_async(
        db: AsyncSession,
        user_id: int,
        embedding_service: Any,
        skill_name: str,
    ) -> dict:
        """Add a standalone skill to an employee."""
        if embedding_service is None:
            raise RuntimeError("embedding service is not ready")

        user = await db.get(User, user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")

        employee_result = await db.execute(
            select(Employee).where(Employee.user_id == user_id)
        )
        employee = employee_result.scalars().first()
        if not employee:
            raise ValueError(f"Employee profile not found for user_id {user_id}")

        normalized_skill_names = UserService._normalize_skill_names([skill_name])
        skill, _ = await UserService._get_or_create_skills(db, normalized_skill_names)
        skill = skill[0]

        education_skill_result = await db.execute(
            select(EducationSkill.skill_id)
            .join(Education, EducationSkill.education_id == Education.id)
            .where(
                Education.employee_id == employee.id,
                EducationSkill.skill_id == skill.id,
            )
        )
        if education_skill_result.scalar_one_or_none() is not None:
            raise ValueError(
                f"Skill {skill.name} already belongs to an education record"
            )

        experience_skill_result = await db.execute(
            select(ExperienceSkill.skill_id)
            .join(Experience, ExperienceSkill.experience_id == Experience.id)
            .where(
                Experience.employee_id == employee.id,
                ExperienceSkill.skill_id == skill.id,
            )
        )
        if experience_skill_result.scalar_one_or_none() is not None:
            raise ValueError(
                f"Skill {skill.name} already belongs to an experience record"
            )

        existing_skill_result = await db.execute(
            select(EmployeeSkill).where(
                EmployeeSkill.employee_id == employee.id,
                EmployeeSkill.skill_id == skill.id,
            )
        )
        if existing_skill_result.scalars().first():
            raise ValueError(f"Employee already has standalone skill {skill.id}")

        try:
            db.add(EmployeeSkill(employee_id=employee.id, skill_id=skill.id))
            user.updated_at = datetime.utcnow()
            await db.flush()
            employee_id = employee.id
            skill_id = skill.id
            response_skill_name = skill.name

            if skill.embedding_status != "done":
                await embedding_service.embed_skills(
                    db,
                    [skill.name],
                )

            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise ValueError(f"Failed to add skill to employee: {exc}") from exc
        except Exception:
            await db.rollback()
            raise

        return {
            "employee_id": employee_id,
            "skill_id": skill_id,
            "skill_name": response_skill_name,
        }

    @staticmethod
    async def remove_employee_skill_async(
        db: AsyncSession,
        user_id: int,
        skill_id: int,
    ) -> dict:
        """Remove a standalone skill from an employee."""
        user = await db.get(User, user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")

        employee_result = await db.execute(
            select(Employee).where(Employee.user_id == user_id)
        )
        employee = employee_result.scalars().first()
        if not employee:
            raise ValueError(f"Employee profile not found for user_id {user_id}")

        employee_skill_result = await db.execute(
            select(EmployeeSkill).where(
                EmployeeSkill.employee_id == employee.id,
                EmployeeSkill.skill_id == skill_id,
            )
        )
        employee_skill = employee_skill_result.scalars().first()
        if not employee_skill:
            raise ValueError(f"Employee standalone skill {skill_id} not found")

        try:
            employee_id = employee.id
            await db.delete(employee_skill)
            user.updated_at = datetime.utcnow()
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise ValueError(f"Failed to remove skill from employee: {exc}") from exc
        except Exception:
            await db.rollback()
            raise

        return {
            "employee_id": employee_id,
            "skill_id": skill_id,
            "message": "Skill removed successfully",
        }

    @staticmethod
    async def list_user_skills_async(db: AsyncSession, user_id: int) -> list:
        """List all standalone skills for a user."""
        employee = await UserService._fetch_employee_with_skills(db, user_id)
        if not employee:
            raise ValueError(f"Employee profile not found for user_id {user_id}")

        return [
            {"skill_id": employee_skill.skill_id, "skill_name": employee_skill.skill.name}
            for employee_skill in employee.employee_skills
        ]

    @staticmethod
    async def get_full_user_profile_async(db: AsyncSession, user_id: int) -> dict:
        """Retrieve a full employee profile for API display."""
        result = await db.execute(
            select(User)
            .options(
                selectinload(User.employee)
                .selectinload(Employee.employee_skills)
                .selectinload(EmployeeSkill.skill),
                selectinload(User.employee)
                .selectinload(Employee.educations)
                .selectinload(Education.education_skills)
                .selectinload(EducationSkill.skill),
                selectinload(User.employee)
                .selectinload(Employee.experiences)
                .selectinload(Experience.experience_skills)
                .selectinload(ExperienceSkill.skill),
            )
            .where(User.id == user_id)
        )
        user = result.scalars().first()
        if not user:
            raise ValueError(f"User with id {user_id} not found")

        employee = user.employee
        if not employee:
            raise ValueError(f"Employee profile not found for user_id {user_id}")

        educations = [
            UserService._serialize_education(
                education,
                [
                    education_skill.skill
                    for education_skill in education.education_skills
                ],
            )
            for education in employee.educations
        ]
        experiences = [
            UserService._serialize_experience(
                experience,
                [
                    experience_skill.skill
                    for experience_skill in experience.experience_skills
                ],
            )
            for experience in employee.experiences
        ]
        skills = [
            {
                "skill_id": employee_skill.skill_id,
                "skill_name": employee_skill.skill.name,
            }
            for employee_skill in employee.employee_skills
        ]

        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "role": user.role,
            "avatar_url": user.avatar_url,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "employee_profile": {
                "employee_id": employee.id,
                "headline": employee.headline,
                "summary": employee.summary,
                "years_of_experience": employee.years_of_experience,
                "current_location": employee.current_location,
                "created_at": (
                    employee.created_at.isoformat()
                    if employee.created_at
                    else None
                ),
            },
            "experiences": experiences,
            "educations": educations,
            "skills": skills,
        }

    @staticmethod
    def add_employee_skill(db: Session, user_id: int, skill_id: int) -> dict:
        """Add a skill to an employee."""
        employee = db.query(Employee).filter(Employee.user_id == user_id).first()
        if not employee:
            raise ValueError(f"Employee profile not found for user_id {user_id}")

        skill = db.query(Skill).filter(Skill.id == skill_id).first()
        if not skill:
            raise ValueError(f"Skill with id {skill_id} not found")

        existing_skill = (
            db.query(EmployeeSkill)
            .filter(
                EmployeeSkill.employee_id == employee.id,
                EmployeeSkill.skill_id == skill_id,
            )
            .first()
        )
        if existing_skill:
            raise ValueError(f"Employee already has skill {skill_id}")

        employee_skill = EmployeeSkill(employee_id=employee.id, skill_id=skill_id)

        try:
            db.add(employee_skill)
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError(f"Failed to add skill to employee: {exc}") from exc

        return {
            "employee_id": employee.id,
            "skill_id": skill_id,
            "skill_name": skill.name,
        }

    @staticmethod
    def remove_employee_skill(db: Session, user_id: int, skill_id: int) -> dict:
        """Remove a skill from an employee."""
        employee = db.query(Employee).filter(Employee.user_id == user_id).first()
        if not employee:
            raise ValueError(f"Employee profile not found for user_id {user_id}")

        employee_skill = (
            db.query(EmployeeSkill)
            .filter(
                EmployeeSkill.employee_id == employee.id,
                EmployeeSkill.skill_id == skill_id,
            )
            .first()
        )
        if not employee_skill:
            raise ValueError(f"Employee does not have skill {skill_id}")

        try:
            db.delete(employee_skill)
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError(f"Failed to remove skill from employee: {exc}") from exc

        return {
            "employee_id": employee.id,
            "skill_id": skill_id,
            "message": "Skill removed successfully",
        }

    @staticmethod
    def list_user_skills(db: Session, user_id: int) -> list:
        """List all skills for a user."""
        employee = db.query(Employee).filter(Employee.user_id == user_id).first()
        if not employee:
            raise ValueError(f"Employee profile not found for user_id {user_id}")

        skills = []
        if employee.employee_skills:
            skills = [
                {"skill_id": es.skill_id, "skill_name": es.skill.name}
                for es in employee.employee_skills
            ]

        return skills

    @staticmethod
    def get_user_full_profile(db: Session, user_id: int) -> dict:
        """Get complete user profile with all related information."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User with id {user_id} not found")

        employee = user.employee

        user_data = {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "role": user.role,
            "avatar_url": user.avatar_url,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        }

        if employee:
            user_data["employee_profile"] = {
                "employee_id": employee.id,
                "headline": employee.headline,
                "summary": employee.summary,
                "years_of_experience": employee.years_of_experience,
                "current_location": employee.current_location,
            }

            if employee.employee_skills:
                user_data["skills"] = [
                    {"skill_id": es.skill_id, "skill_name": es.skill.name}
                    for es in employee.employee_skills
                ]
            else:
                user_data["skills"] = []
        else:
            user_data["employee_profile"] = None
            user_data["skills"] = []

        return user_data
