import pytest
from sqlalchemy import select, update

from app.models import (
    Course,
    MasteryLevel,
    PlacementLevel,
    PlacementTest,
    SkillResult,
    TestQuestion,
    TestStatus,
)
from app.services import submission as submission_service
from app.schemas.placement import SubmitAnswer


@pytest.fixture()
def course_id(seeded_db) -> int:
    return seeded_db.scalar(select(Course.id).where(Course.code == "python-basics"))


@pytest.fixture()
def started(client, make_user, course_id):
    """Un étudiant avec un test démarré : (en-têtes, corps du test)."""
    _, headers = make_user()
    body = client.post("/placement-tests", json={"course_id": course_id}, headers=headers).json()
    return headers, body


def rows(db, test_id):
    """Questions du test en base, avec leur bonne réponse (que l'API ne donne pas)."""
    db.expire_all()
    return list(db.scalars(select(TestQuestion).where(TestQuestion.test_id == test_id)))


def all_correct(db, test_id):
    return [{"question_id": q.id, "answer": q.correct_answer} for q in rows(db, test_id)]


def wrong_option(question) -> str:
    return next(o for o in question.options if o != question.correct_answer)


def submit(client, headers, test_id, answers):
    return client.post(f"/placement-tests/{test_id}/submit", json={"answers": answers}, headers=headers)


# --- sauvegarde des réponses (reprise) ------------------------------------------------------


def test_sauvegarde_d_une_reponse_puis_reprise(client, started, seeded_db):
    headers, body = started
    question = rows(seeded_db, body["id"])[0]

    response = client.put(
        f"/placement-tests/{body['id']}/answers/{question.id}",
        json={"answer": question.options[0]},
        headers=headers,
    )
    assert response.status_code == 204

    resumed = client.get(f"/placement-tests/{body['id']}", headers=headers).json()
    assert resumed["answers"] == [{"question_id": question.id, "answer": question.options[0]}]
    assert "correct_answer" not in str(resumed)


def test_une_reponse_peut_etre_remplacee(client, started, seeded_db):
    headers, body = started
    question = rows(seeded_db, body["id"])[0]
    url = f"/placement-tests/{body['id']}/answers/{question.id}"
    client.put(url, json={"answer": question.options[0]}, headers=headers)
    client.put(url, json={"answer": question.options[1]}, headers=headers)

    answers = client.get(f"/placement-tests/{body['id']}", headers=headers).json()["answers"]
    assert answers == [{"question_id": question.id, "answer": question.options[1]}]


def test_reponse_hors_options_422(client, started, seeded_db):
    headers, body = started
    question = rows(seeded_db, body["id"])[0]
    response = client.put(
        f"/placement-tests/{body['id']}/answers/{question.id}", json={"answer": "invention"}, headers=headers
    )
    assert response.status_code == 422


def test_question_d_un_autre_test_404(client, started, make_user, course_id, seeded_db):
    headers, body = started
    _, other_headers = make_user("autre@example.com")
    other = client.post("/placement-tests", json={"course_id": course_id}, headers=other_headers).json()
    foreign_question = rows(seeded_db, other["id"])[0]

    response = client.put(
        f"/placement-tests/{body['id']}/answers/{foreign_question.id}",
        json={"answer": foreign_question.options[0]},
        headers=headers,
    )
    assert response.status_code == 404


# --- soumission et score --------------------------------------------------------------------


def test_tout_juste_donne_100_et_niveau_avance(client, started, seeded_db):
    headers, body = started
    response = submit(client, headers, body["id"], all_correct(seeded_db, body["id"]))

    assert response.status_code == 200
    data = response.json()
    assert (data["score"], data["level"]) == (100.0, "advanced")
    assert (data["correct_count"], data["total_questions"], data["unanswered_count"]) == (16, 16, 0)

    test = seeded_db.get(PlacementTest, body["id"])
    seeded_db.refresh(test)
    assert test.status == TestStatus.COMPLETED and test.completed_at is not None
    assert test.scoring_version == "v1"
    skill_results = seeded_db.scalars(select(SkillResult).where(SkillResult.test_id == test.id)).all()
    assert len(skill_results) == 4
    assert {r.mastery for r in skill_results} == {MasteryLevel.MASTERED}
    assert all(q.is_correct is True for q in rows(seeded_db, test.id))


