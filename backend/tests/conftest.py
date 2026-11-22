import os

# Doit être défini AVANT tout import de `app` : les tests n'utilisent jamais la vraie base.
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

import pytest
from sqlalchemy import create_engine
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