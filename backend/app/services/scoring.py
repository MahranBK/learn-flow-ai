"""
Calcul du score et du niveau d'un test de positionnement.

Module volontairement « pur » : aucune base de données, aucun FastAPI, aucune horloge.
Il reçoit des résultats par question et renvoie des résultats chiffrés, ce qui le rend
facile à tester et à faire évoluer (tout changement de règle = changer SCORING_VERSION).

Règles (voir la proposition d'architecture, §7) :
- chaque question pèse selon sa difficulté (facile 1, moyenne 2, difficile 3) ;
- une question sans réponse vaut 0 mais reste dans le total (sauter une question
  difficile ne doit pas faire monter le score) ;
- score = 100 × points obtenus / points possibles, arrondi à 0,1 ;
- les mêmes seuils servent au niveau global et à la maîtrise par compétence.
"""

from collections import defaultdict
from dataclasses import dataclass

from app.models.placement import MasteryLevel, PlacementLevel

SCORING_VERSION = "v1"

# Pondération par difficulté : réussir une question difficile apporte plus de preuve.
DIFFICULTY_WEIGHTS: dict[int, int] = {1: 1, 2: 2, 3: 3}

# Seuils provisoires, à recalibrer après un pilote avec de vraies données.
# 40 % : au-dessus du hasard (25 % avec 4 options). 70 % : convention de « maîtrise ».
LOW_THRESHOLD = 40.0
HIGH_THRESHOLD = 70.0

# En dessous de ce nombre de questions, une compétence n'est pas évaluée (pas de fausse lacune).
MIN_QUESTIONS_PER_SKILL = 3

# Au-delà de cette part de questions sans réponse, le résultat est marqué « non fiable ».
MAX_UNANSWERED_RATIO = 0.5


@dataclass(frozen=True)
class QuestionOutcome:
    """Résultat d'une question, indépendamment de la base de données."""

    skill_id: int
    difficulty: int
    answered: bool
    correct: bool

    def __post_init__(self) -> None:
        if self.difficulty not in DIFFICULTY_WEIGHTS:
            raise ValueError(f"Difficulté invalide : {self.difficulty}.")
        if self.correct and not self.answered:
            raise ValueError("Une question sans réponse ne peut pas être correcte.")

    @property
    def weight(self) -> int:
        return DIFFICULTY_WEIGHTS[self.difficulty]


@dataclass(frozen=True)
class SkillScore:
    skill_id: int
    score: float
    n_questions: int
    n_correct: int
    n_unanswered: int
    mastery: MasteryLevel


@dataclass(frozen=True)
class ScoringResult:
    score: float
    level: PlacementLevel
    correct_count: int
    total_questions: int
    unanswered_count: int
    reliable: bool
    skills: list[SkillScore]


def grade_answer(user_answer: str | None, correct_answer: str) -> bool:
    """Une réponse est correcte si elle est identique à la bonne option (pas de réponse = faux)."""
    return user_answer is not None and user_answer == correct_answer


def weighted_score(outcomes: list[QuestionOutcome]) -> float:
    """Pourcentage de points obtenus (0-100, arrondi à 0,1)."""
    if not outcomes:
        raise ValueError("Aucune question à corriger.")
    possible = sum(o.weight for o in outcomes)
    obtained = sum(o.weight for o in outcomes if o.correct)
    return round(100 * obtained / possible, 1)


def level_from_score(score: float) -> PlacementLevel:
    if score >= HIGH_THRESHOLD:
        return PlacementLevel.ADVANCED
    if score >= LOW_THRESHOLD:
        return PlacementLevel.INTERMEDIATE
    return PlacementLevel.BEGINNER


def mastery_from_score(score: float, n_questions: int) -> MasteryLevel:
    if n_questions < MIN_QUESTIONS_PER_SKILL:
        return MasteryLevel.INSUFFICIENT_DATA
    if score >= HIGH_THRESHOLD:
        return MasteryLevel.MASTERED
    if score >= LOW_THRESHOLD:
        return MasteryLevel.PARTIAL
    return MasteryLevel.GAP

def is_reliable(unanswered_count: int, total_questions: int) -> bool:
    """Un résultat est fiable si au plus la moitié des questions sont restées sans réponse."""
    return total_questions > 0 and unanswered_count / total_questions <= MAX_UNANSWERED_RATIO

def compute_result(outcomes: list[QuestionOutcome]) -> ScoringResult:
    """Calcule le score global, le niveau et le détail par compétence."""
    if not outcomes:
        raise ValueError("Aucune question à corriger.")

    by_skill: dict[int, list[QuestionOutcome]] = defaultdict(list)
    for outcome in outcomes:
        by_skill[outcome.skill_id].append(outcome)

    skills = []
    for skill_id in sorted(by_skill):  # ordre stable
        items = by_skill[skill_id]
        score = weighted_score(items)
        skills.append(
            SkillScore(
                skill_id=skill_id,
                score=score,
                n_questions=len(items),
                n_correct=sum(o.correct for o in items),
                n_unanswered=sum(not o.answered for o in items),
                mastery=mastery_from_score(score, len(items)),
            )
        )

    global_score = weighted_score(outcomes)
    unanswered = sum(not o.answered for o in outcomes)
    return ScoringResult(
        score=global_score,
        level=level_from_score(global_score),
        correct_count=sum(o.correct for o in outcomes),
        total_questions=len(outcomes),
        unanswered_count=unanswered,
        reliable=is_reliable(unanswered, len(outcomes)),
        skills=skills,
    )