import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """Données reçues à l'inscription."""

    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr  # vérifie que l'email est valide
    password: str = Field(min_length=8, max_length=72)

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Le nom doit contenir au moins 2 caractères.")
        return v

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.lower()  # "Ali@Mail.com" et "ali@mail.com" = même compte

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("Le mot de passe doit contenir au moins une lettre et un chiffre.")
        if len(v.encode("utf-8")) > 72:  # limite technique de bcrypt
            raise ValueError("Le mot de passe est trop long.")
        return v


class UserOut(BaseModel):
    """Données renvoyées au client (jamais le mot de passe !)."""

    id: int
    full_name: str
    email: EmailStr
    role: str
    created_at: datetime


class RegisterResponse(BaseModel):
    message: str
    user: UserOut