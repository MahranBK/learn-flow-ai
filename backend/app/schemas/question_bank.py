from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.question_bank import Difficulty

OPTIONS_COUNT = 4


class QuestionDraft(BaseModel):
    """
    Contenu d'une question à valider avant d'entrer dans la banque.
    Sert à vérifier TOUTE question venant d'ailleurs : sortie du LLM (T9) ou fichier de secours.
    Une question qui ne respecte pas ce schéma est rejetée, jamais « réparée ».
    """

    difficulty: Difficulty
    question: str = Field(min_length=10, max_length=1000)
    options: list[str] = Field(min_length=OPTIONS_COUNT, max_length=OPTIONS_COUNT)
    correct_answer: str = Field(min_length=1, max_length=255)
    explanation: str | None = Field(default=None, max_length=1000)

    @field_validator("question", "correct_answer")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip()

    @field_validator("options")
    @classmethod
    def clean_options(cls, options: list[str]) -> list[str]:
        cleaned = [option.strip() for option in options]
        if any(not option or len(option) > 255 for option in cleaned):
            raise ValueError("Chaque option doit contenir entre 1 et 255 caractères.")
        if len({option.casefold() for option in cleaned}) != len(cleaned):
            raise ValueError("Les options doivent être toutes différentes.")
        return cleaned

    @model_validator(mode="after")
    def answer_in_options(self) -> "QuestionDraft":
        if self.correct_answer not in self.options:
            raise ValueError("La bonne réponse doit faire partie des options.")
        return self

        

class SeedQuestion(QuestionDraft):
    """Question du fichier de secours : une QuestionDraft + le cours et la compétence visés."""

    course: str = Field(min_length=1, max_length=50)  # code du cours, ex. "python-basics"
    skill: str = Field(min_length=1, max_length=50)  # code de la compétence, ex. "loops"