import json
from collections import Counter

import pytest
from sqlalchemy import func, select

from app.db.seed import BANK_FILE, seed_catalog, seed_question_bank
from app.models import BankQuestion, ReviewStatus, Skill
from app.services.question_bank import compute_content_hash

OPTIONS = ["3", "4", "5", "6"]


# --- empreinte anti-doublon -----------------------------------------------------------------


def test_hash_ignore_casse_espaces_et_ordre_des_options():
    a = compute_content_hash("Que renvoie 2 + 2 ?", OPTIONS)
    b = compute_content_hash("  que renvoie   2 + 2 ?", ["6", "5", "4 ", "3"])
    assert a == b


def test_hash_different_si_la_question_change():
    assert compute_content_hash("Que renvoie 2 + 2 ?", OPTIONS) != compute_content_hash(
        "Que renvoie 2 + 3 ?", OPTIONS
    )


# --- chargement de la banque de secours -----------------------------------------------------


def test_chargement_et_idempotence(db):
    seed_catalog(db)
    added = seed_question_bank(db)
    db.commit()
    assert added > 0
    assert db.scalar(select(func.count(BankQuestion.id))) == added

    # deuxième chargement : rien n'est ajouté
    assert seed_question_bank(db) == 0
    assert db.scalar(select(func.count(BankQuestion.id))) == added


def test_la_banque_de_secours_permet_de_composer_un_test(db):
    """Chaque compétence doit avoir de quoi former 1 facile + 2 moyennes + 1 difficile."""
    seed_catalog(db)
    seed_question_bank(db)
    db.commit()

    for skill in db.scalars(select(Skill)):
        approved = db.scalars(
            select(BankQuestion.difficulty).where(
                BankQuestion.skill_id == skill.id,
                BankQuestion.review_status == ReviewStatus.APPROVED,
            )
        ).all()
        counts = Counter(approved)
        assert counts[1] >= 1 and counts[2] >= 2 and counts[3] >= 1, f"{skill.code}: {counts}"


def test_fichier_sans_doublon_interne():
    questions = json.loads(BANK_FILE.read_text(encoding="utf-8"))
    hashes = [compute_content_hash(q["question"], q["options"]) for q in questions]
    assert len(hashes) == len(set(hashes))


def test_question_invalide_fait_echouer_le_chargement(db, tmp_path):
    seed_catalog(db)
    bad = [{"course": "python-basics", "skill": "loops", "difficulty": 1,
            "question": "Une question à trois options seulement ?", "options": ["a", "b", "c"],
            "correct_answer": "a"}]
    path = tmp_path / "bank.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="question n°1 invalide"):
        seed_question_bank(db, path)


def test_competence_inconnue_fait_echouer_le_chargement(db, tmp_path):
    seed_catalog(db)
    bad = [{"course": "python-basics", "skill": "inconnue", "difficulty": 1,
            "question": "Une question quelconque ici ?", "options": ["a", "b", "c", "d"],
            "correct_answer": "a"}]
    path = tmp_path / "bank.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="compétence inconnue"):
        seed_question_bank(db, path)



def test_chaque_cours_du_catalogue_a_une_banque_suffisante(db):
    """Un cours sans assez de questions ferait échouer « Commencer le test » (503)."""
    from app.models import Course

    seed_catalog(db)
    seed_question_bank(db)
    db.commit()

    for course in db.scalars(select(Course)):
        assert len(course.skills) >= 4, f"{course.code} : moins de 4 compétences"
        for skill in course.skills:
            counts = Counter(
                db.scalars(
                    select(BankQuestion.difficulty).where(
                        BankQuestion.skill_id == skill.id,
                        BankQuestion.review_status == ReviewStatus.APPROVED,
                    )
                ).all()
            )
            assert counts[1] >= 2 and counts[2] >= 3 and counts[3] >= 2, f"{course.code}/{skill.code}: {dict(counts)}"