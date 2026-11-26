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
    return test["id"]


def get_detail(client, headers, skill_id):
    return client.get(f"/skills/{skill_id}/detail", headers=headers)


def test_sans_jeton_401(client, course):
    assert client.get(f"/skills/{course.skills[0].id}/detail").status_code == 401


def test_admin_refuse_403(client, make_user, course):
    _, headers = make_user("admin@example.com", role="admin")
    assert get_detail(client, headers, course.skills[0].id).status_code == 403


def test_competence_inconnue_404(client, make_user):
    _, headers = make_user()
    assert get_detail(client, headers, 999_999).status_code == 404


def test_aucun_test_409(client, make_user, course):
    _, headers = make_user()
    response = get_detail(client, headers, course.skills[0].id)
    assert response.status_code == 409
    assert "test de positionnement" in response.json()["detail"]


def test_detail_apres_un_test_rate(client, seeded_db, make_user, course):
    _, headers = make_user()
    test_id = run_test(client, seeded_db, headers, course.id, correct=False)
    skill = course.skills[0]

    body = get_detail(client, headers, skill.id).json()
    assert body["skill"]["id"] == skill.id
    assert body["course"]["id"] == course.id
    assert body["test_id"] == test_id
    assert body["mastery"] == "gap"
    assert body["score"] == 0
    assert body["n_correct"] == 0
    assert body["step"] is None  # parcours pas encore construit


def test_detail_apres_un_test_parfait(client, seeded_db, make_user, course):
    _, headers = make_user()
    run_test(client, seeded_db, headers, course.id, correct=True)
    client.post("/learning-path/rebuild", headers=headers)

    body = get_detail(client, headers, course.skills[0].id).json()
    assert body["mastery"] == "mastered"
    assert body["score"] == 100
    assert body["step"] is None  # compétence maîtrisée : pas d'étape


def test_lien_vers_l_etape_du_parcours(client, seeded_db, make_user, course):
    _, headers = make_user()
    run_test(client, seeded_db, headers, course.id, correct=False)
    steps = client.post("/learning-path/rebuild", headers=headers).json()["steps"]
    first = steps[0]

    body = get_detail(client, headers, first["skill"]["id"]).json()
    assert body["step"] == {"id": first["id"], "position": 1, "status": "todo"}

    client.patch(f"/learning-path/steps/{first['id']}", json={"status": "done"}, headers=headers)
    assert get_detail(client, headers, first["skill"]["id"]).json()["step"]["status"] == "done"


def test_un_etudiant_ne_voit_pas_le_detail_d_un_autre(client, seeded_db, make_user, course):
    _, headers_a = make_user("a@example.com")
    _, headers_b = make_user("b@example.com")
    run_test(client, seeded_db, headers_a, course.id, correct=False)
    skill_id = course.skills[0].id

    assert get_detail(client, headers_a, skill_id).status_code == 200
    assert get_detail(client, headers_b, skill_id).status_code == 409

def test_questions_ratees_listees_avec_la_correction(client, seeded_db, make_user, course):
    _, headers = make_user()
    run_test(client, seeded_db, headers, course.id, correct=False)
    skill = course.skills[0]

    body = get_detail(client, headers, skill.id).json()
    assert body["n_questions"] > 0
    assert len(body["missed_questions"]) == body["n_questions"]
    for q in body["missed_questions"]:
        assert q["user_answer"] != q["correct_answer"]
        assert q["correct_answer"] in q["options"]
    positions = [q["position"] for q in body["missed_questions"]]
    assert positions == sorted(positions)


def test_aucune_question_ratee_apres_un_test_parfait(client, seeded_db, make_user, course):
    _, headers = make_user()
    run_test(client, seeded_db, headers, course.id, correct=True)

    body = get_detail(client, headers, course.skills[0].id).json()
    assert body["missed_questions"] == []
    assert body["n_unanswered"] == 0