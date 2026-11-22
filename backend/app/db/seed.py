"""Données initiales du catalogue (cours et compétences). Idempotent : relançable sans doublon."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Course, Skill

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