from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.db.database import get_db
from app.models import PlacementTest, User
from app.schemas.course import CourseOut
from app.schemas.placement import (
    AnswerIn,
    PlacementHistoryItem,
    PlacementResultOut,
    PlacementStartRequest,
    PlacementTestOut,
    QuestionReview,
    SavedAnswer,
    SkillResultOut,
    SubmitRequest,
    SubmitResponse,
    TestQuestionPublic,
)
from app.services import placement as placement_service
from app.services import submission as submission_service
from app.services.scoring import is_reliable

router = APIRouter(prefix="/placement-tests", tags=["Test de positionnement"])


def to_test_out(test: PlacementTest) -> PlacementTestOut:
    """Convertit un test en réponse API. Les schémas ne contiennent jamais la bonne réponse."""
    return PlacementTestOut(
        id=test.id,
        status=test.status,
        course=CourseOut.model_validate(test.course),
        total_questions=test.total_questions,
        started_at=test.started_at,
        questions=[TestQuestionPublic.model_validate(q) for q in test.questions],
        answers=[
            SavedAnswer(question_id=q.id, answer=q.user_answer)
            for q in test.questions
            if q.user_answer is not None
        ],
    )


def to_result_out(test: PlacementTest) -> PlacementResultOut:
    """Résultat complet : n'est construit que pour un test terminé (la correction est alors visible)."""
    return PlacementResultOut(
        id=test.id,
        course=CourseOut.model_validate(test.course),
        score=test.score,
        level=test.level,
        reliable=is_reliable(test.unanswered_count, test.total_questions),
        correct_count=test.correct_count,
        total_questions=test.total_questions,
        unanswered_count=test.unanswered_count,
        completed_at=test.completed_at,
        skills=[
            SkillResultOut.model_validate(result)
            for result in sorted(test.skill_results, key=lambda r: r.skill_id)
        ],
        review=[
            QuestionReview(
                question=q.question,
                options=q.options,
                your_answer=q.user_answer,
                correct_answer=q.correct_answer,
                is_correct=bool(q.is_correct),
                explanation=q.bank_question.explanation if q.bank_question else None,
            )
            for q in test.questions
        ],
    )


def _http_error(exc: Exception) -> HTTPException:
    """Traduit une erreur métier en réponse HTTP (messages en français)."""
    if isinstance(exc, (placement_service.CourseNotFoundError, submission_service.PlacementNotFoundError)):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    if isinstance(exc, submission_service.QuestionNotFoundError):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    if isinstance(exc, submission_service.InvalidAnswerError):
        return HTTPException(422, str(exc))
    if isinstance(exc, (submission_service.AlreadyCompletedError, submission_service.NotCompletedError)):
        return HTTPException(status.HTTP_409_CONFLICT, str(exc))
    if isinstance(exc, placement_service.RetakeNotAllowedError):
        return HTTPException(
            status.HTTP_409_CONFLICT,
            f"Vous pourrez repasser ce test à partir du {exc.available_at:%d/%m/%Y}.",
        )
    if isinstance(exc, placement_service.NotEnoughQuestionsError):
        return HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Ce cours n'est pas encore disponible : la banque de questions est insuffisante.",
        )
    raise exc


@router.post("", response_model=PlacementTestOut)
def start_test(
    payload: PlacementStartRequest,
    response: Response,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    """Démarre un test sur un cours, ou renvoie le test déjà en cours (reprise)."""
    try:
        test, created = placement_service.start_or_resume(db, current_user.id, payload.course_id)
    except placement_service.PlacementError as exc:
        raise _http_error(exc)

    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return to_test_out(test)


@router.get("", response_model=list[PlacementHistoryItem])
def list_my_tests(
    course_id: int | None = None,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    """Historique des tests de l'étudiant connecté (jamais ceux des autres)."""
    return [
        PlacementHistoryItem(
            id=test.id,
            course=CourseOut.model_validate(test.course),
            attempt_number=test.attempt_number,
            status=test.status,
            score=test.score,
            level=test.level,
            started_at=test.started_at,
            completed_at=test.completed_at,
        )
        for test in submission_service.list_history(db, current_user.id, course_id)
    ]


@router.get("/{test_id}", response_model=PlacementTestOut)
def get_test(
    test_id: int,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    """Récupère un de SES tests (reprise). Le test d'un autre étudiant donne un 404."""
    test = placement_service.get_test_for_user(db, test_id, current_user.id)
    if test is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Test introuvable.")
    return to_test_out(test)


@router.put("/{test_id}/answers/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def save_answer(
    test_id: int,
    question_id: int,
    payload: AnswerIn,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    """Enregistre la réponse à une question (sauvegarde au fil de l'eau)."""
    try:
        submission_service.save_answer(db, test_id, current_user.id, question_id, payload.answer)
    except placement_service.PlacementError as exc:
        raise _http_error(exc)


@router.post("/{test_id}/submit", response_model=SubmitResponse)
def submit_test(
    test_id: int,
    payload: SubmitRequest,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    """Corrige le test côté serveur et enregistre le score. Un test terminé ne peut pas être renvoyé."""
    try:
        test = submission_service.submit_test(db, test_id, current_user.id, payload.answers)
    except placement_service.PlacementError as exc:
        raise _http_error(exc)

    return SubmitResponse(
        id=test.id,
        score=test.score,
        level=test.level,
        correct_count=test.correct_count,
        total_questions=test.total_questions,
        unanswered_count=test.unanswered_count,
        completed_at=test.completed_at,
    )


@router.get("/{test_id}/result", response_model=PlacementResultOut)
def get_result(
    test_id: int,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    """Résultat détaillé (score, niveau, compétences, correction) d'un de SES tests terminés."""
    try:
        return to_result_out(submission_service.get_result(db, test_id, current_user.id))
    except placement_service.PlacementError as exc:
        raise _http_error(exc)