"""
Réponses d'un étudiant, soumission (correction + score), résultats et historique.

La correction se fait TOUJOURS ici, côté serveur : le client n'envoie que ses réponses,
jamais un score ni une correction.
"""

from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.models import PlacementTest, SkillResult, TestQuestion, TestStatus
from app.models.user import utcnow
from app.schemas.placement import SubmitAnswer
from app.services.placement import PlacementError, get_test_for_user
from app.services.scoring import SCORING_VERSION, QuestionOutcome, compute_result, grade_answer


class PlacementNotFoundError(PlacementError):
    pass


class QuestionNotFoundError(PlacementError):
    pass


class InvalidAnswerError(PlacementError):
    pass


class AlreadyCompletedError(PlacementError):
    pass


class NotCompletedError(PlacementError):
    pass


def _check_answer(question: TestQuestion, answer: str) -> None:
    if answer not in question.options:
        raise InvalidAnswerError("Réponse invalide : elle ne correspond à aucune option de la question.")


def _owned_in_progress_test(db: Session, test_id: int, user_id: int) -> PlacementTest:
    test = get_test_for_user(db, test_id, user_id)
    if test is None:
        raise PlacementNotFoundError("Test introuvable.")
    if test.status != TestStatus.IN_PROGRESS:
        raise AlreadyCompletedError("Ce test est déjà terminé.")
    return test


def save_answer(db: Session, test_id: int, user_id: int, question_id: int, answer: str) -> None:
    """Enregistre (ou remplace) la réponse à une question, pour pouvoir reprendre le test plus tard."""
    test = _owned_in_progress_test(db, test_id, user_id)
    question = next((q for q in test.questions if q.id == question_id), None)
    if question is None:
        raise QuestionNotFoundError("Question introuvable dans ce test.")
    _check_answer(question, answer)

    question.user_answer = answer
    question.answered_at = utcnow()
    db.commit()


def submit_test(db: Session, test_id: int, user_id: int, answers: list[SubmitAnswer]) -> PlacementTest:
    """
    Corrige le test, calcule et enregistre le score, le niveau et les résultats par compétence.

    - Les réponses du corps remplacent celles déjà enregistrées ; une réponse None efface la réponse ;
      une question absente du corps garde sa réponse enregistrée.
    - Tout est validé AVANT de modifier quoi que ce soit : une réponse invalide ne change rien.
    """
    test = _owned_in_progress_test(db, test_id, user_id)
    by_id = {q.id: q for q in test.questions}

    for item in answers:
        question = by_id.get(item.question_id)
        if question is None:
            raise InvalidAnswerError(f"Question inconnue dans ce test : {item.question_id}.")
        if item.answer is not None:
            _check_answer(question, item.answer)

    # Passage atomique « en cours » → « terminé » : si une autre requête a déjà terminé ce test
    # (double clic, deux onglets), 0 ligne est modifiée et on refuse, sans corriger deux fois.
    now = utcnow()
    claimed = db.execute(
        update(PlacementTest)
        .where(PlacementTest.id == test.id, PlacementTest.status == TestStatus.IN_PROGRESS)
        .values(status=TestStatus.COMPLETED, completed_at=now)
        .execution_options(synchronize_session=False)
    )
    if claimed.rowcount == 0:
        db.rollback()
        raise AlreadyCompletedError("Ce test est déjà terminé.")

    for item in answers:
        question = by_id[item.question_id]
        question.user_answer = item.answer
        question.answered_at = now if item.answer is not None else None

    outcomes = []
    for question in test.questions:
        question.is_correct = grade_answer(question.user_answer, question.correct_answer)
        outcomes.append(
            QuestionOutcome(
                skill_id=question.skill_id,
                difficulty=question.difficulty,
                answered=question.user_answer is not None,
                correct=question.is_correct,
            )
        )
    result = compute_result(outcomes)

    test.status = TestStatus.COMPLETED
    test.completed_at = now
    test.score = result.score
    test.level = result.level
    test.correct_count = result.correct_count
    test.unanswered_count = result.unanswered_count
    test.scoring_version = SCORING_VERSION
    test.skill_results = [
        SkillResult(
            skill_id=skill.skill_id,
            n_questions=skill.n_questions,
            n_correct=skill.n_correct,
            n_unanswered=skill.n_unanswered,
            score=skill.score,
            mastery=skill.mastery,
        )
        for skill in result.skills
    ]
    db.commit()
    return test


def get_result(db: Session, test_id: int, user_id: int) -> PlacementTest:
    """Test terminé d'un étudiant avec tout ce qu'il faut pour afficher le résultat et la correction."""
    test = db.scalar(
        select(PlacementTest)
        .options(
            selectinload(PlacementTest.course),
            selectinload(PlacementTest.questions).selectinload(TestQuestion.bank_question),
            selectinload(PlacementTest.skill_results).selectinload(SkillResult.skill),
        )
        .where(PlacementTest.id == test_id, PlacementTest.user_id == user_id)
    )
    if test is None:
        raise PlacementNotFoundError("Test introuvable.")
    if test.status != TestStatus.COMPLETED:
        raise NotCompletedError("Ce test n'est pas encore terminé : les résultats ne sont pas disponibles.")
    return test


def list_history(db: Session, user_id: int, course_id: int | None = None) -> list[PlacementTest]:
    """Tests de l'étudiant (du plus récent au plus ancien), éventuellement pour un seul cours."""
    query = (
        select(PlacementTest)
        .options(selectinload(PlacementTest.course))
        .where(PlacementTest.user_id == user_id)
        .order_by(PlacementTest.started_at.desc(), PlacementTest.id.desc())
    )
    if course_id is not None:
        query = query.where(PlacementTest.course_id == course_id)
    return list(db.scalars(query).all())