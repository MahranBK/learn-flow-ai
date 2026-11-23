"""
Démarrage et lecture des tests de positionnement.

- pick_questions : sélection pure (sans base de données) des questions d'une compétence ;
- build_test     : assemble un test complet à partir de la banque et le fige (snapshot) ;
- start_or_resume: reprend le test en cours, sinon en crée un (en respectant le délai de repasse).
"""

import logging
import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Protocol, Sequence, TypeVar

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import PLACEMENT_RETAKE_COOLDOWN_DAYS
from app.models import (
    BankQuestion,
    Course,
    Difficulty,
    GenerationSource,
    PlacementTest,
    QuestionSource,
    ReviewStatus,
    Skill,
    TestQuestion,
    TestStatus,
)
from app.models.user import utcnow
from app.services.question_generation import Generator, top_up_bank
from app.services.scoring import MIN_QUESTIONS_PER_SKILL

logger = logging.getLogger(__name__)

# Composition d'un test : nombre de questions PAR COMPÉTENCE et par difficulté.
QUESTIONS_PER_DIFFICULTY: dict[int, int] = {
    Difficulty.EASY: 1,
    Difficulty.MEDIUM: 2,
    Difficulty.HARD: 1,
}

# En dessous de ce total, on refuse de démarrer plutôt que de proposer un test peu fiable.
MIN_TOTAL_QUESTIONS = 8


class PlacementError(Exception):
    """Erreur métier : le router la traduit en code HTTP."""


class CourseNotFoundError(PlacementError):
    pass


class NotEnoughQuestionsError(PlacementError):
    pass


class RetakeNotAllowedError(PlacementError):
    def __init__(self, available_at: datetime) -> None:
        super().__init__("Nouvelle tentative pas encore autorisée.")
        self.available_at = available_at


class _HasDifficulty(Protocol):
    id: int
    difficulty: int


T = TypeVar("T", bound=_HasDifficulty)


def pick_questions(
    candidates: Sequence[T],
    blueprint: dict[int, int],
    seen_ids: set[int],
    rng: random.Random,
) -> list[T]:
    """
    Choisit des questions au hasard selon le plan du test (blueprint : difficulté → nombre).

    Ordre de préférence pour chaque place à remplir :
      1. question jamais vue par l'étudiant, de la bonne difficulté ;
      2. question jamais vue, de la difficulté la plus proche ;
      3. question déjà vue (seulement si la banque est épuisée), mêmes règles.
    Peut renvoyer moins de questions que prévu si la banque est trop petite.
    """
    open_slots = [difficulty for difficulty, count in sorted(blueprint.items()) for _ in range(count)]
    picked: list[T] = []
    taken: set[int] = set()

    for seen_tier in (False, True):
        if not open_slots:
            break
        pool = [q for q in candidates if (q.id in seen_ids) == seen_tier]
        rng.shuffle(pool)  # le hasard départage les ex æquo

        unmatched = []
        for difficulty in open_slots:  # 1re passe : difficulté exacte
            match = next((q for q in pool if q.difficulty == difficulty and q.id not in taken), None)
            if match is None:
                unmatched.append(difficulty)
            else:
                picked.append(match)
                taken.add(match.id)

        open_slots = []
        for difficulty in unmatched:  # 2e passe : difficulté la plus proche
            nearest = min(
                (q for q in pool if q.id not in taken),
                key=lambda q: abs(q.difficulty - difficulty),
                default=None,
            )
            if nearest is None:
                open_slots.append(difficulty)
            else:
                picked.append(nearest)
                taken.add(nearest.id)

    return picked


