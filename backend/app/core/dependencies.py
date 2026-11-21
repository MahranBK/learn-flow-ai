from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.database import get_db
from app.models import User

# auto_error=False : on gère nous-mêmes l'erreur pour renvoyer un message en français
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session invalide ou expirée. Veuillez vous reconnecter.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    payload = decode_access_token(credentials.credentials)  # signature + expiration
    if payload is None:
        raise unauthorized

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise unauthorized

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user

def require_role(*allowed_roles: str):
    """
    Dépendance qui autorise seulement certains rôles.
    Exemple : @router.get("/admin/users", dependencies=[Depends(require_role("admin"))])
    """

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès refusé : vous n'avez pas les droits nécessaires.",
            )
        return current_user

    return role_checker