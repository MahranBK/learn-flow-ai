"""
Appel au LLM et validation de sa réponse (aucun accès à la base de données).

Le LLM n'est qu'une SOURCE de brouillons : chaque question qu'il renvoie est validée par
QuestionDraft (JSON strict, 4 options distinctes, bonne réponse parmi les options…). Ce qui est
invalide est écarté. En cas d'échec (clé absente, timeout, réponse illisible), on renvoie un
résultat vide : l'appelant continue avec la banque de secours.
"""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
from pydantic import ValidationError

from app.core.config import (
    LLM_API_KEY,
    LLM_API_URL,
    LLM_FALLBACK_MODEL,
    LLM_MODEL,
    LLM_REASONING_EFFORT,
    LLM_TIMEOUT_SECONDS,
)
from app.schemas.question_bank import QuestionDraft

logger = logging.getLogger(__name__)

# (skill_id, nom de la compétence, questions voulues par difficulté)
Job = tuple[int, str, dict[int, int]]

DIFFICULTY_GUIDE = {
    1: "facile : reconnaître une définition ou une syntaxe de base",
    2: "moyenne : appliquer une notion à un petit cas concret",
    3: "difficile : analyser un extrait de code ou une situation, repérer une erreur ou prédire un résultat",
}


# Erreurs passagères du service (surcharge, limite de débit) : cela vaut la peine de réessayer.
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
# Clé refusée : inutile d'insister, ni de changer de modèle.
FATAL_STATUS = {401, 403}
MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2  # 2 s puis 4 s entre les tentatives


class LLMError(Exception):
    """Le LLM est indisponible ou sa réponse est inutilisable."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def is_enabled() -> bool:
    return bool(LLM_API_KEY)


def build_messages(course_title: str, skill_name: str, wanted: dict[int, int]) -> list[dict]:
    """Construit le prompt. wanted : difficulté (1-3) → nombre de questions voulues."""
    lines = "\n".join(
        f"- {count} question(s) de difficulté {difficulty} ({DIFFICULTY_GUIDE[difficulty]})"
        for difficulty, count in sorted(wanted.items())
        if count > 0
    )
    system = (
        "Tu es un enseignant expert qui rédige des questions à choix multiple, en français, pour un "
        "test de positionnement. Réponds UNIQUEMENT par un objet JSON, sans texte autour, de la forme :\n"
        '{"questions": [{"difficulty": 1, "question": "...", "options": ["A", "B", "C", "D"], '
        '"correct_answer": "...", "explanation": "..."}]}\n'
        "Règles impératives :\n"
        "- exactement 4 options, toutes différentes, plausibles et de longueur comparable ;\n"
        "- une seule bonne réponse, recopiée À L'IDENTIQUE dans correct_answer depuis options ;\n"
        "- la bonne réponse doit être vérifiable et sans ambiguïté ; pas de « toutes les réponses » ;\n"
        "- si la question contient du code : l'énoncé sur la 1re ligne, puis le code sur les lignes "
        "suivantes (retours à la ligne avec \\n, sans balises markdown) ;\n"
        "- explanation : une ou deux phrases qui justifient la bonne réponse ;\n"
        "- chaque question est indépendante des autres et porte uniquement sur la compétence indiquée."
    )
    user = f"Cours : {course_title}\nCompétence évaluée : {skill_name}\nRédige :\n{lines}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def parse_questions(raw: str) -> list[QuestionDraft]:
    """Transforme la réponse brute du LLM en questions valides (les invalides sont écartées)."""
    text = (raw or "").strip()
    if text.startswith("```"):  # certains modèles entourent le JSON de balises markdown
        text = text.strip("`").removeprefix("json").strip()
    try:
        data = json.loads(text)
    except (TypeError, json.JSONDecodeError) as exc:
        raise LLMError("JSON invalide.") from exc

    items = data.get("questions") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise LLMError("clé « questions » absente.")

    valid: list[QuestionDraft] = []
    for item in items:
        try:
            valid.append(QuestionDraft.model_validate(item))
        except ValidationError:
            logger.warning("Question du LLM rejetée (schéma non respecté).")
    return valid


def select_by_blueprint(drafts: list[QuestionDraft], wanted: dict[int, int]) -> list[QuestionDraft]:
    """Garde au plus `wanted[difficulté]` questions par difficulté, sans doublon d'énoncé."""
    remaining = dict(wanted)
    seen: set[str] = set()
    kept: list[QuestionDraft] = []
    for draft in drafts:
        key = " ".join(draft.question.casefold().split())
        if key in seen or remaining.get(int(draft.difficulty), 0) <= 0:
            continue
        seen.add(key)
        remaining[int(draft.difficulty)] -= 1
        kept.append(draft)
    return kept


def _post(model: str, messages: list[dict]) -> str:
    """Un appel HTTP (API compatible OpenAI). Lève LLMError avec un message utile en cas d'échec."""
    payload: dict = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "response_format": {"type": "json_object"},
    }
    if LLM_REASONING_EFFORT:
        payload["reasoning_effort"] = LLM_REASONING_EFFORT

    try:
        response = httpx.post(
            LLM_API_URL,
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json=payload,
            timeout=LLM_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        raise LLMError(f"HTTP {status} ({model}) : {exc.response.text[:300]}", status=status) from exc
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise LLMError(f"appel impossible ({model}, {exc.__class__.__name__}).") from exc


def _call_llm(messages: list[dict]) -> str:
    """
    Appelle le modèle principal en réessayant sur les erreurs passagères (503, 429…),
    puis le modèle de secours s'il est configuré. Une clé refusée (401/403) arrête tout.
    """
    last_error = LLMError("aucun modèle configuré.")
    for model in [m for m in (LLM_MODEL, LLM_FALLBACK_MODEL) if m]:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                return _post(model, messages)
            except LLMError as exc:
                last_error = exc
                if exc.status in FATAL_STATUS:
                    raise
                if exc.status not in RETRYABLE_STATUS:
                    break  # ex. modèle introuvable ou réponse illisible : on passe au modèle suivant
                if attempt < MAX_ATTEMPTS:
                    logger.info("LLM %s surchargé (%s), nouvel essai…", model, exc.status)
                    time.sleep(RETRY_DELAY_SECONDS * attempt)
    raise last_error


def generate_for_skill(course_title: str, skill_name: str, wanted: dict[int, int]) -> list[QuestionDraft]:
    raw = _call_llm(build_messages(course_title, skill_name, wanted))
    return select_by_blueprint(parse_questions(raw), wanted)


def generate_many(course_title: str, jobs: list[Job]) -> dict[int, list[QuestionDraft]]:
    """
    Génère les questions de plusieurs compétences EN PARALLÈLE (chaque appel prend des secondes).
    Renvoie {skill_id: questions valides}. Une compétence en échec est simplement absente.
    Sans clé API, renvoie {} sans aucun appel réseau.
    """
    if not jobs or not is_enabled():
        return {}

    def work(job: Job) -> tuple[int, list[QuestionDraft]]:
        skill_id, skill_name, wanted = job
        try:
            return skill_id, generate_for_skill(course_title, skill_name, wanted)
        except LLMError as exc:
            logger.warning("LLM : échec pour la compétence « %s » : %s", skill_name, exc)
            return skill_id, []

    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        return {skill_id: drafts for skill_id, drafts in pool.map(work, jobs) if drafts}
