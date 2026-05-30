from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models import Employer, Job, JobSkill, Skill, User


class JobService:
    """Service for employer job posting workflows."""

    VALID_STATUSES = {"open", "closed", "draft"}

    @staticmethod
    async def _fetch_job_skills(
        db: AsyncSession,
        job_id: int,
    ) -> list[tuple[Skill, bool]]:
        result = await db.execute(
            select(Skill, JobSkill.is_required)
            .join(JobSkill, JobSkill.skill_id == Skill.id)
            .where(JobSkill.job_id == job_id)
            .order_by(Skill.name)
        )
        return [(row[0], row[1]) for row in result.all()]

    @staticmethod
    def _serialize_job(
        job: Job,
        skills: list[tuple[Skill, bool]],
        vector_jobs: dict | None = None,
    ) -> dict:
        return {
            "job_id": job.id,
            "employer_id": job.employer_id,
            "company_id": job.company_id,
            "title": job.title,
            "description": job.description,
            "requirement": job.requirement,
            "benefit": job.benefit,
            "salary_min": str(job.salary_min) if job.salary_min is not None else None,
            "salary_max": str(job.salary_max) if job.salary_max is not None else None,
            "salary_currency": job.salary_currency,
            "experience_required": job.experience_required,
            "employment_type": job.employment_type,
            "working_time": job.working_time,
            "location_type": job.location_type,
            "address": job.address,
            "deadline": job.deadline.isoformat() if job.deadline else None,
            "status": job.status,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "skills": [
                {
                    "skill_id": skill.id,
                    "skill_name": skill.name,
                    "is_required": is_required,
                }
                for skill, is_required in skills
            ],
            "vector_jobs": vector_jobs,
        }

    @staticmethod
    def _serialize_job_summary(job: Job) -> dict:
        return {
            "job_id": job.id,
            "title": job.title,
            "status": job.status,
            "salary_min": str(job.salary_min) if job.salary_min is not None else None,
            "salary_max": str(job.salary_max) if job.salary_max is not None else None,
            "salary_currency": job.salary_currency,
            "experience_required": job.experience_required,
            "employment_type": job.employment_type,
            "working_time": job.working_time,
            "location_type": job.location_type,
            "address": job.address,
            "deadline": job.deadline.isoformat() if job.deadline else None,
            "created_at": job.created_at.isoformat() if job.created_at else None,
        }

    @staticmethod
    def _build_job_embedding_payload(job: Job) -> dict:
        return {
            "job_id": job.id,
            "job_title": job.title,
            "title": job.title,
            "description": job.description,
            "requirement": job.requirement,
        }

    @staticmethod
    async def create_job_for_employer_async(
        db: AsyncSession,
        current_user: User,
        embedding_service: Any,
        title: str,
        description: str = None,
        requirement: str = None,
        benefit: str = None,
        salary_min: Decimal = None,
        salary_max: Decimal = None,
        salary_currency: str = None,
        experience_required: int = None,
        employment_type: str = None,
        working_time: str = None,
        location_type: str = None,
        address: str = None,
        deadline: datetime = None,
        status: str = "open",
    ) -> dict:
        if current_user.role != "employer":
            raise PermissionError("Only employers can create jobs")

        normalized_title = title.strip() if title else ""
        if not normalized_title:
            raise ValueError("title must not be empty")

        job_status = status or "open"
        if job_status not in JobService.VALID_STATUSES:
            raise ValueError("status must be one of: open, closed, draft")

        if salary_min is not None and salary_min < 0:
            raise ValueError("salary_min must be greater than or equal to 0")
        if salary_max is not None and salary_max < 0:
            raise ValueError("salary_max must be greater than or equal to 0")
        if (
            salary_min is not None
            and salary_max is not None
            and salary_max < salary_min
        ):
            raise ValueError("salary_max must be greater than or equal to salary_min")

        employer_result = await db.execute(
            select(Employer).where(Employer.user_id == current_user.id)
        )
        employer = employer_result.scalars().first()
        if employer is None:
            raise ValueError(f"Employer profile not found for user_id {current_user.id}")

        job = Job(
            employer_id=employer.id,
            company_id=employer.company_id,
            title=normalized_title,
            description=description,
            requirement=requirement,
            benefit=benefit,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            experience_required=experience_required,
            employment_type=employment_type,
            working_time=working_time,
            location_type=location_type,
            address=address,
            deadline=deadline,
            status=job_status,
        )

        try:
            db.add(job)
            await db.flush()

            await db.commit()
            await db.refresh(job)
        except IntegrityError as exc:
            await db.rollback()
            raise ValueError(f"Failed to create job: {exc}") from exc
        except Exception:
            await db.rollback()
            raise

        job_payload = JobService._build_job_embedding_payload(job)
        bert_job_id = embedding_service.enqueue_job_bert_embedding_update(
            job_id=job.id,
            job_payload=job_payload,
        )
        tfidf_job_id = embedding_service.enqueue_job_tfidf_embedding_update(
            job_id=job.id,
            job_payload=job_payload,
        )
        skill_extraction_job_id = embedding_service.enqueue_job_skill_extraction_update(
            job_id=job.id,
            job_payload=job_payload,
        )
        vector_jobs = {
            "bert_job_id": bert_job_id,
            "tfidf_job_id": tfidf_job_id,
            "skill_extraction_job_id": skill_extraction_job_id,
            "status": "queued",
        }

        return JobService._serialize_job(job, [], vector_jobs)

    @staticmethod
    async def list_jobs_for_employer_async(
        db: AsyncSession,
        current_user: User,
    ) -> list[dict]:
        if current_user.role != "employer":
            raise PermissionError("Only employers can list their jobs")

        employer_result = await db.execute(
            select(Employer).where(Employer.user_id == current_user.id)
        )
        employer = employer_result.scalars().first()
        if employer is None:
            raise ValueError(f"Employer profile not found for user_id {current_user.id}")

        jobs_result = await db.execute(
            select(Job)
            .where(
                Job.employer_id == employer.id,
                Job.status.in_(("open", "closed")),
            )
            .order_by(Job.created_at.desc(), Job.id.desc())
        )
        jobs = jobs_result.scalars().all()
        return [JobService._serialize_job_summary(job) for job in jobs]

    @staticmethod
    async def update_job_for_employer_async(
        db: AsyncSession,
        current_user: User,
        embedding_service: Any,
        job_id: int,
        fields_set: set[str],
        title: str = None,
        description: str = None,
        requirement: str = None,
        benefit: str = None,
        salary_min: Decimal = None,
        salary_max: Decimal = None,
        salary_currency: str = None,
        experience_required: int = None,
        employment_type: str = None,
        working_time: str = None,
        location_type: str = None,
        address: str = None,
        deadline: datetime = None,
        status: str = None,
    ) -> dict:
        if current_user.role != "employer":
            raise PermissionError("Only employers can update jobs")

        employer_result = await db.execute(
            select(Employer).where(Employer.user_id == current_user.id)
        )
        employer = employer_result.scalars().first()
        if employer is None:
            raise ValueError(f"Employer profile not found for user_id {current_user.id}")

        job = await db.get(Job, job_id)
        if job is None:
            raise ValueError(f"Job with id {job_id} not found")
        if job.employer_id != employer.id:
            raise PermissionError("You do not have permission to update this job")

        if "title" in fields_set:
            title = title.strip() if title else ""
            if not title:
                raise ValueError("title must not be empty")

        if "status" in fields_set:
            if not status or status not in JobService.VALID_STATUSES:
                raise ValueError("status must be one of: open, closed, draft")

        proposed_salary_min = salary_min if "salary_min" in fields_set else job.salary_min
        proposed_salary_max = salary_max if "salary_max" in fields_set else job.salary_max
        if proposed_salary_min is not None and proposed_salary_min < 0:
            raise ValueError("salary_min must be greater than or equal to 0")
        if proposed_salary_max is not None and proposed_salary_max < 0:
            raise ValueError("salary_max must be greater than or equal to 0")
        if (
            proposed_salary_min is not None
            and proposed_salary_max is not None
            and proposed_salary_max < proposed_salary_min
        ):
            raise ValueError("salary_max must be greater than or equal to salary_min")

        vector_source_changed = False
        if "title" in fields_set and job.title != title:
            vector_source_changed = True
        if "description" in fields_set and job.description != description:
            vector_source_changed = True
        if "requirement" in fields_set and job.requirement != requirement:
            vector_source_changed = True

        update_fields = {
            "title": title,
            "description": description,
            "requirement": requirement,
            "benefit": benefit,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": salary_currency,
            "experience_required": experience_required,
            "employment_type": employment_type,
            "working_time": working_time,
            "location_type": location_type,
            "address": address,
            "deadline": deadline,
            "status": status,
        }
        for field_name, value in update_fields.items():
            if field_name in fields_set:
                setattr(job, field_name, value)

        try:
            await db.commit()
            await db.refresh(job)
            job_skills = await JobService._fetch_job_skills(db, job.id)
        except IntegrityError as exc:
            await db.rollback()
            raise ValueError(f"Failed to update job: {exc}") from exc
        except Exception:
            await db.rollback()
            raise

        if vector_source_changed:
            job_payload = JobService._build_job_embedding_payload(job)
            bert_job_id = embedding_service.enqueue_job_bert_embedding_update(
                job_id=job.id,
                job_payload=job_payload,
            )
            tfidf_job_id = embedding_service.enqueue_job_tfidf_embedding_update(
                job_id=job.id,
                job_payload=job_payload,
            )
            skill_extraction_job_id = embedding_service.enqueue_job_skill_extraction_update(
                job_id=job.id,
                job_payload=job_payload,
            )
            vector_jobs = {
                "bert_job_id": bert_job_id,
                "tfidf_job_id": tfidf_job_id,
                "skill_extraction_job_id": skill_extraction_job_id,
                "status": "queued",
            }
        else:
            vector_jobs = {
                "status": "skipped",
                "reason": "vector_source_unchanged",
            }

        return JobService._serialize_job(job, job_skills, vector_jobs)
