from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models import Course, User
from app.schemas.course import CourseOut

router = APIRouter(prefix="/courses", tags=["Cours"])


@router.get("", response_model=list[CourseOut])
def list_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cours actifs sur lesquels on peut passer un test de positionnement."""
    return db.scalars(select(Course).where(Course.is_active.is_(True)).order_by(Course.title)).all()