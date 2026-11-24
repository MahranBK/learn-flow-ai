import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://admin:adminpassword@localhost:5432/learnflow_db"
)

# JWT (utilisé à partir de T5)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


# Test de positionnement : délai (en jours) avant de pouvoir repasser un test terminé (0 = aucun)
PLACEMENT_RETAKE_COOLDOWN_DAYS = int(os.getenv("PLACEMENT_RETAKE_COOLDOWN_DAYS", "7"))

# --- LLM (génération des questions) -----------------------------------------------------------
# Toute API « compatible OpenAI » convient (Google Gemini, OpenAI, Groq…). Sans clé, aucun appel
# n'est fait : les tests utilisent uniquement la banque de questions déjà enregistrées.
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_URL = os.getenv(
    "LLM_API_URL", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
)
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.8-flash")
# Modèle essayé si le principal est indisponible (optionnel, ex. un modèle « flash-lite »).
LLM_FALLBACK_MODEL = os.getenv("LLM_FALLBACK_MODEL", "")
# « none » / « low » pour les modèles qui réfléchissent (plus rapide). Vide = paramètre non envoyé.
LLM_REASONING_EFFORT = os.getenv("LLM_REASONING_EFFORT", "low")
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "45"))
