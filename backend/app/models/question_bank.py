import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.db.types import enum_type
from app.models.user import utcnow

if TYPE_CHECKING:
    from app.models.course import Skill


class Difficulty(enum.IntEnum):
    """Niveau de difficulté d'une question (sert de pondération dans le score)."""

    EASY = 1
    MEDIUM = 2
    HARD = 3


class QuestionSource(str, enum.Enum):
    MANUAL = "manual"  # rédigée par l'équipe
    LLM = "llm"  # générée par le LLM


class ReviewStatus(str, enum.Enum):
    DRAFT = "draft"  # générée, pas encore relue : jamais utilisée dans un test
    APPROVED = "approved"  # validée : utilisable dans les tests
    RETIRED = "retired"  # retirée (erreur détectée, question trop facile/difficile…)


class BankQuestion(Base):
    """
    Question validée de la banque. Les tests sont construits à partir de cette table ;
    chaque test en garde une copie figée dans TestQuestion (snapshot).
    Une question approuvée n'est jamais modifiée : une correction crée une nouvelle version.
    """

    __tablename__ = "bank_questions"
    __table_args__ = (
        CheckConstraint("difficulty BETWEEN 1 AND 3", name="ck_bank_questions_difficulty"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    difficulty: Mapped[int] = mapped_column(Integer, default=Difficulty.MEDIUM)
    question: Mapped[str] = mapped_column(Text)
    options: Mapped[list[str]] = mapped_column(JSON, default=list)  # 4 propositions distinctes
    correct_answer: Mapped[str] = mapped_column(String(255))  # doit figurer dans options
    explanation: Mapped[str | None] = mapped_column(Text)  # montrée après la soumission
    source: Mapped[QuestionSource] = mapped_column(
        enum_type(QuestionSource), default=QuestionSource.MANUAL
    )
    review_status: Mapped[ReviewStatus] = mapped_column(
        enum_type(ReviewStatus), default=ReviewStatus.DRAFT, index=True
    )
    # SHA-256 du texte normalisé (question + options) : évite les doublons
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    skill: Mapped["Skill"] = relationship(back_populates="questions")