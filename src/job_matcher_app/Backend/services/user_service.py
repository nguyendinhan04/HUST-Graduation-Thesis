from datetime import datetime
from typing import Any

from passlib.context import CryptContext
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from models import User, Employee, EmployeeSkill, Skill


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
BCRYPT_MAX_PASSWORD_BYTES = 72


class UserService:
    """Service for managing user information and profiles."""

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
        if len(password.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
            raise ValueError(
                f"password must not exceed {BCRYPT_MAX_PASSWORD_BYTES} bytes"
            )

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

    @staticmethod
    async def update_user_profile_async(
        db: AsyncSession,
        user_id: int,
        embedding_service: Any,
        full_name: str = None,
        phone: str = None,
        avatar_url: str = None,
        headline: str = None,
        summary: str = None,
        years_of_experience: int = None,
        current_location: str = None,
        skills: list[str] | None = None,
        skills_provided: bool = False,
    ) -> dict:
        """Update user/employee profile and embed new or pending skills."""
        user = await db.get(User, user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")

        employee_fields = {
            "headline": headline,
            "summary": summary,
            "years_of_experience": years_of_experience,
            "current_location": current_location,
        }
        needs_employee = skills_provided or any(
            value is not None for value in employee_fields.values()
        )

        employee = await UserService._fetch_employee_with_skills(db, user_id)
        if needs_employee and not employee:
            raise ValueError(f"Employee profile not found for user_id {user_id}")

        skills_changed = False
        embedded_skill_count = 0
        profile_embedding_updated = False
        response_skills = [
            employee_skill.skill
            for employee_skill in employee.employee_skills
        ] if employee else []

        try:
            user_profile_changed = False
            if full_name is not None:
                user.full_name = full_name
                user_profile_changed = True
            if phone is not None:
                user.phone = phone
                user_profile_changed = True
            if avatar_url is not None:
                user.avatar_url = avatar_url
                user_profile_changed = True

            employee_profile_changed = False
            if employee:
                for field_name, value in employee_fields.items():
                    if value is not None:
                        setattr(employee, field_name, value)
                        employee_profile_changed = True

            skills_to_embed = []
            if skills_provided:
                if skills is None:
                    raise ValueError("skills must be a list when provided")

                normalized_skill_names = UserService._normalize_skill_names(skills or [])
                desired_skills, created_skill_keys = await UserService._get_or_create_skills(
                    db,
                    normalized_skill_names,
                )

                current_skill_ids = {
                    employee_skill.skill_id
                    for employee_skill in employee.employee_skills
                }
                desired_skill_ids = {skill.id for skill in desired_skills}
                skills_changed = current_skill_ids != desired_skill_ids

                if skills_changed:
                    skill_ids_to_remove = current_skill_ids - desired_skill_ids
                    if skill_ids_to_remove:
                        await db.execute(
                            delete(EmployeeSkill).where(
                                EmployeeSkill.employee_id == employee.id,
                                EmployeeSkill.skill_id.in_(skill_ids_to_remove),
                            )
                        )

                    skill_ids_to_add = desired_skill_ids - current_skill_ids
                    for skill_id in skill_ids_to_add:
                        db.add(
                            EmployeeSkill(
                                employee_id=employee.id,
                                skill_id=skill_id,
                            )
                        )

                response_skills = desired_skills
                skills_to_embed = [
                    skill.name
                    for skill in desired_skills
                    if skill.name.lower() in created_skill_keys
                    or skill.embedding_status != "done"
                ]

            if user_profile_changed or employee_profile_changed or skills_changed:
                user.updated_at = datetime.utcnow()

            profile_embedding_should_update = (
                employee is not None
                and (employee_profile_changed or skills_changed)
            )
            if (skills_to_embed or profile_embedding_should_update) and embedding_service is None:
                raise RuntimeError("embedding service is not ready")

            await db.flush()

            if skills_to_embed:
                if embedding_service is None:
                    raise RuntimeError("skill embedding service is not ready")

                embedded_skill_count = await embedding_service.embed_skills(
                    db,
                    skills_to_embed,
                )

            if profile_embedding_should_update:
                profile = await embedding_service.get_user_profile(db, user_id)
                profile_vector_tfidf = await embedding_service.process_user_profile_tfidf(
                    profile
                )
                profile_vector = await embedding_service.process_user_profile_multimodal(
                    profile
                )
                profile_vector["tfidf_vec"] = profile_vector_tfidf
                await embedding_service.upsert_user_profile_embedding(
                    db,
                    employee.id,
                    profile_vector,
                )
                profile_embedding_updated = True

            await db.commit()

        except IntegrityError as exc:
            await db.rollback()
            raise ValueError(f"Failed to update user profile: {exc}") from exc
        except Exception:
            await db.rollback()
            raise

        return UserService._serialize_updated_profile(
            user=user,
            employee=employee,
            skills=response_skills,
            skills_changed=skills_changed,
            embedded_skill_count=embedded_skill_count,
            profile_embedding_updated=profile_embedding_updated,
        )

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