def test_aucune_reponse_donne_0_et_resultat_non_fiable(client, started):
    headers, body = started
    data = submit(client, headers, body["id"], []).json()
    assert (data["score"], data["level"], data["unanswered_count"]) == (0.0, "beginner", 16)

    result = client.get(f"/placement-tests/{body['id']}/result", headers=headers).json()
    assert result["reliable"] is False


def test_les_questions_difficiles_pesent_plus(client, started, seeded_db):
    """Faciles et moyennes justes, difficiles fausses : par compétence 5 points sur 8 = 62,5 %."""
    headers, body = started
    answers = []
    for q in rows(seeded_db, body["id"]):
        answer = wrong_option(q) if q.difficulty == 3 else q.correct_answer
        answers.append({"question_id": q.id, "answer": answer})

    data = submit(client, headers, body["id"], answers).json()
    assert (data["score"], data["level"]) == (62.5, "intermediate")
    assert data["correct_count"] == 12


def test_les_reponses_sauvegardees_sont_utilisees_a_la_soumission(client, started, seeded_db):
    headers, body = started
    for q in rows(seeded_db, body["id"]):
        client.put(f"/placement-tests/{body['id']}/answers/{q.id}", json={"answer": q.correct_answer}, headers=headers)

    assert submit(client, headers, body["id"], []).json()["score"] == 100.0


def test_une_reponse_null_efface_la_reponse_enregistree(client, started, seeded_db):
    headers, body = started
    questions = rows(seeded_db, body["id"])
    for q in questions:
        client.put(f"/placement-tests/{body['id']}/answers/{q.id}", json={"answer": q.correct_answer}, headers=headers)

    data = submit(client, headers, body["id"], [{"question_id": questions[0].id, "answer": None}]).json()
    assert data["unanswered_count"] == 1 and data["correct_count"] == 15


# --- protections ----------------------------------------------------------------------------


def test_un_test_termine_ne_peut_pas_etre_resoumis(client, started, seeded_db):
    headers, body = started
    first = submit(client, headers, body["id"], all_correct(seeded_db, body["id"]))
    second = submit(client, headers, body["id"], [])

    assert first.status_code == 200
    assert second.status_code == 409
    seeded_db.expire_all()
    assert seeded_db.get(PlacementTest, body["id"]).score == 100.0  # le score n'a pas bougé


def test_impossible_de_modifier_une_reponse_apres_la_fin(client, started, seeded_db):
    headers, body = started
    submit(client, headers, body["id"], [])
    question = rows(seeded_db, body["id"])[0]

    response = client.put(
        f"/placement-tests/{body['id']}/answers/{question.id}",
        json={"answer": question.correct_answer},
        headers=headers,
    )
    assert response.status_code == 409


def test_reponse_invalide_a_la_soumission_ne_change_rien(client, started, seeded_db):
    headers, body = started
    question = rows(seeded_db, body["id"])[0]
    response = submit(client, headers, body["id"], [{"question_id": question.id, "answer": "invention"}])

    assert response.status_code == 422
    seeded_db.expire_all()
    assert seeded_db.get(PlacementTest, body["id"]).status == TestStatus.IN_PROGRESS


def test_question_inconnue_a_la_soumission_422(client, started):
    headers, body = started
    assert submit(client, headers, body["id"], [{"question_id": 999999, "answer": "x"}]).status_code == 422


def test_question_en_double_dans_la_soumission_422(client, started, seeded_db):
    headers, body = started
    q = rows(seeded_db, body["id"])[0]
    answers = [{"question_id": q.id, "answer": q.options[0]}] * 2
    assert submit(client, headers, body["id"], answers).status_code == 422


def test_soumettre_le_test_d_un_autre_404(client, started, make_user):
    _, body = started
    _, other_headers = make_user("autre@example.com")
    assert submit(client, other_headers, body["id"], []).status_code == 404


