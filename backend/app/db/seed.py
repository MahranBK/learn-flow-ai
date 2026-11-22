"""Données initiales du catalogue (cours et compétences). Idempotent : relançable sans doublon."""


import json
from collections import defaultdict
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Course, QuestionSource, ReviewStatus, Skill
from app.schemas.question_bank import SeedQuestion
from app.services.question_bank import add_questions

# Banque de secours : questions rédigées et relues par l'équipe (versionnée dans Git)
BANK_FILE = Path(__file__).resolve().parent.parent / "data" / "question_bank.json"


# Pour ajouter un cours ou une compétence : ajouter une entrée ici (puis redémarrer le backend).
CATALOG: list[dict] = [
    {
        "code": "python-basics",
        "title": "Bases de Python",
        "description": "Test de positionnement sur les fondamentaux de la programmation en Python.",
        "skills": [
            {"code": "variables-types", "name": "Variables et types de données"},
            {"code": "conditions", "name": "Structures conditionnelles"},
            {"code": "loops", "name": "Boucles"},
            {"code": "functions", "name": "Fonctions"},
        ],
    },
]


def seed_catalog(db: Session) -> None:
    """Crée les cours et compétences manquants. Ne modifie jamais ceux qui existent déjà."""
    for course_data in CATALOG:
        course = db.scalar(select(Course).where(Course.code == course_data["code"]))
        if course is None:
            course = Course(
                code=course_data["code"],
                title=course_data["title"],
                description=course_data["description"],
            )
            db.add(course)
            db.flush()  # obtient course.id

        existing_codes = set(
            db.scalars(select(Skill.code).where(Skill.course_id == course.id)).all()
        )
        for skill_data in course_data["skills"]:
            if skill_data["code"] not in existing_codes:
                db.add(Skill(course_id=course.id, code=skill_data["code"], name=skill_data["name"]))
    


def seed_question_bank(db: Session, path: Path = BANK_FILE) -> int:
    """
    Charge la banque de secours (questions validées par l'équipe). Idempotent.
    Une question invalide fait échouer le démarrage avec un message clair : on ne « répare » pas.
    Renvoie le nombre de questions ajoutées.
    """
    db.flush()  # les cours et compétences créés juste avant doivent avoir un id
    skills = {
        (course.code, skill.code): skill
        for course in db.scalars(select(Course))
        for skill in course.skills
    }

    raw_questions = json.loads(path.read_text(encoding="utf-8"))
    by_skill: dict[tuple[str, str], list[SeedQuestion]] = defaultdict(list)
    for number, raw in enumerate(raw_questions, start=1):
        try:
            question = SeedQuestion.model_validate(raw)
        except ValidationError as exc:
            raise ValueError(f"{path.name}, question n°{number} invalide :\n{exc}") from exc
        key = (question.course, question.skill)
        if key not in skills:
            raise ValueError(f"{path.name}, question n°{number} : compétence inconnue {key}.")
        by_skill[key].append(question)

    return sum(
        add_questions(
            db,
            skills[key],
            drafts,
            source=QuestionSource.MANUAL,
            review_status=ReviewStatus.APPROVED,
        )
        for key, drafts in by_skill.items()
    )