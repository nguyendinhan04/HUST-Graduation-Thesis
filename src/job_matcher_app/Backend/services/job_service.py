from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models import Application, Company, Employee, Employer, Job, JobSkill, Skill, User


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
    def _serialize_open_job_summary(job: Job, company: Company) -> dict:
        return {
            "id": job.id,
            "job_id": job.id,
            "title": job.title,
            "salary_min": str(job.salary_min) if job.salary_min is not None else None,
            "salary_max": str(job.salary_max) if job.salary_max is not None else None,
            "salary_currency": job.salary_currency,
            "location": job.address,
            "location_type": job.location_type,
            "experience_required": job.experience_required,
            "employment_type": job.employment_type,
            "working_time": job.working_time,
            "deadline": job.deadline.isoformat() if job.deadline else None,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "company_name": company.name,
            "company_logo_url": company.logo_url,
        }

    @staticmethod
    def _serialize_application(application: Application) -> dict:
        return {
            "application_id": application.id,
            "employee_id": application.employee_id,
            "job_id": application.job_id,
            "status": application.status,
            "applied_at": (
                application.applied_at.isoformat()
                if application.applied_at
                else None
            ),
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

        prepared_vector_tasks = []
        try:
            db.add(job)
            await db.flush()

            job_payload = JobService._build_job_embedding_payload(job)
            prepared_vector_tasks = [
                await embedding_service.prepare_job_bert_embedding_update_outbox_task(
                    db,
                    job_id=job.id,
                    job_payload=job_payload,
                ),
                await embedding_service.prepare_job_tfidf_embedding_update_outbox_task(
                    db,
                    job_id=job.id,
                    job_payload=job_payload,
                ),
                await embedding_service.prepare_job_skill_extraction_update_outbox_task(
                    db,
                    job_id=job.id,
                    job_payload=job_payload,
                ),
            ]

            await db.commit()
            await db.refresh(job)
        except IntegrityError as exc:
            await db.rollback()
            raise ValueError(f"Failed to create job: {exc}") from exc
        except Exception:
            await db.rollback()
            raise

        bert_job_id = embedding_service.enqueue_prepared_outbox_task(
            prepared_vector_tasks[0]
        )
        tfidf_job_id = embedding_service.enqueue_prepared_outbox_task(
            prepared_vector_tasks[1]
        )
        skill_extraction_job_id = embedding_service.enqueue_prepared_outbox_task(
            prepared_vector_tasks[2]
        )
        vector_jobs = {
            "bert_job_id": bert_job_id,
            "tfidf_job_id": tfidf_job_id,
            "skill_extraction_job_id": skill_extraction_job_id,
            "outbox_ids": embedding_service.get_last_outbox_ids(),
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
    async def search_open_jobs_async(
        db: AsyncSession,
        current_user: User,
        query: str | None = None,
        location: str | None = None,
        employment_type: str | None = None,
        max_experience: int | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> dict:
        if current_user.role == "employer":
            filters = [Job.status.in_(("open", "closed"))]
        else:
            filters = [Job.status == "open"]
        stmt = (
            select(Job, Company)
            .join(Company, Job.company_id == Company.id)
        )

        normalized_query = query.strip() if query else ""
        if normalized_query:
            pattern = f"%{normalized_query}%"
            filters.append(Job.title.ilike(pattern))

        normalized_location = location.strip() if location else ""
        if normalized_location:
            pattern = f"%{normalized_location}%"
            filters.append(
                or_(
                    Job.address.ilike(pattern),
                    Job.location_type.ilike(pattern),
                    Company.location.ilike(pattern),
                )
            )

        normalized_employment_type = employment_type.strip() if employment_type else ""
        if normalized_employment_type:
            filters.append(Job.employment_type.ilike(f"%{normalized_employment_type}%"))

        if max_experience is not None:
            filters.append(
                or_(
                    Job.experience_required.is_(None),
                    Job.experience_required <= max_experience,
                )
            )

        total = await db.scalar(
            select(func.count())
            .select_from(Job)
            .join(Company, Job.company_id == Company.id)
            .where(*filters)
        )
        total_count = int(total or 0)
        total_pages = max((total_count + page_size - 1) // page_size, 1)
        current_page = min(max(page, 1), total_pages)
        offset = (current_page - 1) * page_size

        stmt = (
            stmt.where(*filters)
            .order_by(Job.created_at.desc(), Job.id.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows = (await db.execute(stmt)).all()
        items = [
            JobService._serialize_open_job_summary(job, company)
            for job, company in rows
        ]
        return {
            "items": items,
            "total": total_count,
            "page": current_page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    @staticmethod
    async def apply_job_for_employee_async(
        db: AsyncSession,
        current_user: User,
        job_id: int,
    ) -> dict:
        if current_user.role != "employee":
            raise PermissionError("Only employees can apply for jobs")

        employee_result = await db.execute(
            select(Employee).where(Employee.user_id == current_user.id)
        )
        employee = employee_result.scalars().first()
        if employee is None:
            raise ValueError(f"Employee profile not found for user_id {current_user.id}")

        job = await db.get(Job, job_id)
        if job is None:
            raise ValueError(f"Job with id {job_id} not found")

        if job.status != "open":
            raise ValueError("Only open jobs can be applied to")

        if job.deadline:
            now = (
                datetime.now(job.deadline.tzinfo)
                if job.deadline.tzinfo
                else datetime.now()
            )
            if job.deadline < now:
                raise ValueError("Job application deadline has passed")

        existing_application_result = await db.execute(
            select(Application).where(
                Application.employee_id == employee.id,
                Application.job_id == job.id,
            )
        )
        existing_application = existing_application_result.scalars().first()
        if existing_application is not None:
            raise ValueError("Employee already applied to this job")

        application = Application(
            employee_id=employee.id,
            job_id=job.id,
            status="pending",
        )

        try:
            db.add(application)
            await db.commit()
            await db.refresh(application)
        except IntegrityError as exc:
            await db.rollback()
            raise ValueError(f"Failed to apply for job: {exc}") from exc
        except Exception:
            await db.rollback()
            raise

        return JobService._serialize_application(application)

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

        prepared_vector_tasks = []
        try:
            if vector_source_changed:
                await db.flush()
                job_payload = JobService._build_job_embedding_payload(job)
                prepared_vector_tasks = [
                    await embedding_service.prepare_job_bert_embedding_update_outbox_task(
                        db,
                        job_id=job.id,
                        job_payload=job_payload,
                    ),
                    await embedding_service.prepare_job_tfidf_embedding_update_outbox_task(
                        db,
                        job_id=job.id,
                        job_payload=job_payload,
                    ),
                    await embedding_service.prepare_job_skill_extraction_update_outbox_task(
                        db,
                        job_id=job.id,
                        job_payload=job_payload,
                    ),
                ]

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
            bert_job_id = embedding_service.enqueue_prepared_outbox_task(
                prepared_vector_tasks[0]
            )
            tfidf_job_id = embedding_service.enqueue_prepared_outbox_task(
                prepared_vector_tasks[1]
            )
            skill_extraction_job_id = embedding_service.enqueue_prepared_outbox_task(
                prepared_vector_tasks[2]
            )
            vector_jobs = {
                "bert_job_id": bert_job_id,
                "tfidf_job_id": tfidf_job_id,
                "skill_extraction_job_id": skill_extraction_job_id,
                "outbox_ids": embedding_service.get_last_outbox_ids(),
                "status": "queued",
            }
        else:
            vector_jobs = {
                "status": "skipped",
                "reason": "vector_source_unchanged",
            }

        return JobService._serialize_job(job, job_skills, vector_jobs)
