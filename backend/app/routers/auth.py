from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.database import get_db
from app.models import Role, User
from app.schemas.user import RegisterResponse, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["Authentification"])

EMAIL_TAKEN = "Cet email est déjà utilisé."


def to_user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role.name,
        created_at=user.created_at,
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    # 1. Email déjà utilisé ?
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=EMAIL_TAKEN)

    # 2. Un nouvel inscrit est toujours "student"
    student_role = db.scalar(select(Role).where(Role.name == "student"))
    if student_role is None:
        raise HTTPException(status_code=500, detail="Rôle 'student' introuvable.")

    # 3. Création avec mot de passe haché
    user = User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=student_role,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # 2 inscriptions simultanées avec le même email
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=EMAIL_TAKEN)
    db.refresh(user)

    # 4. Message de confirmation
    return RegisterResponse(
        message="Inscription réussie ! Vous pouvez maintenant vous connecter.",
        user=to_user_out(user),
    )