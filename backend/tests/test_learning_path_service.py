import pytest
from sqlalchemy import select

from app.models import Course, LearningPath, PathStatus, StepStatus, TestQuestion
from app.services import learning_path as service


def run_test(client, seeded_db, headers, course_id, correct: bool):
    """Démarre puis soumet un test : toutes les réponses justes, ou toutes fausses."""
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


@pytest.fixture()
def course(seeded_db) -> Course:
    return seeded_db.scalar(select(Course).where(Course.code == "python-basics"))


def test_sans_test_termine_erreur(seeded_db, make_user):
    user, _ = make_user()
    with pytest.raises(service.NoCompletedTestError):
        service.build_learning_path(seeded_db, user.id)


def test_test_parfait_donne_un_parcours_vide(client, seeded_db, make_user, course):
    user, headers = make_user()
    run_test(client, seeded_db, headers, course.id, correct=True)
    path = service.build_learning_path(seeded_db, user.id)
    assert path.steps == []


def test_test_rate_donne_une_etape_par_competence_dans_l_ordre(client, seeded_db, make_user, course):
    user, headers = make_user()
    run_test(client, seeded_db, headers, course.id, correct=False)
    path = service.build_learning_path(seeded_db, user.id)

    assert [s.skill_id for s in path.steps] == [s.id for s in course.skills]
    assert [s.position for s in path.steps] == list(range(1, len(course.skills) + 1))
    assert all(s.status == StepStatus.TODO for s in path.steps)
    assert all(s.mastery_at_creation.value == "gap" for s in path.steps)
    assert all(s.objective for s in path.steps)


def test_reconstruire_archive_l_ancien_parcours(client, seeded_db, make_user, course):
    user, headers = make_user()
    run_test(client, seeded_db, headers, course.id, correct=False)
    first = service.build_learning_path(seeded_db, user.id)
    second = service.build_learning_path(seeded_db, user.id)

    seeded_db.expire_all()
    paths = seeded_db.scalars(select(LearningPath).where(LearningPath.user_id == user.id)).all()
    assert len(paths) == 2
    assert [p.id for p in paths if p.status == PathStatus.ACTIVE] == [second.id]
    assert [p.id for p in paths if p.status == PathStatus.ARCHIVED] == [first.id]


def test_parcours_global_sur_plusieurs_cours(client, seeded_db, make_user):
    courses = [c for c in seeded_db.scalars(select(Course).order_by(Course.id)) if c.is_active and c.skills]
    if len(courses) < 2:
        pytest.skip("Le catalogue de test contient moins de 2 cours.")
    user, headers = make_user()
    for c in courses[:2]:
        run_test(client, seeded_db, headers, c.id, correct=False)

    path = service.build_learning_path(seeded_db, user.id)
    assert len(path.steps) == sum(len(c.skills) for c in courses[:2])
    assert [s.course_id for s in path.steps][0] == courses[0].id  # cours dans l'ordre


def test_un_etudiant_n_a_pas_le_parcours_d_un_autre(client, seeded_db, make_user, course):
    a, headers_a = make_user("a@example.com")
    b, _ = make_user("b@example.com")
    run_test(client, seeded_db, headers_a, course.id, correct=False)
    service.build_learning_path(seeded_db, a.id)
    assert service.get_active_path(seeded_db, b.id) is None