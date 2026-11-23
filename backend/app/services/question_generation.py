"""
Alimentation de la banque de questions par le LLM.

Principe « banque d'abord » : les tests sont toujours construits à partir de la banque.
Quand une compétence n'a pas assez de questions, on demande au LLM de compléter la banque UNE fois ;
les étudiants suivants réutilisent ces questions (rapide, économique, résultats comparables).
Si le LLM échoue, rien n'est perdu : on continue avec ce que la banque contient déjà.
"""

import logging
from collections import defaultdict
from typing import Callable

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import BankQuestion, Course, Difficulty, QuestionSource, ReviewStatus
from app.schemas.question_bank import QuestionDraft
from app.services.llm import Job
from app.services.question_bank import add_questions

logger = logging.getLogger(__name__)

# Taille visée de la banque PAR COMPÉTENCE (le test en pioche 4 : 1 facile, 2 moyennes, 1 difficile).
# Deux fois plus que nécessaire, pour que deux tentatives successives ne se ressemblent pas.
BANK_TARGET_PER_DIFFICULTY: dict[int, int] = {
    Difficulty.EASY: 2,
    Difficulty.MEDIUM: 4,
    Difficulty.HARD: 2,
}

# (nom du cours, travaux) → {skill_id: questions}. Implémenté par llm.generate_many.
Generator = Callable[[str, list[Job]], dict[int, list[QuestionDraft]]]


def missing_questions(db: Session, course: Course) -> list[Job]:
    """Pour chaque compétence du cours : combien de questions manquent, par difficulté."""
    rows = db.execute(
        select(BankQuestion.skill_id, BankQuestion.difficulty, func.count())
        .where(
            BankQuestion.skill_id.in_([skill.id for skill in course.skills]),
            BankQuestion.review_status == ReviewStatus.APPROVED,
        )
        .group_by(BankQuestion.skill_id, BankQuestion.difficulty)
    ).all()
    have: dict[tuple[int, int], int] = defaultdict(int)
    for skill_id, difficulty, count in rows:
        have[(skill_id, difficulty)] = count

    jobs: list[Job] = []
    for skill in course.skills:
        missing = {
            int(difficulty): target - have[(skill.id, int(difficulty))]
            for difficulty, target in BANK_TARGET_PER_DIFFICULTY.items()
            if have[(skill.id, int(difficulty))] < target
        }
        if missing:
            jobs.append((skill.id, skill.name, missing))
    return jobs


def top_up_bank(db: Session, course: Course, generate: Generator) -> int:
    """Complète la banque du cours avec le LLM. Renvoie le nombre de questions ajoutées."""
    jobs = missing_questions(db, course)
    if not jobs:
        return 0

    results = generate(course.title, jobs)
    skills = {skill.id: skill for skill in course.skills}
    added = sum(
        add_questions(
            db,
            skills[skill_id],
            drafts,
            source=QuestionSource.LLM,
            review_status=ReviewStatus.APPROVED,
        )
        for skill_id, drafts in results.items()
    )
    if added:
        try:
            db.commit()
            logger.info("Banque du cours « %s » complétée : %d question(s) ajoutée(s).", course.code, added)
        except IntegrityError:  # deux étudiants ont déclenché la génération en même temps
            db.rollback()
            return 0
    return added
