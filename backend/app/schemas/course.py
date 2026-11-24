from app.schemas.base import ORMModel
from app.schemas.domain import DomainOut


class SkillOut(ORMModel):
    id: int
    code: str
    name: str


class CourseOut(ORMModel):
    id: int
    domain_id: int
    code: str
    title: str
    description: str | None = None


class CourseListItem(CourseOut):
    """Cours tel qu'affiché dans le catalogue : avec son domaine et ses compétences."""

    domain: DomainOut
    skills: list[SkillOut]
