"""Gestion de la banque de questions : empreinte anti-doublon et ajout de questions validées."""

import hashlib
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BankQuestion, QuestionSource, ReviewStatus, Skill
from app.schemas.question_bank import QuestionDraft


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def compute_content_hash(question: str, options: list[str]) -> str:
    """
    Empreinte d'une question : identique si le texte et l'ensemble des options sont les mêmes,
    quels que soient la casse, les espaces ou l'ordre des options.
    """
    payload = "\n".join([_normalize(question), *sorted(_normalize(o) for o in options)])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def add_questions(
    db: Session,
    skill: Skill,
    drafts: list[QuestionDraft],
    *,
    source: QuestionSource,
    review_status: ReviewStatus,
) -> int:
    """
    Ajoute à la banque les questions qui n'y sont pas déjà (clé : content_hash).
    Ne fait pas de commit. Renvoie le nombre de questions ajoutées.
    """
    known_hashes = set(db.scalars(select(BankQuestion.content_hash)).all())
    added = 0
    for draft in drafts:
        content_hash = compute_content_hash(draft.question, draft.options)
        if content_hash in known_hashes:
            continue
        db.add(
            BankQuestion(
                skill_id=skill.id,
                difficulty=draft.difficulty,
                question=draft.question,
                options=draft.options,
                correct_answer=draft.correct_answer,
                explanation=draft.explanation,
                source=source,
                review_status=review_status,
                content_hash=content_hash,
            )
        )
        known_hashes.add(content_hash)
        added += 1
    return added