def test_sans_authentification_401(client, started):
    _, body = started
    assert client.post(f"/placement-tests/{body['id']}/submit", json={"answers": []}).status_code == 401
    assert client.get(f"/placement-tests/{body['id']}/result").status_code == 401


def test_double_soumission_simultanee_une_seule_correction(seeded_db, started):
    """
    Une autre requête termine le test entre notre lecture et notre écriture.
    En mémoire le test paraît encore « en cours » : seul le passage atomique en SQL peut refuser.
    """
    _, body = started
    user_id = seeded_db.get(PlacementTest, body["id"]).user_id
    seeded_db.expire_all()
    test = submission_service.get_test_for_user(seeded_db, body["id"], user_id)
    assert test.status == TestStatus.IN_PROGRESS  # lecture « en cours » gardée en mémoire

    seeded_db.execute(  # l'autre requête a terminé le test (sans commit : la lecture reste périmée)
        update(PlacementTest)
        .where(PlacementTest.id == body["id"])
        .values(status=TestStatus.COMPLETED)
        .execution_options(synchronize_session=False)
    )

    with pytest.raises(submission_service.AlreadyCompletedError):
        submission_service.submit_test(seeded_db, body["id"], user_id, [SubmitAnswer(question_id=1, answer=None)])
    seeded_db.expire_all()
    assert seeded_db.get(PlacementTest, body["id"]).score is None  # aucune correction n'a été enregistrée


# --- résultat et historique -----------------------------------------------------------------


def test_resultat_indisponible_avant_la_fin_409(client, started):
    headers, body = started
    assert client.get(f"/placement-tests/{body['id']}/result", headers=headers).status_code == 409


def test_resultat_complet_avec_correction(client, started, seeded_db):
    headers, body = started
    questions = rows(seeded_db, body["id"])
    answers = [{"question_id": q.id, "answer": q.correct_answer} for q in questions]
    answers[0]["answer"] = wrong_option(questions[0])  # une erreur volontaire
    submit(client, headers, body["id"], answers)

    result = client.get(f"/placement-tests/{body['id']}/result", headers=headers).json()
    assert result["correct_count"] == 15 and result["reliable"] is True
    assert result["course"]["code"] == "python-basics"
    assert len(result["skills"]) == 4
    assert {s["mastery"] for s in result["skills"]} <= {"mastered", "partial", "gap"}

    review = result["review"]
    assert len(review) == 16
    assert review[0]["is_correct"] is False and review[0]["your_answer"] != review[0]["correct_answer"]
    assert all(item["explanation"] for item in review)  # explications de la banque
    assert all(item["correct_answer"] in item["options"] for item in review)


def test_resultat_d_un_autre_etudiant_404(client, started, make_user, seeded_db):
    headers, body = started
    submit(client, headers, body["id"], [])
    _, other_headers = make_user("autre@example.com")
    assert client.get(f"/placement-tests/{body['id']}/result", headers=other_headers).status_code == 404


def test_apres_la_soumission_le_delai_de_repasse_s_applique(client, started, course_id):
    headers, body = started
    submit(client, headers, body["id"], [])
    response = client.post("/placement-tests", json={"course_id": course_id}, headers=headers)
    assert response.status_code == 409


def test_historique_ne_contient_que_mes_tests(client, started, make_user, course_id):
    headers, body = started
    _, other_headers = make_user("autre@example.com")
    client.post("/placement-tests", json={"course_id": course_id}, headers=other_headers)
    submit(client, headers, body["id"], [])

    mine = client.get("/placement-tests", headers=headers).json()
    assert [t["id"] for t in mine] == [body["id"]]
    assert mine[0]["status"] == "completed" and mine[0]["score"] == 0.0 and mine[0]["attempt_number"] == 1

    assert client.get(f"/placement-tests?course_id={course_id}", headers=headers).json() == mine
    assert client.get("/placement-tests?course_id=9999", headers=headers).json() == []
    assert client.get("/placement-tests").status_code == 401