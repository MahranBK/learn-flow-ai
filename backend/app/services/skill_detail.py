"""Détail d'une compétence (US7) : lecture seule, d'après le dernier test terminé de l'étudiant."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Course,
    LearningPath,
    MasteryLevel,
    PathStatus,
    PathStep,
    PlacementTest,
    Skill,
    TestStatus,
    TestQuestion,
)
from app.schemas.course import CourseOut, SkillOut
from app.schemas.skill_detail import MissedQuestion, SkillDetailOut, SkillDetailStep
from app.services.learning_path import NoCompletedTestError
from app.services.placement import PlacementError


class SkillNotFoundError(PlacementError):
    """Compétence inexistante."""


def get_skill_detail(db: Session, user_id: int, skill_id: int) -> SkillDetailOut:
    skill = db.get(Skill, skill_id)
    course = db.scalar(
        select(Course).join(Course.skills).where(Skill.id == skill_id, Course.is_active.is_(True))
    )
    if skill is None or course is None:
        raise SkillNotFoundError("Compétence introuvable.")

    test = db.scalar(
        select(PlacementTest)
        .options(selectinload(PlacementTest.skill_results))
        .where(
            PlacementTest.user_id == user_id,
            PlacementTest.course_id == course.id,
            PlacementTest.status == TestStatus.COMPLETED,
        )
        .order_by(PlacementTest.completed_at.desc(), PlacementTest.id.desc())
        .limit(1)
    )
    if test is None:
        raise NoCompletedTestError("Passez d'abord le test de positionnement pour ce cours.")

    result = next((r for r in test.skill_results if r.skill_id == skill_id), None)

    questions = db.scalars(
        select(TestQuestion)
        .where(TestQuestion.test_id == test.id, TestQuestion.skill_id == skill_id)
        .order_by(TestQuestion.position)
    ).all()
    missed = [MissedQuestion.model_validate(q) for q in questions if q.user_answer is None or not q.is_correct]

    step = db.scalar(
        select(PathStep)
        .join(LearningPath, PathStep.path_id == LearningPath.id)
        .where(
            LearningPath.user_id == user_id,
            LearningPath.status == PathStatus.ACTIVE,
            PathStep.skill_id == skill_id,
        )
    )

    return SkillDetailOut(
        skill=SkillOut.model_validate(skill),
        course=CourseOut.model_validate(course),
        test_id=test.id,
        completed_at=test.completed_at,
        mastery=result.mastery if result else MasteryLevel.INSUFFICIENT_DATA,
        score=result.score if result else None,
        n_questions=result.n_questions if result else 0,
        n_correct=result.n_correct if result else 0,
        n_unanswered=result.n_unanswered if result else 0,
        missed_questions=missed,
        step=SkillDetailStep.model_validate(step) if step else None,
    )