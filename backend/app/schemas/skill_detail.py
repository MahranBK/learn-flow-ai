from datetime import datetime

from app.models.learning_path import StepStatus
from app.models.placement import MasteryLevel
from app.schemas.base import ORMModel
from app.schemas.course import CourseOut, SkillOut


class SkillDetailStep(ORMModel):
    """L'étape du parcours actif qui travaille cette compétence."""

    id: int
    position: int
    status: StepStatus

class MissedQuestion(ORMModel):
    """Une question de cette compétence que l'étudiant a ratée ou laissée sans réponse."""

    position: int
    difficulty: int  # 1 à 3
    question: str
    options: list[str]
    user_answer: str | None  # None : laissée sans réponse
    correct_answer: str  # le test est terminé : la correction peut être affichée

class SkillDetailOut(ORMModel):
    """GET /skills/{id}/detail : niveau de l'étudiant sur une compétence (US7)."""

    skill: SkillOut
    course: CourseOut
    test_id: int
    completed_at: datetime
    mastery: MasteryLevel
    score: float | None  # en % (0-100) ; None si non évaluée
    n_questions: int
    n_correct: int
    n_unanswered: int
    missed_questions: list[MissedQuestion]
    step: SkillDetailStep | None  # None : compétence maîtrisée ou parcours pas encore construit