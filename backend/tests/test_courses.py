"""Catalogue des cours : domaines, filtrage selon les centres d'intérêt, banque de questions."""

import pytest
from sqlalchemy import select

from app.models import Domain


@pytest.fixture()
def domain_ids(seeded_db) -> dict[str, int]:
    return {d.code: d.id for d in seeded_db.scalars(select(Domain))}


def codes(response) -> list[str]:
    return [course["code"] for course in response.json()]


def choose(client, headers, domain_ids, *domain_codes):
    ids = [domain_ids[code] for code in domain_codes]
    assert client.put("/me/interests", json={"domain_ids": ids}, headers=headers).status_code == 200


def test_le_catalogue_complet_contient_les_cours_de_chaque_domaine(client, make_user):
    _, headers = make_user()
    response = client.get("/courses", headers=headers)

    assert response.status_code == 200
    assert {"python-basics", "sql-basics", "html-css-basics", "javascript-basics", "ml-basics"} <= set(
        codes(response)
    )


def test_chaque_cours_expose_son_domaine_et_ses_competences(client, make_user):
    _, headers = make_user()
    course = next(c for c in client.get("/courses", headers=headers).json() if c["code"] == "ml-basics")

    assert course["domain"]["code"] == "ai"
    assert course["domain_id"] == course["domain"]["id"]
    assert len(course["skills"]) == 4


def test_sans_centres_d_interet_aucun_cours_pour_mine(client, make_user):
    _, headers = make_user()
    assert client.get("/courses", params={"mine": True}, headers=headers).json() == []


def test_mine_ne_renvoie_que_les_cours_des_domaines_choisis(client, make_user, domain_ids):
    _, headers = make_user()
    choose(client, headers, domain_ids, "web-dev")

    response = client.get("/courses", params={"mine": True}, headers=headers)
    assert set(codes(response)) == {"html-css-basics", "javascript-basics"}


def test_mine_avec_plusieurs_domaines(client, make_user, domain_ids):
    _, headers = make_user()
    choose(client, headers, domain_ids, "ai", "programming")

    response = client.get("/courses", params={"mine": True}, headers=headers)
    assert set(codes(response)) == {"ml-basics", "python-basics"}


def test_changer_de_domaine_change_les_cours(client, make_user, domain_ids):
    _, headers = make_user()
    choose(client, headers, domain_ids, "web-dev")
    choose(client, headers, domain_ids, "data")

    assert codes(client.get("/courses", params={"mine": True}, headers=headers)) == ["sql-basics"]


def test_les_choix_d_un_etudiant_ne_changent_pas_le_catalogue_d_un_autre(client, make_user, domain_ids):
    _, headers_a = make_user("a@example.com")
    _, headers_b = make_user("b@example.com")
    choose(client, headers_a, domain_ids, "ai")

    assert client.get("/courses", params={"mine": True}, headers=headers_b).json() == []


def test_filtre_par_domaine(client, make_user, domain_ids):
    _, headers = make_user()
    response = client.get("/courses", params={"domain_id": domain_ids["web-dev"]}, headers=headers)
    assert set(codes(response)) == {"html-css-basics", "javascript-basics"}


def test_cours_tries_par_domaine_puis_par_titre(client, make_user):
    _, headers = make_user()
    courses = client.get("/courses", headers=headers).json()
    keys = [(c["domain"]["name"], c["title"]) for c in courses]
    assert keys == sorted(keys)


def test_catalogue_sans_authentification_401(client):
    assert client.get("/courses").status_code == 401


@pytest.mark.parametrize("code", ["html-css-basics", "javascript-basics", "ml-basics"])
def test_les_nouveaux_cours_ont_assez_de_questions_sans_llm(client, make_user, code):
    """La banque écrite à l'avance suffit : le test démarre même sans aucune clé LLM."""
    _, headers = make_user()
    course_id = next(c["id"] for c in client.get("/courses", headers=headers).json() if c["code"] == code)

    response = client.post("/placement-tests", json={"course_id": course_id}, headers=headers)
    assert response.status_code == 201
    assert response.json()["total_questions"] == 16
