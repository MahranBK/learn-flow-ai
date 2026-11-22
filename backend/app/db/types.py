import enum

from sqlalchemy import Enum


def enum_type(enum_cls: type[enum.Enum], *, length: int = 20) -> Enum:
    """
    Type de colonne pour un Enum Python, stocké en VARCHAR (pas d'enum natif PostgreSQL).

    - native_enum=False : ajouter une valeur plus tard ne demande pas de migration
      (important : le projet n'utilise pas Alembic).
    - values_callable : on stocke la valeur ("in_progress") et non le nom ("IN_PROGRESS"),
      ce qui rend la base lisible et les requêtes SQL simples.
    """
    return Enum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=lambda members: [member.value for member in members],
    )