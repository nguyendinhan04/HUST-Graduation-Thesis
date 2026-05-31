from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    full_name = Column(String(255))
    phone = Column(String(50))
    role = Column(String(20), nullable=False)
    avatar_url = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    employer = relationship("Employer", back_populates="user", uselist=False)
    employee = relationship("Employee", back_populates="user", uselist=False)


class Company(Base):
    __tablename__ = "companies"

    id = Column(BigInteger, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    website = Column(String(255))
    logo_url = Column(Text)
    industry = Column(String(255))
    company_size = Column(String(100))
    address = Column(Text)
    location = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())

    employers = relationship("Employer", back_populates="company")
    jobs = relationship("Job", back_populates="company")


class Employer(Base):
    __tablename__ = "employers"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, unique=True)
    company_id = Column(BigInteger, ForeignKey("companies.id"), nullable=False)
    position = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="employer")
    company = relationship("Company", back_populates="employers")
    jobs = relationship("Job", back_populates="employer")


class Employee(Base):
    __tablename__ = "employees"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, unique=True)
    headline = Column(String(255))
    summary = Column(Text)
    years_of_experience = Column(Integer)
    current_location = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="employee")
    educations = relationship("Education", back_populates="employee")
    experiences = relationship("Experience", back_populates="employee")
    applications = relationship("Application", back_populates="employee")
    employee_skills = relationship("EmployeeSkill", back_populates="employee")

class Skill(Base):
    __tablename__ = "skills"

    id = Column(BigInteger, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    embedding_status = Column(String(20), nullable=False, server_default="pending")
    created_at = Column(DateTime, server_default=func.now())

    employee_skills = relationship("EmployeeSkill", back_populates="skill")
    job_skills = relationship("JobSkill", back_populates="skill")
    education_skills = relationship("EducationSkill", back_populates="skill")
    experience_skills = relationship("ExperienceSkill", back_populates="skill")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(BigInteger, primary_key=True)
    employer_id = Column(BigInteger, ForeignKey("employers.id"), nullable=False)
    company_id = Column(BigInteger, ForeignKey("companies.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    requirement = Column(Text)
    benefit = Column(Text)
    salary_min = Column(Numeric(12, 2))
    salary_max = Column(Numeric(12, 2))
    salary_currency = Column(String(10))
    experience_required = Column(Integer)
    employment_type = Column(String(50))
    working_time = Column(String(100))
    location_type = Column(String(255))
    address = Column(Text)
    deadline = Column(DateTime)
    status = Column(String(20), server_default="open")
    created_at = Column(DateTime, server_default=func.now())

    employer = relationship("Employer", back_populates="jobs")
    company = relationship("Company", back_populates="jobs")
    applications = relationship("Application", back_populates="job")
    job_skills = relationship("JobSkill", back_populates="job")


class EmployeeSkill(Base):
    __tablename__ = "employee_skills"

    employee_id = Column(BigInteger, ForeignKey("employees.id"), primary_key=True)
    skill_id = Column(BigInteger, ForeignKey("skills.id"), primary_key=True)

    employee = relationship("Employee", back_populates="employee_skills")
    skill = relationship("Skill", back_populates="employee_skills")

class JobSkill(Base):
    __tablename__ = "job_skills"

    job_id = Column(BigInteger, ForeignKey("jobs.id"), primary_key=True)
    skill_id = Column(BigInteger, ForeignKey("skills.id"), primary_key=True)
    is_required = Column(Boolean, server_default="true")

    job = relationship("Job", back_populates="job_skills")
    skill = relationship("Skill", back_populates="job_skills")


class Education(Base):
    __tablename__ = "educations"

    id = Column(BigInteger, primary_key=True)
    employee_id = Column(BigInteger, ForeignKey("employees.id"), nullable=False)
    school = Column(String(255))
    degree = Column(String(255))
    field_of_study = Column(String(255))
    description = Column(Text)
    start_date = Column(Date)
    end_date = Column(Date)

    employee = relationship("Employee", back_populates="educations")
    education_skills = relationship("EducationSkill", back_populates="education")


class EducationSkill(Base):
    __tablename__ = "education_skills"

    education_id = Column(BigInteger, ForeignKey("educations.id"), primary_key=True)
    skill_id = Column(BigInteger, ForeignKey("skills.id"), primary_key=True)

    education = relationship("Education", back_populates="education_skills")
    skill = relationship("Skill", back_populates="education_skills")


class Experience(Base):
    __tablename__ = "experiences"

    id = Column(BigInteger, primary_key=True)
    employee_id = Column(BigInteger, ForeignKey("employees.id"), nullable=False)
    title = Column(String(255))
    company_name = Column(String(255))
    employment_type = Column(String(100))
    location = Column(String(255))
    location_type = Column(String(100))
    description = Column(Text)
    start_date = Column(Date)
    end_date = Column(Date)

    employee = relationship("Employee", back_populates="experiences")
    experience_skills = relationship("ExperienceSkill", back_populates="experience")


class ExperienceSkill(Base):
    __tablename__ = "experience_skills"

    experience_id = Column(BigInteger, ForeignKey("experiences.id"), primary_key=True)
    skill_id = Column(BigInteger, ForeignKey("skills.id"), primary_key=True)

    experience = relationship("Experience", back_populates="experience_skills")
    skill = relationship("Skill", back_populates="experience_skills")


class Application(Base):
    __tablename__ = "applications"

    id = Column(BigInteger, primary_key=True)
    employee_id = Column(BigInteger, ForeignKey("employees.id"), nullable=False)
    job_id = Column(BigInteger, ForeignKey("jobs.id"), nullable=False)
    status = Column(String(50), server_default="pending")
    resume_url = Column(Text)
    cover_letter = Column(Text)
    applied_at = Column(DateTime, server_default=func.now())

    employee = relationship("Employee", back_populates="applications")
    job = relationship("Job", back_populates="applications")


class TaskOutbox(Base):
    __tablename__ = "task_outbox"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_type = Column(String(100), nullable=False)
    aggregate_type = Column(String(100), nullable=False)
    aggregate_id = Column(BigInteger, nullable=False)
    queue_name = Column(String(255), nullable=False)
    rq_job_id = Column(String(255))
    status = Column(String(20), nullable=False, server_default="pending")
    payload = Column(JSON, nullable=False, server_default="{}")
    result = Column(JSON)
    error_message = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'done', 'failed')",
            name="ck_task_outbox_status",
        ),
    )
