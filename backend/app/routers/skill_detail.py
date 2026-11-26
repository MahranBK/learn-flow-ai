from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_role
from app.db.database import get_db
from app.models import User
from app.schemas.skill_detail import SkillDetailOut
from app.services import skill_detail as service
from app.services.learning_path import NoCompletedTestError

router = APIRouter(prefix="/skills", tags=["Détail d'une compétence"])


@router.get("/{skill_id}/detail", response_model=SkillDetailOut)
def read_skill_detail(
    skill_id: int,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    """Niveau de l'étudiant connecté sur une compétence (US7). 404 : compétence inconnue. 409 : aucun test terminé."""
    try:
        return service.get_skill_detail(db, current_user.id, skill_id)
    except service.SkillNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    except NoCompletedTestError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))