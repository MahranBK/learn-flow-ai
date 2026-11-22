import os

# Doit être défini AVANT tout import de `app` : les tests n'utilisent jamais la vraie base.
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def db():
    """Session sur une base SQLite en mémoire, vide et neuve pour chaque test."""
    import app.models  # noqa: F401  (enregistre toutes les tables)
    from app.db.database import Base

    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture()
def seeded_db(db):
    """Base avec rôles, cours, compétences et banque de questions de secours."""
    from app.db.database import DEFAULT_ROLES
    from app.db.seed import seed_catalog, seed_question_bank
    from app.models import Role

    for name, description in DEFAULT_ROLES.items():
        db.add(Role(name=name, description=description))
    seed_catalog(db)
    seed_question_bank(db)
    db.commit()
    return db


@pytest.fixture()
def client(seeded_db):
    """Client HTTP de test branché sur la base de test (le vrai PostgreSQL n'est jamais touché)."""
    from fastapi.testclient import TestClient

    from app.db.database import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: seeded_db
    yield TestClient(app)  # sans « with » : init_db() du démarrage n'est pas exécuté
    app.dependency_overrides.clear()


@pytest.fixture()
def make_user(seeded_db):
    """Fabrique un utilisateur et renvoie (utilisateur, en-têtes d'authentification)."""
    from app.core.security import create_access_token
    from app.models import Role, User

    def _make(email: str = "etudiant@example.com", role: str = "student"):
        role_obj = seeded_db.scalar(select(Role).where(Role.name == role))
        user = User(full_name="Utilisateur Test", email=email, hashed_password="x", role=role_obj)
        seeded_db.add(user)
        seeded_db.commit()
        return user, {"Authorization": f"Bearer {create_access_token(user.id, role)}"}

    return _make