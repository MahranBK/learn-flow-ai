"""Domaines d'apprentissage et centres d'intérêt de l'étudiant."""

import pytest
from sqlalchemy import select

from app.db.seed import seed_catalog
from app.models import Course, Domain


@pytest.fixture()
def domain_ids(seeded_db) -> dict[str, int]:
    return {d.code: d.id for d in seeded_db.scalars(select(Domain))}


# --- catalogue ------------------------------------------------------------------------------


def test_le_catalogue_est_charge_sans_doublon_meme_relance(seeded_db):
    before = (len(seeded_db.scalars(select(Domain)).all()), len(seeded_db.scalars(select(Course)).all()))
    seed_catalog(seeded_db)
    seeded_db.commit()
    after = (len(seeded_db.scalars(select(Domain)).all()), len(seeded_db.scalars(select(Course)).all()))
    assert before == after


def test_chaque_cours_appartient_a_un_domaine(seeded_db):
    courses = {c.code: c.domain.code for c in seeded_db.scalars(select(Course))}
    assert courses["python-basics"] == "programming"
    assert courses["sql-basics"] == "data"


def test_liste_des_domaines(client, make_user, domain_ids):
    _, headers = make_user()
    response = client.get("/domains", headers=headers)

    assert response.status_code == 200
    assert {d["code"] for d in response.json()} == set(domain_ids)
    assert all({"id", "code", "name", "icon"} <= d.keys() for d in response.json())


def test_liste_des_domaines_sans_authentification_401(client):
    assert client.get("/domains").status_code == 401


# --- centres d'intérêt ----------------------------------------------------------------------


def test_aucun_interet_au_depart(client, make_user):
    _, headers = make_user()
    assert client.get("/me/interests", headers=headers).json() == []


def test_choisir_ses_domaines_puis_les_relire(client, make_user, domain_ids):
    _, headers = make_user()
    chosen = [domain_ids["web-dev"], domain_ids["ai"]]

    response = client.put("/me/interests", json={"domain_ids": chosen}, headers=headers)
    assert response.status_code == 200
    assert {d["code"] for d in response.json()} == {"web-dev", "ai"}
    assert {d["code"] for d in client.get("/me/interests", headers=headers).json()} == {"web-dev", "ai"}


def test_un_nouveau_choix_remplace_l_ancien(client, make_user, domain_ids):
    _, headers = make_user()
    client.put("/me/interests", json={"domain_ids": [domain_ids["web-dev"]]}, headers=headers)
    client.put("/me/interests", json={"domain_ids": [domain_ids["ai"]]}, headers=headers)

    assert [d["code"] for d in client.get("/me/interests", headers=headers).json()] == ["ai"]


def test_les_interets_sont_propres_a_chaque_etudiant(client, make_user, domain_ids):
    _, headers_a = make_user("a@example.com")
    _, headers_b = make_user("b@example.com")
    client.put("/me/interests", json={"domain_ids": [domain_ids["ai"]]}, headers=headers_a)

    assert client.get("/me/interests", headers=headers_b).json() == []


@pytest.mark.parametrize(
    "body",
    [{"domain_ids": []}, {"domain_ids": [9999]}, {"domain_ids": "web"}, {}],
)
def test_choix_invalide_422(client, make_user, body):
    _, headers = make_user()
    assert client.put("/me/interests", json=body, headers=headers).status_code == 422


def test_domaine_en_double_422(client, make_user, domain_ids):
    _, headers = make_user()
    ids = [domain_ids["ai"], domain_ids["ai"]]
    assert client.put("/me/interests", json={"domain_ids": ids}, headers=headers).status_code == 422


def test_domaine_desactive_refuse_422(client, make_user, domain_ids, seeded_db):
    seeded_db.get(Domain, domain_ids["ai"]).is_active = False
    seeded_db.commit()
    _, headers = make_user()
    response = client.put("/me/interests", json={"domain_ids": [domain_ids["ai"]]}, headers=headers)
    assert response.status_code == 422


def test_un_admin_n_a_pas_de_centres_d_interet_403(client, make_user, domain_ids):
    _, headers = make_user("admin@example.com", role="admin")
    assert client.get("/me/interests", headers=headers).status_code == 403
    response = client.put("/me/interests", json={"domain_ids": [domain_ids["ai"]]}, headers=headers)
    assert response.status_code == 403
