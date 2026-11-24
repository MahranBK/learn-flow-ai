"""T12 - Tests d'intégration : authentification et rôles (US1 + US2)."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import select

from app.core.config import JWT_ALGORITHM, JWT_SECRET_KEY
from app.core.dependencies import require_role
from app.core.security import create_access_token
from app.db.database import get_db
from app.models import User

VALID = {"full_name": "Ali Ben Salah", "email": "ali@example.com", "password": "motdepasse1"}


def register(client, **overrides):
    return client.post("/auth/register", json={**VALID, **overrides})


def login(client, email=VALID["email"], password=VALID["password"]):
    return client.post("/auth/login", json={"email": email, "password": password})


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# --- inscription (US1) ---------------------------------------------------------------------


def test_inscription_ok_cree_un_etudiant(client, seeded_db):
    response = register(client)

    assert response.status_code == 201
    user = response.json()["user"]
    assert user["email"] == "ali@example.com"
    assert user["role"] == "student"
    assert "password" not in user and "hashed_password" not in user
    # le mot de passe est haché en base, jamais stocké en clair
    stored = seeded_db.scalar(select(User).where(User.email == "ali@example.com"))
    assert stored.hashed_password != VALID["password"]
    assert stored.hashed_password.startswith("$2")


def test_inscription_normalise_l_email_en_minuscules(client):
    response = register(client, email="Ali@Example.COM")
    assert response.status_code == 201
    assert response.json()["user"]["email"] == "ali@example.com"


def test_inscription_email_deja_utilise_409(client):
    assert register(client).status_code == 201
    response = register(client, email="ALI@example.com")  # même compte, autre casse
    assert response.status_code == 409
    assert response.json()["detail"] == "Cet email est déjà utilisé."


@pytest.mark.parametrize("password", ["motdepasse", "12345678", "abc1"])  # sans chiffre / sans lettre / trop court
def test_inscription_mot_de_passe_faible_422(client, password):
    assert register(client, password=password).status_code == 422


def test_inscription_email_invalide_422(client):
    assert register(client, email="pas-un-email").status_code == 422


# --- connexion (US2) -----------------------------------------------------------------------


def test_connexion_ok_renvoie_un_jeton(client):
    register(client)
    response = login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "ali@example.com"


def test_connexion_mauvais_mot_de_passe_401(client):
    register(client)
    response = login(client, password="mauvaismdp1")
    assert response.status_code == 401
    assert response.json()["detail"] == "Email ou mot de passe incorrect."


def test_connexion_email_inconnu_meme_message_401(client):
    # même message que pour un mauvais mot de passe : on ne révèle pas quels emails existent
    response = login(client, email="inconnu@example.com")
    assert response.status_code == 401
    assert response.json()["detail"] == "Email ou mot de passe incorrect."


def test_connexion_compte_desactive_403(client, seeded_db):
    register(client)
    user = seeded_db.scalar(select(User).where(User.email == "ali@example.com"))
    user.is_active = False
    seeded_db.commit()
    assert login(client).status_code == 403


# --- GET /auth/me --------------------------------------------------------------------------


def test_me_sans_jeton_401(client):
    assert client.get("/auth/me").status_code == 401


def test_me_jeton_invalide_401(client):
    assert client.get("/auth/me", headers=bearer("pas.un.jeton")).status_code == 401


def test_me_jeton_signe_avec_une_autre_cle_401(client):
    forged = jwt.encode({"sub": "1", "role": "admin"}, "autre-cle", algorithm=JWT_ALGORITHM)
    assert client.get("/auth/me", headers=bearer(forged)).status_code == 401


def test_me_jeton_expire_401(client, make_user):
    user, _ = make_user()
    expired = jwt.encode(
        {"sub": str(user.id), "role": "student", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )
    assert client.get("/auth/me", headers=bearer(expired)).status_code == 401


def test_me_utilisateur_inexistant_401(client):
    assert client.get("/auth/me", headers=bearer(create_access_token(9999, "student"))).status_code == 401


def test_me_jeton_valide_200(client):
    register(client)
    token = login(client).json()["access_token"]

    response = client.get("/auth/me", headers=bearer(token))
    assert response.status_code == 200
    assert response.json()["email"] == "ali@example.com"


# --- rôles : require_role -------------------------------------------------------------------


@pytest.fixture()
def role_client(seeded_db):
    """Mini-application avec une route réservée aux admins (il n'en existe pas encore dans l'API)."""
    app = FastAPI()

    @app.get("/admin-only", dependencies=[Depends(require_role("admin"))])
    def admin_only():
        return {"ok": True}

    app.dependency_overrides[get_db] = lambda: seeded_db
    return TestClient(app)


def test_route_admin_sans_jeton_401(role_client):
    assert role_client.get("/admin-only").status_code == 401


def test_route_admin_refuse_un_etudiant_403(role_client, make_user):
    _, headers = make_user(role="student")
    response = role_client.get("/admin-only", headers=headers)
    assert response.status_code == 403
    assert "Accès refusé" in response.json()["detail"]


def test_route_admin_accepte_un_admin_200(role_client, make_user):
    _, headers = make_user(email="admin@example.com", role="admin")
    assert role_client.get("/admin-only", headers=headers).status_code == 200