def _as_utc(value: datetime) -> datetime:
    """SQLite renvoie des dates sans fuseau ; PostgreSQL avec. On uniformise."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def build_test(db: Session, user_id: int, course: Course, rng: random.Random) -> PlacementTest:
    """Assemble un nouveau test (non enregistré) à partir des questions approuvées de la banque."""
    skill_ids = [skill.id for skill in course.skills]
    approved = db.scalars(
        select(BankQuestion).where(
            BankQuestion.skill_id.in_(skill_ids),
            BankQuestion.review_status == ReviewStatus.APPROVED,
        )
    ).all()
    by_skill: dict[int, list[BankQuestion]] = defaultdict(list)
    for question in approved:
        by_skill[question.skill_id].append(question)

    # Questions déjà posées à cet étudiant sur ce cours (pour varier d'une tentative à l'autre)
    seen_ids = set(
        db.scalars(
            select(TestQuestion.bank_question_id)
            .join(PlacementTest, TestQuestion.test_id == PlacementTest.id)
            .where(
                PlacementTest.user_id == user_id,
                PlacementTest.course_id == course.id,
                TestQuestion.bank_question_id.is_not(None),
            )
        ).all()
    )

    selected: list[tuple[Skill, BankQuestion]] = []
    for skill in course.skills:
        picked = pick_questions(by_skill[skill.id], QUESTIONS_PER_DIFFICULTY, seen_ids, rng)
        if len(picked) < MIN_QUESTIONS_PER_SKILL:
            logger.warning("Compétence « %s » ignorée : seulement %d question(s).", skill.code, len(picked))
            continue
        selected.extend((skill, question) for question in picked)

    if len(selected) < MIN_TOTAL_QUESTIONS:
        raise NotEnoughQuestionsError("Banque de questions insuffisante pour ce cours.")

    rng.shuffle(selected)  # les compétences sont mélangées dans le test
    llm_count = sum(question.source == QuestionSource.LLM for _, question in selected)
    if llm_count == 0:
        source = GenerationSource.BANK
    elif llm_count == len(selected):
        source = GenerationSource.LLM
    else:
        source = GenerationSource.MIXED
    last_attempt = db.scalar(
        select(func.max(PlacementTest.attempt_number)).where(
            PlacementTest.user_id == user_id, PlacementTest.course_id == course.id
        )
    )
    test = PlacementTest(
        user_id=user_id,
        course=course,
        attempt_number=(last_attempt or 0) + 1,
        status=TestStatus.IN_PROGRESS,
        total_questions=len(selected),
        generation_source=source,
    )
    test.questions = [
        TestQuestion(
            skill=skill,
            bank_question_id=question.id,
            position=position,
            difficulty=question.difficulty,
            question=question.question,
            options=rng.sample(question.options, len(question.options)),  # ordre mélangé
            correct_answer=question.correct_answer,
        )
        for position, (skill, question) in enumerate(selected, start=1)
    ]
    return test


def _load_options():
    return (
        selectinload(PlacementTest.questions).selectinload(TestQuestion.skill),
        selectinload(PlacementTest.course),
    )


def _find_active(db: Session, user_id: int, course_id: int) -> PlacementTest | None:
    return db.scalar(
        select(PlacementTest)
        .options(*_load_options())
        .where(
            PlacementTest.user_id == user_id,
            PlacementTest.course_id == course_id,
            PlacementTest.status == TestStatus.IN_PROGRESS,
        )
    )


def _check_retake_allowed(db: Session, user_id: int, course_id: int) -> None:
    if PLACEMENT_RETAKE_COOLDOWN_DAYS <= 0:
        return
    last_completed_at = db.scalar(
        select(func.max(PlacementTest.completed_at)).where(
            PlacementTest.user_id == user_id,
            PlacementTest.course_id == course_id,
            PlacementTest.status == TestStatus.COMPLETED,
        )
    )
    if last_completed_at is None:
        return
    available_at = _as_utc(last_completed_at) + timedelta(days=PLACEMENT_RETAKE_COOLDOWN_DAYS)
    if utcnow() < available_at:
        raise RetakeNotAllowedError(available_at)


def start_or_resume(
    db: Session,
    user_id: int,
    course_id: int,
    rng: random.Random | None = None,
    generate: Generator | None = None,
) -> tuple[PlacementTest, bool]:
    """
    Renvoie (test, créé) : le test en cours s'il existe (créé=False), sinon un nouveau test.
    Si `generate` est fourni (LLM), la banque du cours est d'abord complétée si elle est incomplète.
    Lève CourseNotFoundError, RetakeNotAllowedError ou NotEnoughQuestionsError.
    """
    course = db.scalar(
        select(Course)
        .options(selectinload(Course.skills))
        .where(Course.id == course_id, Course.is_active.is_(True))
    )
    if course is None:
        raise CourseNotFoundError("Cours introuvable.")

    active = _find_active(db, user_id, course.id)
    if active is not None:
        return active, False

    _check_retake_allowed(db, user_id, course.id)
    if generate is not None:
        top_up_bank(db, course, generate)

    test = build_test(db, user_id, course, rng or random.Random())
    db.add(test)
    try:
        db.commit()
    except IntegrityError:
        # Deux demandes simultanées : l'index unique a bloqué la seconde → on renvoie le test créé.
        db.rollback()
        active = _find_active(db, user_id, course.id)
        if active is None:
            raise
        return active, False
    return test, True


def get_test_for_user(db: Session, test_id: int, user_id: int) -> PlacementTest | None:
    """Test d'un étudiant, ou None s'il n'existe pas OU appartient à quelqu'un d'autre."""
    return db.scalar(
        select(PlacementTest)
        .options(*_load_options())
        .where(PlacementTest.id == test_id, PlacementTest.user_id == user_id)
    )