from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_role
from app.db.database import get_db
from app.models import User
from app.schemas.domain import DomainOut, InterestsUpdate
from app.services import interests as interests_service

router = APIRouter(tags=["Domaines"])


@router.get("/domains", response_model=list[DomainOut])
def list_domains(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Tous les domaines proposés (pour l'écran « Choisissez vos centres d'intérêt »)."""
    return interests_service.list_active_domains(db)


@router.get("/me/interests", response_model=list[DomainOut])
def get_my_interests(current_user: User = Depends(require_role("student"))):
    """Domaines choisis par l'étudiant connecté (liste vide tant qu'il n'a rien choisi)."""
    return current_user.interests


@router.put("/me/interests", response_model=list[DomainOut])
def update_my_interests(
    payload: InterestsUpdate,
    current_user: User = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    """Remplace les domaines d'intérêt de l'étudiant connecté."""
    try:
        return interests_service.set_interests(db, current_user, payload.domain_ids)
    except interests_service.InvalidDomainsError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
