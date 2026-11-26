import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.db.types import enum_type
from app.models.placement import MasteryLevel
from app.models.user import utcnow

if TYPE_CHECKING:
    from app.models.course import Course, Skill


class PathStatus(str, enum.Enum):
    ACTIVE = "active"      # le parcours en cours (un seul par étudiant)
    ARCHIVED = "archived"  # remplacé par un parcours plus récent


class StepStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class LearningPath(Base):
    """Parcours global d'un étudiant : toutes les compétences à travailler, tous cours confondus (US8)."""

    __tablename__ = "learning_paths"
    __table_args__ = (
        Index(
            "uq_path_one_active",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[PathStatus] = mapped_column(enum_type(PathStatus), default=PathStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    steps: Mapped[list["PathStep"]] = relationship(
        back_populates="path", cascade="all, delete-orphan", order_by="PathStep.position"
    )


class PathStep(Base):
    """Une étape : travailler une compétence (US8), dont l'étudiant suit l'avancement (US9)."""

    __tablename__ = "path_steps"
    __table_args__ = (
        UniqueConstraint("path_id", "position", name="uq_step_position"),
        UniqueConstraint("path_id", "skill_id", name="uq_step_skill"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    path_id: Mapped[int] = mapped_column(ForeignKey("learning_paths.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="RESTRICT"), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="RESTRICT"), index=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("placement_tests.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer)  # 1, 2, 3… : ordre à suivre
    mastery_at_creation: Mapped[MasteryLevel] = mapped_column(enum_type(MasteryLevel))
    score_at_creation: Mapped[float | None] = mapped_column(Float)
    objective: Mapped[str] = mapped_column(Text)  # « pourquoi cette étape »
    status: Mapped[StepStatus] = mapped_column(enum_type(StepStatus), default=StepStatus.TODO)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    path: Mapped["LearningPath"] = relationship(back_populates="steps")
    course: Mapped["Course"] = relationship()
    skill: Mapped["Skill"] = relationship()