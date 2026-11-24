from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.user import utcnow

if TYPE_CHECKING:
    from app.models.domain import Domain
    from app.models.question_bank import BankQuestion


class Course(Base):
    """Cours / matière sur lequel porte un test de positionnement (ex. « Python », « SQL »)."""

    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    # RESTRICT : on ne supprime pas un domaine qui contient encore des cours
    domain_id: Mapped[int] = mapped_column(ForeignKey("domains.id", ondelete="RESTRICT"), index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # ex. "python-basics"
    title: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    domain: Mapped["Domain"] = relationship(back_populates="courses")
    skills: Mapped[list["Skill"]] = relationship(
        back_populates="course", cascade="all, delete-orphan", order_by="Skill.id"
    )


class Skill(Base):
    """
    Compétence évaluée dans un cours (ex. « Boucles », « Fonctions »).
    C'est l'unité d'analyse des lacunes (US4) : les scores sont calculés par compétence.
    """

    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("course_id", "code", name="uq_skills_course_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(String(50))  # ex. "loops", unique dans un cours
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(Text)

    course: Mapped["Course"] = relationship(back_populates="skills")
    questions: Mapped[list["BankQuestion"]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )