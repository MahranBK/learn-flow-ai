import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.db.types import enum_type
from app.models.user import utcnow

if TYPE_CHECKING:
    from app.models.course import Course, Skill
    from app.models.question_bank import BankQuestion
    from app.models.user import User


class TestStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class PlacementLevel(str, enum.Enum):
    """Niveau initial déterminé à partir du score global."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class MasteryLevel(str, enum.Enum):
    """Maîtrise d'une compétence, déterminée à partir de son score."""

    GAP = "gap"  # lacune
    PARTIAL = "partial"
    MASTERED = "mastered"
    INSUFFICIENT_DATA = "insufficient_data"  # trop peu de questions pour conclure


class GenerationSource(str, enum.Enum):
    BANK = "bank"  # toutes les questions viennent de la banque
    LLM = "llm"  # toutes les questions ont été générées à la demande
    MIXED = "mixed"


class PlacementTest(Base):
    """Tentative de test de positionnement d'un étudiant sur un cours (US3)."""

    __tablename__ = "placement_tests"
    __table_args__ = (
        UniqueConstraint("user_id", "course_id", "attempt_number", name="uq_placement_attempt"),
        # Un seul test "en cours" par étudiant et par cours (reprise au lieu de doublon)
        Index(
            "uq_placement_one_active",
            "user_id",
            "course_id",
            unique=True,
            postgresql_where=text("status = 'in_progress'"),
            sqlite_where=text("status = 'in_progress'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # RESTRICT : on ne supprime pas un cours qui a un historique de tests
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="RESTRICT"), index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[TestStatus] = mapped_column(enum_type(TestStatus), default=TestStatus.PENDING)

    # Résultat global (renseigné à la soumission)
    score: Mapped[float | None] = mapped_column(Float)  # en % (0-100)
    level: Mapped[PlacementLevel | None] = mapped_column(enum_type(PlacementLevel))
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    correct_count: Mapped[int | None] = mapped_column(Integer)
    unanswered_count: Mapped[int | None] = mapped_column(Integer)
    scoring_version: Mapped[str | None] = mapped_column(String(20))  # version de l'algorithme
    generation_source: Mapped[GenerationSource] = mapped_column(
        enum_type(GenerationSource), default=GenerationSource.BANK
    )

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="tests")
    course: Mapped["Course"] = relationship()
    questions: Mapped[list["TestQuestion"]] = relationship(
        back_populates="test", cascade="all, delete-orphan", order_by="TestQuestion.position"
    )
    skill_results: Mapped[list["SkillResult"]] = relationship(
        back_populates="test", cascade="all, delete-orphan"
    )


class TestQuestion(Base):
    """
    Question d'un test : copie figée (snapshot) de la question de la banque
    + réponse de l'étudiant. Les résultats passés restent corrects même si la banque évolue.
    """

    __tablename__ = "test_questions"
    __table_args__ = (UniqueConstraint("test_id", "position", name="uq_test_question_position"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    test_id: Mapped[int] = mapped_column(
        ForeignKey("placement_tests.id", ondelete="CASCADE"), index=True
    )
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="RESTRICT"), index=True)
    # Question d'origine (conservée pour les statistiques) ; NULL si elle est supprimée
    bank_question_id: Mapped[int | None] = mapped_column(
        ForeignKey("bank_questions.id", ondelete="SET NULL")
    )
    position: Mapped[int] = mapped_column(Integer)  # ordre d'affichage (1, 2, 3…)
    difficulty: Mapped[int] = mapped_column(Integer)  # 1 à 3, copiée de la banque

    question: Mapped[str] = mapped_column(Text)
    options: Mapped[list[str]] = mapped_column(JSON, default=list)  # ordre mélangé pour ce test
    correct_answer: Mapped[str] = mapped_column(String(255))  # ne JAMAIS envoyer avant la soumission

    user_answer: Mapped[str | None] = mapped_column(String(255))
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    test: Mapped["PlacementTest"] = relationship(back_populates="questions")
    skill: Mapped["Skill"] = relationship()
    bank_question: Mapped["BankQuestion | None"] = relationship()


class SkillResult(Base):
    """Résultat d'un test pour une compétence : c'est ce que lira l'agent de lacunes (US4)."""

    __tablename__ = "skill_results"
    __table_args__ = (UniqueConstraint("test_id", "skill_id", name="uq_skill_result_test_skill"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    test_id: Mapped[int] = mapped_column(
        ForeignKey("placement_tests.id", ondelete="CASCADE"), index=True
    )
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="RESTRICT"), index=True)
    n_questions: Mapped[int] = mapped_column(Integer)
    n_correct: Mapped[int] = mapped_column(Integer)
    n_unanswered: Mapped[int] = mapped_column(Integer, default=0)
    score: Mapped[float] = mapped_column(Float)  # en % (0-100), pondéré par la difficulté
    mastery: Mapped[MasteryLevel] = mapped_column(enum_type(MasteryLevel))

    test: Mapped["PlacementTest"] = relationship(back_populates="skill_results")
    skill: Mapped["Skill"] = relationship()