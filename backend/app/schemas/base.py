from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    """Base des schémas construits à partir d'objets SQLAlchemy (from_attributes)."""

    model_config = ConfigDict(from_attributes=True)