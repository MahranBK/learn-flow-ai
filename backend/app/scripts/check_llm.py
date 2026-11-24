"""
Vérifie la connexion au LLM :  docker exec learnflow_api python -m app.scripts.check_llm
Affiche la configuration utilisée, puis génère 2 questions d'essai (ou l'erreur exacte du service).
"""

from app.core.config import LLM_API_URL, LLM_FALLBACK_MODEL, LLM_MODEL, LLM_REASONING_EFFORT
from app.services import llm


def main() -> None:
    print(f"URL     : {LLM_API_URL}")
    print(f"Modèle  : {LLM_MODEL}  (reasoning_effort={LLM_REASONING_EFFORT or 'non envoyé'})")
    print(f"Secours : {LLM_FALLBACK_MODEL or 'aucun'}")
    if not llm.is_enabled():
        print("❌ LLM_API_KEY est vide : voir .env et docker-compose.yml, puis `docker compose up`.")
        return
    try:
        drafts = llm.generate_for_skill("Bases de Python", "Boucles", {1: 1, 2: 1})
    except llm.LLMError as exc:
        print(f"❌ Échec : {exc}")
        return
    print(f"✅ Connexion OK : {len(drafts)} question(s) valide(s) reçue(s).\n")
    for draft in drafts:
        print(f"[difficulté {int(draft.difficulty)}] {draft.question}")
        for option in draft.options:
            print(f"   {'✔' if option == draft.correct_answer else '·'} {option}")
        print()


if __name__ == "__main__":
    main()
