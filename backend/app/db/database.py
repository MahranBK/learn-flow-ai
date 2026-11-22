from sqlalchemy import create_engine, select
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import DATABASE_URL


# SQLite (tests) a besoin de check_same_thread=False
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dépendance FastAPI : ouvre une session par requête et la ferme ensuite."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DEFAULT_ROLES = {
    "student": "Étudiant : passe les tests, suit son parcours, fait les exercices.",
    "admin": "Administrateur : gère les utilisateurs et les rôles.",
}


def init_db() -> None:
    """Crée les tables et insère les rôles par défaut s'ils n'existent pas."""
    from app.models import Role  # importe tous les modèles via models/__init__.py
    from app.db.seed import seed_catalog , seed_question_bank # import local : seed.py importe les modèles
    from app.db.seed import seed_catalog, seed_question_bank  # import local : seed.py importe les modèles
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        existing = set(db.scalars(select(Role.name)).all())
        for name, description in DEFAULT_ROLES.items():
            if name not in existing:
                db.add(Role(name=name, description=description))
        seed_catalog(db)# cours et compétences par défaut
        seed_question_bank(db)  # banque de questions de secours
        db.commit()