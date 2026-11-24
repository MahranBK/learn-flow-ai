from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models import Course, Domain, User, user_interests
from app.schemas.course import CourseListItem

router = APIRouter(prefix="/courses", tags=["Cours"])


@router.get("", response_model=list[CourseListItem])
def list_courses(
    mine: bool = Query(False, description="Ne garder que les cours des domaines choisis par l'étudiant."),
    domain_id: int | None = Query(None, description="Ne garder que les cours de ce domaine."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Catalogue des cours actifs sur lesquels on peut passer un test de positionnement,
    triés par domaine puis par titre.
    """
    query = (
        select(Course)
        .join(Course.domain)
        .options(selectinload(Course.domain), selectinload(Course.skills))
        .where(Course.is_active.is_(True), Domain.is_active.is_(True))
        .order_by(Domain.name, Course.title)
    )
    if domain_id is not None:
        query = query.where(Course.domain_id == domain_id)
    if mine:
        chosen = select(user_interests.c.domain_id).where(user_interests.c.user_id == current_user.id)
        query = query.where(Course.domain_id.in_(chosen))
    return db.scalars(query).all()
