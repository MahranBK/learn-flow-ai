import random
from dataclasses import dataclass

from app.services.placement import pick_questions

BLUEPRINT = {1: 1, 2: 2, 3: 1}  # 1 facile, 2 moyennes, 1 difficile


@dataclass(frozen=True)
class Q:
    id: int
    difficulty: int


def bank(*difficulties: int) -> list[Q]:
    return [Q(id=i, difficulty=d) for i, d in enumerate(difficulties, start=1)]


def rng() -> random.Random:
    return random.Random(42)  # résultat reproductible


def test_respecte_la_composition_demandee():
    picked = pick_questions(bank(1, 1, 2, 2, 2, 3, 3), BLUEPRINT, set(), rng())
    assert sorted(q.difficulty for q in picked) == [1, 2, 2, 3]


def test_jamais_deux_fois_la_meme_question():
    picked = pick_questions(bank(2, 2, 2, 2, 2, 2), BLUEPRINT, set(), rng())
    assert len({q.id for q in picked}) == len(picked)


def test_prefere_les_questions_jamais_vues():
    candidates = bank(1, 1, 2, 2, 2, 2, 3, 3)
    seen = {1, 3, 4, 7}  # une facile, deux moyennes, une difficile déjà vues
    picked = pick_questions(candidates, BLUEPRINT, seen, rng())
    assert not ({q.id for q in picked} & seen)


def test_utilise_la_difficulte_la_plus_proche_si_il_en_manque():
    # aucune question difficile : la place « difficile » est prise par une moyenne
    picked = pick_questions(bank(1, 2, 2, 2), BLUEPRINT, set(), rng())
    assert sorted(q.difficulty for q in picked) == [1, 2, 2, 2]


def test_reprend_des_questions_deja_vues_si_la_banque_est_epuisee():
    candidates = bank(1, 2, 2, 3)
    picked = pick_questions(candidates, BLUEPRINT, {1, 2, 3, 4}, rng())
    assert len(picked) == 4


def test_mieux_vaut_une_question_vue_qu_aucune_mais_les_neuves_passent_d_abord():
    candidates = bank(1, 2, 2, 3, 2)
    picked = pick_questions(candidates, BLUEPRINT, {1, 2}, rng())  # 3 neuves, 2 vues
    assert len(picked) == 4
    assert {3, 4, 5} <= {q.id for q in picked}  # toutes les neuves sont prises


def test_renvoie_moins_de_questions_si_la_banque_est_trop_petite():
    assert len(pick_questions(bank(1, 2), BLUEPRINT, set(), rng())) == 2
    assert pick_questions([], BLUEPRINT, set(), rng()) == []