"""Domaines d'intérêt d'un étudiant (choisis à l'onboarding, modifiables ensuite)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Domain, User


class InvalidDomainsError(Exception):
    """Un ou plusieurs domaines demandés n'existent pas (ou ne sont plus actifs)."""


def list_active_domains(db: Session) -> list[Domain]:
    return list(db.scalars(select(Domain).where(Domain.is_active.is_(True)).order_by(Domain.name)))


def set_interests(db: Session, user: User, domain_ids: list[int]) -> list[Domain]:
    """Remplace les centres d'intérêt de l'étudiant par les domaines demandés."""
    domains = list(
        db.scalars(select(Domain).where(Domain.id.in_(domain_ids), Domain.is_active.is_(True)))
    )
    if len(domains) != len(set(domain_ids)):
        raise InvalidDomainsError("Un ou plusieurs domaines choisis n'existent pas.")

    user.interests = sorted(domains, key=lambda d: d.name)
    db.commit()
    return user.interests
