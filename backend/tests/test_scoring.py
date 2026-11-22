import pytest

from app.models.placement import MasteryLevel, PlacementLevel
from app.services.scoring import (
    QuestionOutcome,
    compute_result,
    grade_answer,
    level_from_score,
    mastery_from_score,
    weighted_score,
)


def q(skill_id=1, difficulty=1, answered=True, correct=True) -> QuestionOutcome:
    """Raccourci pour fabriquer un résultat de question."""
    return QuestionOutcome(skill_id, difficulty, answered, correct and answered)


# --- grade_answer ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("user_answer", "correct_answer", "expected"),
    [("4", "4", True), ("3", "4", False), (None, "4", False), ("", "4", False), ("4 ", "4", False)],
)
def test_grade_answer(user_answer, correct_answer, expected):
    assert grade_answer(user_answer, correct_answer) is expected


# --- weighted_score -------------------------------------------------------------------------


def test_tout_juste_donne_100():
    assert weighted_score([q(difficulty=1), q(difficulty=2), q(difficulty=3)]) == 100.0


def test_tout_faux_donne_0():
    assert weighted_score([q(correct=False), q(correct=False)]) == 0.0


def test_la_difficulte_pese_dans_le_score():
    # facile réussie (1 pt) + difficile ratée (3 pts) → 1/4 = 25 %
    assert weighted_score([q(difficulty=1), q(difficulty=3, correct=False)]) == 25.0
    # facile ratée + difficile réussie → 3/4 = 75 %
    assert weighted_score([q(difficulty=1, correct=False), q(difficulty=3)]) == 75.0


def test_question_sans_reponse_compte_comme_fausse_dans_le_total():
    # 1 juste + 1 sans réponse, même difficulté → 50 % (et non 100 %)
    assert weighted_score([q(), q(answered=False)]) == 50.0


def test_score_arrondi_a_un_chiffre():
    assert weighted_score([q(), q(correct=False), q(correct=False)]) == 33.3


def test_liste_vide_refusee():
    with pytest.raises(ValueError):
        weighted_score([])
    with pytest.raises(ValueError):
        compute_result([])


# --- seuils ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("score", "level"),
    [
        (0, PlacementLevel.BEGINNER),
        (39.9, PlacementLevel.BEGINNER),
        (40.0, PlacementLevel.INTERMEDIATE),
        (69.9, PlacementLevel.INTERMEDIATE),
        (70.0, PlacementLevel.ADVANCED),
        (100, PlacementLevel.ADVANCED),
    ],
)
def test_niveau_selon_le_score(score, level):
    assert level_from_score(score) == level


@pytest.mark.parametrize(
    ("score", "n_questions", "mastery"),
    [
        (10, 4, MasteryLevel.GAP),
        (55, 4, MasteryLevel.PARTIAL),
        (85, 4, MasteryLevel.MASTERED),
        (100, 2, MasteryLevel.INSUFFICIENT_DATA),  # trop peu de questions pour conclure
        (0, 2, MasteryLevel.INSUFFICIENT_DATA),  # pas de fausse lacune
    ],
)
def test_maitrise_selon_le_score(score, n_questions, mastery):
    assert mastery_from_score(score, n_questions) == mastery


# --- compute_result -------------------------------------------------------------------------


def test_resultat_complet_par_competence():
    outcomes = [
        # compétence 1 : 4 questions, tout juste → maîtrisée
        *[q(skill_id=1, difficulty=d) for d in (1, 2, 2, 3)],
        # compétence 2 : 4 questions, tout faux → lacune
        *[q(skill_id=2, difficulty=d, correct=False) for d in (1, 2, 2, 3)],
    ]
    result = compute_result(outcomes)

    assert result.score == 50.0
    assert result.level == PlacementLevel.INTERMEDIATE
    assert (result.correct_count, result.total_questions, result.unanswered_count) == (4, 8, 0)
    assert result.reliable is True
    assert [s.skill_id for s in result.skills] == [1, 2]
    assert (result.skills[0].score, result.skills[0].mastery) == (100.0, MasteryLevel.MASTERED)
    assert (result.skills[1].score, result.skills[1].mastery) == (0.0, MasteryLevel.GAP)


def test_non_repondues_comptees_par_competence():
    result = compute_result([q(answered=False), q(answered=False), q()])
    assert result.unanswered_count == 2
    assert result.skills[0].n_unanswered == 2
    assert result.skills[0].n_correct == 1


def test_resultat_non_fiable_si_plus_de_la_moitie_sans_reponse():
    assert compute_result([q(answered=False), q(answered=False), q()]).reliable is False


def test_resultat_fiable_a_exactement_la_moitie():
    assert compute_result([q(answered=False), q()]).reliable is True


def test_resultat_independant_de_l_ordre_des_questions():
    outcomes = [q(skill_id=2), q(skill_id=1, correct=False), q(skill_id=1), q(skill_id=2, difficulty=3)]
    assert compute_result(outcomes) == compute_result(list(reversed(outcomes)))


def test_donnees_incoherentes_refusees():
    with pytest.raises(ValueError):
        QuestionOutcome(1, 5, True, True)  # difficulté inconnue
    with pytest.raises(ValueError):
        QuestionOutcome(1, 1, False, True)  # correcte sans avoir répondu


# --- is_reliable ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("unanswered", "total", "expected"),
    [(0, 16, True), (8, 16, True), (9, 16, False), (16, 16, False), (0, 0, False)],
)
def test_is_reliable(unanswered, total, expected):
    from app.services.scoring import is_reliable

    assert is_reliable(unanswered, total) is expected