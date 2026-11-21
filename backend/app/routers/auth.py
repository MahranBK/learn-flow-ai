from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from app.core.security import create_access_token, hash_password, verify_password
from app.db.database import get_db
from app.models import Role, User
from app.schemas.user import RegisterResponse, UserCreate, UserOut
from app.schemas.auth import LoginRequest, TokenResponse

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

INVALID_CREDENTIALS = "Email ou mot de passe incorrect."

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))

    # Même message que l'email existe ou non : on ne révèle pas quels emails sont inscrits
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=INVALID_CREDENTIALS,
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce compte est désactivé. Contactez un administrateur.",
        )

    token = create_access_token(user_id=user.id, role=user.role.name)
    return TokenResponse(
        access_token=token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=to_user_out(user),
    )

@router.get("/me", response_model=UserOut)
def read_me(current_user: User = Depends(get_current_user)):
    """Renvoie l'utilisateur connecté (à partir de son JWT)."""
    return to_user_out(current_user)