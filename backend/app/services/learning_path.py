"""
Parcours d'apprentissage personnalisé (US8).

Règles (déterministes, sans LLM) :
- on prend le DERNIER test terminé de l'étudiant pour chaque cours ;
- chaque compétence non maîtrisée (lacune, en progrès, non évaluée) devient une étape ;
- ordre : cours par id, puis ordre pédagogique du catalogue dans chaque cours ;
- un seul parcours actif par étudiant : l'ancien est archivé quand on reconstruit.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.models.user import utcnow

from app.models import (
    Course,
    LearningPath,
    MasteryLevel,
    PathStatus,
    PathStep,
    PlacementTest,
    StepStatus,
    TestStatus,
)
from app.services.placement import PlacementError


class NoCompletedTestError(PlacementError):
    """Aucun test terminé : impossible de construire un parcours."""


def build_objective(skill_name: str, course_title: str, mastery: MasteryLevel, score: float | None) -> str:
    """Texte « pourquoi cette étape », rédigé par règle."""
    if mastery == MasteryLevel.GAP:
        return f"Reprendre les bases de « {skill_name} » ({course_title}) : votre score de {round(score or 0)} % révèle une lacune."
    if mastery == MasteryLevel.PARTIAL:
        return f"Consolider « {skill_name} » ({course_title}) : vous avez {round(score or 0)} %, la compétence est en cours d'acquisition."
    return f"Évaluer « {skill_name} » ({course_title}) : le test n'a pas posé assez de questions pour conclure."


def get_active_path(db: Session, user_id: int) -> LearningPath | None:
    return db.scalar(
        select(LearningPath)
        .options(selectinload(LearningPath.steps).selectinload(PathStep.skill), selectinload(LearningPath.steps).selectinload(PathStep.course))
        .where(LearningPath.user_id == user_id, LearningPath.status == PathStatus.ACTIVE)
    )


def build_learning_path(db: Session, user_id: int) -> LearningPath:
    # Dernier test terminé de CET étudiant, pour chaque cours
    tests = db.scalars(
        select(PlacementTest)
        .options(selectinload(PlacementTest.skill_results))
        .where(PlacementTest.user_id == user_id, PlacementTest.status == TestStatus.COMPLETED)
        .order_by(PlacementTest.completed_at.desc(), PlacementTest.id.desc())
    ).all()
    latest: dict[int, PlacementTest] = {}
    for test in tests:
        latest.setdefault(test.course_id, test)  # le 1er rencontré est le plus récent
    if not latest:
        raise NoCompletedTestError("Passez d'abord un test de positionnement pour obtenir un parcours.")

    courses = db.scalars(
        select(Course)
        .options(selectinload(Course.skills))
        .where(Course.id.in_(latest.keys()), Course.is_active.is_(True))
        .order_by(Course.id)
    ).all()

    # On archive l'ancien parcours AVANT d'insérer le nouveau (index unique « un seul actif »)
    for old in db.scalars(
        select(LearningPath).where(LearningPath.user_id == user_id, LearningPath.status == PathStatus.ACTIVE)
    ):
        old.status = PathStatus.ARCHIVED
    db.flush()

    path = LearningPath(user_id=user_id)
    position = 0
    for course in courses:
        test = latest[course.id]
        results = {r.skill_id: r for r in test.skill_results}
        for skill in course.skills:  # ordre du catalogue
            result = results.get(skill.id)
            mastery = result.mastery if result else MasteryLevel.INSUFFICIENT_DATA
            score = result.score if result else None
            if mastery == MasteryLevel.MASTERED:
                continue
            position += 1
            path.steps.append(
                PathStep(
                    course_id=course.id,
                    skill_id=skill.id,
                    test_id=test.id,
                    position=position,
                    mastery_at_creation=mastery,
                    score_at_creation=score,
                    objective=build_objective(skill.name, course.title, mastery, score),
                    status=StepStatus.TODO,
                )
            )

    db.add(path)
    db.commit()
    db.refresh(path)
    return path


class StepNotFoundError(PlacementError):
    """Étape inexistante, d'un autre étudiant, ou appartenant à un parcours archivé."""


def update_step_status(db: Session, user_id: int, step_id: int, status: StepStatus) -> LearningPath:
    # On ne peut modifier que les étapes du parcours ACTIF de CET étudiant
    step = db.scalar(
        select(PathStep)
        .join(LearningPath, PathStep.path_id == LearningPath.id)
        .where(
            PathStep.id == step_id,
            LearningPath.user_id == user_id,
            LearningPath.status == PathStatus.ACTIVE,
        )
    )
    if step is None:
        raise StepNotFoundError("Étape introuvable.")

    step.status = status
    step.completed_at = utcnow() if status == StepStatus.DONE else None
    db.commit()

    path = get_active_path(db, user_id)
    assert path is not None
    return path