import bcrypt


def hash_password(password: str) -> str:
    """Hache le mot de passe avec bcrypt (sel aléatoire inclus dans le hash)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Utilisé en T5 (connexion)."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))