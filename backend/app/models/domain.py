from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.user import utcnow

if TYPE_CHECKING:
    from app.models.course import Course

# Table d'association : les domaines qui intéressent un étudiant (relation plusieurs-à-plusieurs).
user_interests = Table(
    "user_interests",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("domain_id", ForeignKey("domains.id", ondelete="CASCADE"), primary_key=True),
)


class Domain(Base):
    """Domaine d'apprentissage (ex. « Développement web », « Intelligence artificielle »)."""

    __tablename__ = "domains"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)  # ex. "web-dev"
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str] = mapped_column(String(30), default="book")  # clé d'icône choisie par le frontend
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    courses: Mapped[list["Course"]] = relationship(back_populates="domain", order_by="Course.title")
