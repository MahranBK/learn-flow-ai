from app.schemas.base import ORMModel


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