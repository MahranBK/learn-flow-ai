from datetime import datetime

from pydantic import BaseModel

from app.models.learning_path import StepStatus
from app.models.placement import MasteryLevel
from app.schemas.base import ORMModel
from app.schemas.course import CourseOut, SkillOut


class PathStepOut(ORMModel):
    id: int
    position: int
    course: CourseOut
    skill: SkillOut
    mastery_at_creation: MasteryLevel
    score_at_creation: float | None  # en % (0-100) ; None si non évaluée
    objective: str
    status: StepStatus
    completed_at: datetime | None


class PathProgress(BaseModel):
    total: int
    done: int
    in_progress: int
    todo: int
    percent: int  # 0-100 ; 100 si le parcours est vide (rien à travailler)


class LearningPathOut(BaseModel):
    id: int
    created_at: datetime
    progress: PathProgress
    steps: list[PathStepOut]

    @classmethod
    def from_path(cls, path) -> "LearningPathOut":
        steps = [PathStepOut.model_validate(step) for step in path.steps]
        total = len(steps)
        done = sum(1 for s in steps if s.status == StepStatus.DONE)
        in_progress = sum(1 for s in steps if s.status == StepStatus.IN_PROGRESS)
        return cls(
            id=path.id,
            created_at=path.created_at,
            progress=PathProgress(
                total=total,
                done=done,
                in_progress=in_progress,
                todo=total - done - in_progress,
                percent=round(100 * done / total) if total else 100,
            ),
            steps=steps,
        )


class StepStatusUpdate(BaseModel):
    status: StepStatus