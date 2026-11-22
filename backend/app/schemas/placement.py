from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.placement import MasteryLevel, PlacementLevel, TestStatus
from app.schemas.base import ORMModel
from app.schemas.course import CourseOut, SkillOut

# ---------------------------------------------------------------------------
# Passage du test
#  Aucun schéma de cette section ne contient `correct_answer` ni `difficulty` :
#    ils ne doivent jamais quitter le serveur avant la soumission.
# ---------------------------------------------------------------------------


class PlacementStartRequest(BaseModel):
    """POST /placement-tests"""

    course_id: int


class TestQuestionPublic(ORMModel):
    """Question telle que l'étudiant la voit pendant le test."""

    id: int
    position: int
    skill: SkillOut
    question: str
    options: list[str]


class SavedAnswer(BaseModel):
    question_id: int
    answer: str


class PlacementTestOut(BaseModel):
    """POST /placement-tests et GET /placement-tests/{id} : le test (avec reprise)."""

    id: int
    status: TestStatus
    course: CourseOut
    total_questions: int
    started_at: datetime
    questions: list[TestQuestionPublic]
    answers: list[SavedAnswer] = []  # réponses déjà enregistrées (reprise)


class AnswerIn(BaseModel):
    """PUT /placement-tests/{id}/answers/{question_id}"""

    answer: str = Field(min_length=1, max_length=255)


class SubmitAnswer(BaseModel):
    question_id: int
    answer: str | None = Field(default=None, max_length=255)  # None = non répondue


class SubmitRequest(BaseModel):
    """POST /placement-tests/{id}/submit"""

    answers: list[SubmitAnswer]

    @field_validator("answers")
    @classmethod
    def no_duplicate_question(cls, answers: list[SubmitAnswer]) -> list[SubmitAnswer]:
        ids = [a.question_id for a in answers]
        if len(ids) != len(set(ids)):
            raise ValueError("Une question ne peut être répondue qu'une seule fois.")
        return answers


# ---------------------------------------------------------------------------
# Résultats (disponibles seulement après la soumission)
# ---------------------------------------------------------------------------


class SubmitResponse(BaseModel):
    id: int
    score: float
    level: PlacementLevel
    correct_count: int
    total_questions: int
    unanswered_count: int
    completed_at: datetime


class SkillResultOut(ORMModel):
    skill: SkillOut
    score: float
    n_questions: int
    n_correct: int
    n_unanswered: int
    mastery: MasteryLevel


class QuestionReview(BaseModel):
    """Correction d'une question (après la soumission uniquement)."""

    question: str
    options: list[str]
    your_answer: str | None
    correct_answer: str
    is_correct: bool
    explanation: str | None = None


class PlacementResultOut(BaseModel):
    """GET /placement-tests/{id}/result"""

    id: int
    course: CourseOut
    score: float
    level: PlacementLevel
    reliable: bool  # False si plus de la moitié des questions sont sans réponse
    correct_count: int
    total_questions: int
    unanswered_count: int
    completed_at: datetime
    skills: list[SkillResultOut]
    review: list[QuestionReview]


class PlacementHistoryItem(BaseModel):
    """GET /placement-tests?course_id=… (historique de l'étudiant connecté)"""

    id: int
    course: CourseOut
    attempt_number: int
    status: TestStatus
    score: float | None
    level: PlacementLevel | None
    started_at: datetime
    completed_at: datetime | None