from pydantic import BaseModel, Field, field_validator

from app.schemas.base import ORMModel


class DomainOut(ORMModel):
    id: int
    code: str
    name: str
    description: str | None = None
    icon: str


class InterestsUpdate(BaseModel):
    """PUT /me/interests : la liste complète des domaines choisis (elle remplace la précédente)."""

    domain_ids: list[int] = Field(min_length=1, max_length=10)

    @field_validator("domain_ids")
    @classmethod
    def no_duplicates(cls, ids: list[int]) -> list[int]:
        if len(ids) != len(set(ids)):
            raise ValueError("Un domaine ne peut être choisi qu'une seule fois.")
        return ids
