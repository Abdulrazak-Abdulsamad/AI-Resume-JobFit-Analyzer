"""
SQLAlchemy ORM models for the AI Resume & Job Fit Analyzer.
Mirrors db/database-schema.sql exactly — if you change one, change both,
then regenerate the Alembic migration.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    resumes: Mapped[list["Resume"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[Optional[str]] = mapped_column(Text)
    file_type: Mapped[Optional[str]] = mapped_column(Text)  # pdf, docx, image
    parsing_status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    parsed_json: Mapped[Optional[dict]] = mapped_column(JSONB)  # A3 NLP extraction output
    embedding_id: Mapped[Optional[str]] = mapped_column(Text)  # set by D1/D2
    score: Mapped[Optional[float]] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "parsing_status IN ('pending','processing','done','failed')",
            name="ck_resumes_parsing_status",
        ),
        CheckConstraint("score IS NULL OR (score BETWEEN 0 AND 100)", name="ck_resumes_score_range"),
        Index("idx_resumes_user_id", "user_id"),
        Index("idx_resumes_parsing_status", "parsing_status"),
        Index("idx_resumes_embedding_id", "embedding_id"),
    )

    user: Mapped["User"] = relationship(back_populates="resumes")
    resume_skills: Mapped[list["ResumeSkill"]] = relationship(back_populates="resume", cascade="all, delete-orphan")
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="resume", cascade="all, delete-orphan")


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    category: Mapped[Optional[str]] = mapped_column(Text)  # technical, soft, tool

    resume_skills: Mapped[list["ResumeSkill"]] = relationship(back_populates="skill", cascade="all, delete-orphan")
    job_skills: Mapped[list["JobSkill"]] = relationship(back_populates="skill", cascade="all, delete-orphan")


class ResumeSkill(Base):
    __tablename__ = "resume_skills"

    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True)
    proficiency: Mapped[Optional[str]] = mapped_column(Text)  # beginner, intermediate, advanced

    __table_args__ = (
        CheckConstraint(
            "proficiency IS NULL OR proficiency IN ('beginner','intermediate','advanced')",
            name="ck_resume_skills_proficiency",
        ),
        Index("idx_resume_skills_skill_id", "skill_id"),
    )

    resume: Mapped["Resume"] = relationship(back_populates="resume_skills")
    skill: Mapped["Skill"] = relationship(back_populates="resume_skills")


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    company: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    embedding_id: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        Index("idx_job_descriptions_embedding_id", "embedding_id"),
    )

    job_skills: Mapped[list["JobSkill"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class JobSkill(Base):
    __tablename__ = "job_skills"

    job_id: Mapped[int] = mapped_column(ForeignKey("job_descriptions.id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True)
    importance: Mapped[str] = mapped_column(Text, nullable=False, server_default="required")

    __table_args__ = (
        CheckConstraint("importance IN ('required','preferred')", name="ck_job_skills_importance"),
        Index("idx_job_skills_skill_id", "skill_id"),
    )

    job: Mapped["JobDescription"] = relationship(back_populates="job_skills")
    skill: Mapped["Skill"] = relationship(back_populates="job_skills")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=False)
    fit_score: Mapped[Optional[float]] = mapped_column()
    skill_gaps: Mapped[Optional[list]] = mapped_column(JSONB)               # [{"skill": ..., "reason": ...}]
    course_recommendations: Mapped[Optional[list]] = mapped_column(JSONB)   # [{"skill": ..., "resource": ..., "url": ...}]
    llm_explanation: Mapped[Optional[str]] = mapped_column(Text)            # from D3 (RAG)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "fit_score IS NULL OR (fit_score BETWEEN 0 AND 100)", name="ck_recommendations_fit_score_range"
        ),
        Index("idx_recommendations_user_id", "user_id"),
        Index("idx_recommendations_resume_id", "resume_id"),
        Index("idx_recommendations_job_id", "job_id"),
    )

    user: Mapped["User"] = relationship(back_populates="recommendations")
    resume: Mapped["Resume"] = relationship(back_populates="recommendations")
    job: Mapped["JobDescription"] = relationship(back_populates="recommendations")
