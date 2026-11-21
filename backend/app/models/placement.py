import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.user import utcnow

if TYPE_CHECKING:
    from app.models.user import User


class TestStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class PlacementTest(Base):
    """Test de positionnement passé par un étudiant (US3)."""

    __tablename__ = "placement_tests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[TestStatus] = mapped_column(
        Enum(TestStatus, name="test_status"), default=TestStatus.PENDING
    )
    score: Mapped[float | None] = mapped_column(Float)  # en %
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="tests")
    questions: Mapped[list["TestQuestion"]] = relationship(
        back_populates="test", cascade="all, delete-orphan"
    )


class TestQuestion(Base):
    """Question d'un test (générée par le LLM) et réponse de l'étudiant."""

    __tablename__ = "test_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    test_id: Mapped[int] = mapped_column(
        ForeignKey("placement_tests.id", ondelete="CASCADE"), index=True
    )
    skill: Mapped[str] = mapped_column(String(100))  # compétence évaluée
    question: Mapped[str] = mapped_column(Text)
    options: Mapped[list[str]] = mapped_column(JSON, default=list)
    correct_answer: Mapped[str] = mapped_column(String(255))
    user_answer: Mapped[str | None] = mapped_column(String(255))
    is_correct: Mapped[bool | None] = mapped_column(Boolean)

    test: Mapped["PlacementTest"] = relationship(back_populates="questions")