import pytest
from sqlalchemy import select

from app.models import Course, TestQuestion


@pytest.fixture()
def course(seeded_db) -> Course:
    return seeded_db.scalar(select(Course).where(Course.code == "python-basics"))


def run_test(client, seeded_db, headers, course_id, correct: bool):
    test = client.post("/placement-tests", json={"course_id": course_id}, headers=headers).json()
    seeded_db.expire_all()
    questions = seeded_db.scalars(select(TestQuestion).where(TestQuestion.test_id == test["id"])).all()
    answers = [
        {
            "question_id": q.id,
            "answer": q.correct_answer if correct else next(o for o in q.options if o != q.correct_answer),
        }
        for q in questions
    ]
    response = client.post(f"/placement-tests/{test['id']}/submit", json={"answers": answers}, headers=headers)
    assert response.status_code == 200


def rebuild(client, headers):
    return client.post("/learning-path/rebuild", headers=headers)


# --- accès -----------------------------------------------------------------------------------


def test_sans_jeton_401(client):
    assert client.get("/learning-path").status_code == 401
    assert client.post("/learning-path/rebuild").status_code == 401


def test_admin_refuse_403(client, make_user):
    _, headers = make_user("admin@example.com", role="admin")
    assert client.get("/learning-path", headers=headers).status_code == 403


# --- construction (US8) ----------------------------------------------------------------------


def test_aucun_parcours_404(client, make_user):
    _, headers = make_user()
    assert client.get("/learning-path", headers=headers).status_code == 404


def test_rebuild_sans_test_409(client, make_user):
    _, headers = make_user()
    response = rebuild(client, headers)
    assert response.status_code == 409
    assert "test de positionnement" in response.json()["detail"]


def test_rebuild_apres_un_test_rate(client, seeded_db, make_user, course):
    _, headers = make_user()
    run_test(client, seeded_db, headers, course.id, correct=False)

    response = rebuild(client, headers)
    assert response.status_code == 201
    body = response.json()
    assert len(body["steps"]) == len(course.skills)
    assert [s["position"] for s in body["steps"]] == list(range(1, len(course.skills) + 1))
    assert body["progress"] == {
        "total": len(course.skills), "done": 0, "in_progress": 0, "todo": len(course.skills), "percent": 0,
    }
    assert client.get("/learning-path", headers=headers).json()["id"] == body["id"]
    assert "correct_answer" not in response.text


def test_rebuild_apres_un_test_parfait_parcours_vide(client, seeded_db, make_user, course):
    _, headers = make_user()
    run_test(client, seeded_db, headers, course.id, correct=True)
    body = rebuild(client, headers).json()
    assert body["steps"] == []
    assert body["progress"]["percent"] == 100


# --- suivi (US9) -----------------------------------------------------------------------------


def test_marquer_une_etape_terminee_puis_la_rouvrir(client, seeded_db, make_user, course):
    _, headers = make_user()
    run_test(client, seeded_db, headers, course.id, correct=False)
    steps = rebuild(client, headers).json()["steps"]
    step_id = steps[0]["id"]

    done = client.patch(f"/learning-path/steps/{step_id}", json={"status": "done"}, headers=headers).json()
    assert done["progress"]["done"] == 1
    assert done["progress"]["percent"] == round(100 / len(steps))
    assert done["steps"][0]["status"] == "done"
    assert done["steps"][0]["completed_at"] is not None

    reopened = client.patch(f"/learning-path/steps/{step_id}", json={"status": "todo"}, headers=headers).json()
    assert reopened["progress"]["done"] == 0
    assert reopened["steps"][0]["completed_at"] is None


def test_statut_invalide_422(client, seeded_db, make_user, course):
    _, headers = make_user()
    run_test(client, seeded_db, headers, course.id, correct=False)
    step_id = rebuild(client, headers).json()["steps"][0]["id"]
    response = client.patch(f"/learning-path/steps/{step_id}", json={"status": "fini"}, headers=headers)
    assert response.status_code == 422


def test_etape_d_un_autre_etudiant_404(client, seeded_db, make_user, course):
    _, headers_a = make_user("a@example.com")
    _, headers_b = make_user("b@example.com")
    run_test(client, seeded_db, headers_a, course.id, correct=False)
    step_id = rebuild(client, headers_a).json()["steps"][0]["id"]

    response = client.patch(f"/learning-path/steps/{step_id}", json={"status": "done"}, headers=headers_b)
    assert response.status_code == 404


def test_etape_d_un_parcours_archive_404(client, seeded_db, make_user, course):
    _, headers = make_user()
    run_test(client, seeded_db, headers, course.id, correct=False)
    old_step_id = rebuild(client, headers).json()["steps"][0]["id"]
    rebuild(client, headers)  # l'ancien parcours est archivé

    response = client.patch(f"/learning-path/steps/{old_step_id}", json={"status": "done"}, headers=headers)
    assert response.status_code == 404