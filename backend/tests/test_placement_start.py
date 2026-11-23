from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models import (
    BankQuestion,
    Course,
    PlacementTest,
    ReviewStatus,
    TestQuestion,
    TestStatus,
)
from app.models.user import utcnow
from app.services import placement as placement_service


@pytest.fixture()
def course_id(seeded_db) -> int:
    return seeded_db.scalar(select(Course.id).where(Course.code == "python-basics"))


def start(client, headers, course_id):
    return client.post("/placement-tests", json={"course_id": course_id}, headers=headers)


# --- démarrage ------------------------------------------------------------------------------


def test_demarrage_cree_un_test_de_16_questions(client, make_user, course_id):
    _, headers = make_user()
    response = start(client, headers, course_id)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "in_progress"
    assert body["total_questions"] == 16  # 4 compétences × (1 + 2 + 1)
    assert [q["position"] for q in body["questions"]] == list(range(1, 17))
    assert body["answers"] == []


def test_la_bonne_reponse_n_est_jamais_envoyee(client, make_user, course_id, seeded_db):
    _, headers = make_user()
    text = start(client, headers, course_id).text
    assert "correct_answer" not in text
    assert "difficulty" not in text
    # même test avec la lecture (GET)
    test_id = seeded_db.scalar(select(PlacementTest.id))
    assert "correct_answer" not in client.get(f"/placement-tests/{test_id}", headers=headers).text


def test_le_test_est_fige_et_options_coherentes_avec_la_banque(client, make_user, course_id, seeded_db):
    _, headers = make_user()
    start(client, headers, course_id)

    for tq in seeded_db.scalars(select(TestQuestion)):
        bank_q = seeded_db.get(BankQuestion, tq.bank_question_id)
        assert sorted(tq.options) == sorted(bank_q.options)  # mêmes options, ordre libre
        assert tq.correct_answer in tq.options
        assert tq.difficulty == bank_q.difficulty


def test_deuxieme_demarrage_renvoie_le_meme_test(client, make_user, course_id, seeded_db):
    _, headers = make_user()
    first = start(client, headers, course_id)
    second = start(client, headers, course_id)

    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json()["id"] == second.json()["id"]
    assert len(seeded_db.scalars(select(PlacementTest)).all()) == 1


def test_deux_etudiants_n_ont_pas_le_meme_test(client, make_user, course_id, seeded_db):
    _, headers_a = make_user("a@example.com")
    _, headers_b = make_user("b@example.com")
    start(client, headers_a, course_id)
    start(client, headers_b, course_id)

    tests = seeded_db.scalars(select(PlacementTest).order_by(PlacementTest.id)).all()
    assert len(tests) == 2
    assert tests[0].user_id != tests[1].user_id


# --- accès et erreurs -----------------------------------------------------------------------


def test_sans_authentification_401(client, course_id):
    assert client.post("/placement-tests", json={"course_id": course_id}).status_code == 401
    assert client.get("/placement-tests/1").status_code == 401


def test_un_admin_ne_passe_pas_de_test_403(client, make_user, course_id):
    _, headers = make_user("admin@example.com", role="admin")
    assert start(client, headers, course_id).status_code == 403


def test_cours_inconnu_ou_inactif_404(client, make_user, course_id, seeded_db):
    _, headers = make_user()
    assert start(client, headers, 9999).status_code == 404

    seeded_db.get(Course, course_id).is_active = False
    seeded_db.commit()
    assert start(client, headers, course_id).status_code == 404


def test_lire_le_test_d_un_autre_etudiant_donne_404(client, make_user, course_id):
    _, headers_a = make_user("a@example.com")
    _, headers_b = make_user("b@example.com")
    test_id = start(client, headers_a, course_id).json()["id"]

    assert client.get(f"/placement-tests/{test_id}", headers=headers_a).status_code == 200
    assert client.get(f"/placement-tests/{test_id}", headers=headers_b).status_code == 404


def test_banque_insuffisante_503(client, make_user, course_id, seeded_db):
    _, headers = make_user()
    for question in seeded_db.scalars(select(BankQuestion)):
        question.review_status = ReviewStatus.RETIRED  # aucune question utilisable
    seeded_db.commit()

    response = start(client, headers, course_id)
    assert response.status_code == 503
    assert "banque de questions" in response.json()["detail"]
    assert seeded_db.scalars(select(PlacementTest)).first() is None  # rien n'a été créé


def test_les_questions_non_approuvees_ne_sont_jamais_utilisees(client, make_user, course_id, seeded_db):
    _, headers = make_user()
    for question in seeded_db.scalars(select(BankQuestion).limit(5)):
        question.review_status = ReviewStatus.DRAFT
    seeded_db.commit()
    start(client, headers, course_id)

    used = {tq.bank_question_id for tq in seeded_db.scalars(select(TestQuestion))}
    drafts = {q.id for q in seeded_db.scalars(select(BankQuestion)) if q.review_status == ReviewStatus.DRAFT}
    assert not (used & drafts)


# --- nouvelle tentative ---------------------------------------------------------------------


def complete(db, test_id: int, days_ago: int) -> None:
    test = db.get(PlacementTest, test_id)
    test.status = TestStatus.COMPLETED
    test.completed_at = utcnow() - timedelta(days=days_ago)
    db.commit()


def test_nouvelle_tentative_refusee_pendant_le_delai(client, make_user, course_id, seeded_db):
    _, headers = make_user()
    complete(seeded_db, start(client, headers, course_id).json()["id"], days_ago=1)

    response = start(client, headers, course_id)
    assert response.status_code == 409
    assert "repasser ce test" in response.json()["detail"]


def test_nouvelle_tentative_apres_le_delai_varie_les_questions(client, make_user, course_id, seeded_db):
    _, headers = make_user()
    first_id = start(client, headers, course_id).json()["id"]
    complete(seeded_db, first_id, days_ago=30)

    response = start(client, headers, course_id)
    assert response.status_code == 201
    second_id = response.json()["id"]
    assert second_id != first_id
    assert seeded_db.get(PlacementTest, second_id).attempt_number == 2

    def bank_ids(test_id):
        return {tq.bank_question_id for tq in seeded_db.get(PlacementTest, test_id).questions}

    # 7 questions par compétence, 4 posées au 1er test : au plus 1 question répétée par compétence
    assert len(bank_ids(first_id) & bank_ids(second_id)) <= 4


def test_demandes_simultanees_ne_creent_qu_un_test(seeded_db, make_user, course_id, monkeypatch):
    """Si deux requêtes passent le contrôle en même temps, l'index unique protège."""
    user, _ = make_user()
    existing, _ = placement_service.start_or_resume(seeded_db, user.id, course_id)

    real_find = placement_service._find_active
    calls = {"n": 0}

    def stale_read(db, user_id, course_id_):
        calls["n"] += 1
        return None if calls["n"] == 1 else real_find(db, user_id, course_id_)  # 1re lecture « périmée »

    monkeypatch.setattr(placement_service, "_find_active", stale_read)
    test, created = placement_service.start_or_resume(seeded_db, user.id, course_id)

    assert created is False
    assert test.id == existing.id
    assert len(seeded_db.scalars(select(PlacementTest)).all()) == 1


# --- liste des cours ------------------------------------------------------------------------


def test_liste_des_cours(client, make_user):
    _, headers = make_user()
    response = client.get("/courses", headers=headers)
    assert response.status_code == 200
    assert [c["code"] for c in response.json()] == ["python-basics", "sql-basics"]
    assert client.get("/courses").status_code == 401