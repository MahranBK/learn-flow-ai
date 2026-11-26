from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.db.database import get_db
from app.models import User
from app.schemas.learning_path import LearningPathOut, StepStatusUpdate
from app.services import learning_path as service

router = APIRouter(prefix="/learning-path", tags=["Parcours personnalisé"])


@router.get("", response_model=LearningPathOut)
def read_learning_path(
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    """Parcours actif de l'étudiant (US8/US9). 404 : aucun parcours construit pour l'instant."""
    path = service.get_active_path(db, current_user.id)
    if path is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aucun parcours pour l'instant.")
    return LearningPathOut.from_path(path)


@router.post("/rebuild", response_model=LearningPathOut, status_code=status.HTTP_201_CREATED)
def rebuild_learning_path(
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    """Construit (ou reconstruit) le parcours depuis les derniers tests terminés. 409 : aucun test terminé."""
    try:
        path = service.build_learning_path(db, current_user.id)
    except service.NoCompletedTestError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    return LearningPathOut.from_path(path)


@router.patch("/steps/{step_id}", response_model=LearningPathOut)
def update_step(
    step_id: int,
    body: StepStatusUpdate,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    """Change le statut d'une étape (US9) et renvoie le parcours mis à jour avec sa progression."""
    try:
        path = service.update_step_status(db, current_user.id, step_id, body.status)
    except service.StepNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    return LearningPathOut.from_path(path)