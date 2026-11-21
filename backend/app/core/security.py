import bcrypt
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES, JWT_ALGORITHM, JWT_SECRET_KEY


def hash_password(password: str) -> str:
    """Hache le mot de passe avec bcrypt (sel aléatoire inclus dans le hash)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Utilisé en T5 (connexion)."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def create_access_token(user_id: int, role: str) -> str:
    """Génère un JWT signé contenant l'id et le rôle de l'utilisateur."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),  # "subject" = l'utilisateur (doit être une chaîne)
        "role": role,
        "iat": now,  # date de création
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),  # expiration
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Vérifie la signature et l'expiration. Retourne le contenu ou None. (utilisé en T7)"""
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None