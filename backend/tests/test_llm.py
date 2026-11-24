"""Génération par LLM : validation de la sortie, complément de la banque, repli sans LLM."""

import json

import httpx
import pytest
from sqlalchemy import func, select

from app.models import (
    BankQuestion,
    Course,
    Domain,
    GenerationSource,
    QuestionSource,
    ReviewStatus,
    Skill,
)
from app.schemas.question_bank import QuestionDraft
from app.services import llm
from app.services import placement as placement_service
from app.services.question_generation import BANK_TARGET_PER_DIFFICULTY, missing_questions, top_up_bank


def good(question="Quel est le type de la valeur 3.14 ?", difficulty=1):
    return {
        "difficulty": difficulty,
        "question": question,
        "options": ["int", "float", "str", "bool"],
        "correct_answer": "float",
        "explanation": "Un nombre décimal est un float.",
    }


# --- validation de la sortie du LLM (fonctions pures) --------------------------------------------


def test_json_invalide_leve_llm_error():
    with pytest.raises(llm.LLMError):
        llm.parse_questions("ceci n'est pas du JSON")


def test_cle_questions_absente_leve_llm_error():
    with pytest.raises(llm.LLMError):
        llm.parse_questions(json.dumps({"autre": []}))


def test_question_invalide_ecartee_les_autres_gardees():
    bad_answer = {**good("Une autre question valide ?"), "correct_answer": "complex"}  # hors options
    few_options = {**good("Encore une question ?"), "options": ["int", "float"]}

    drafts = llm.parse_questions(json.dumps({"questions": [good(), bad_answer, few_options]}))
    assert [d.question for d in drafts] == ["Quel est le type de la valeur 3.14 ?"]


def test_json_entoure_de_balises_markdown_accepte():
    raw = "```json\n" + json.dumps({"questions": [good()]}) + "\n```"
    assert len(llm.parse_questions(raw)) == 1


def test_select_by_blueprint_limite_par_difficulte_et_retire_les_doublons():
    drafts = [QuestionDraft.model_validate(good(f"Question facile numéro {i} ?")) for i in range(3)]
    drafts.append(QuestionDraft.model_validate(good("QUESTION facile numéro 0 ?")))  # doublon (casse)
    assert len(llm.select_by_blueprint(drafts, {1: 1, 2: 2, 3: 1})) == 1


def test_le_prompt_mentionne_le_cours_la_competence_et_les_difficultes():
    system, user = (m["content"] for m in llm.build_messages("Bases de Python", "Boucles", {1: 1, 3: 2}))
    assert "JSON" in system and "4 options" in system
    assert "Bases de Python" in user and "Boucles" in user
    assert "2 question(s) de difficulté 3" in user and "difficulté 2" not in user


def test_sans_cle_api_aucun_appel_reseau(monkeypatch):
    monkeypatch.setattr(llm, "LLM_API_KEY", "")
    monkeypatch.setattr(llm, "_call_llm", lambda *_: pytest.fail("appel réseau inattendu"))
    assert llm.generate_many("Cours", [(1, "Boucles", {1: 1})]) == {}


def test_echec_pour_une_competence_est_isole(monkeypatch):
    monkeypatch.setattr(llm, "LLM_API_KEY", "cle-de-test")

    def fake(course_title, skill_name, wanted):
        if skill_name == "Boucles":
            raise llm.LLMError("timeout")
        return [QuestionDraft.model_validate(good(f"Question sur {skill_name} ?"))]

    monkeypatch.setattr(llm, "generate_for_skill", fake)
    result = llm.generate_many("Cours", [(1, "Boucles", {1: 1}), (2, "Fonctions", {1: 1})])
    assert list(result) == [2]


# --- appels au LLM : réessais et modèle de secours -----------------------------------------------


def fake_post(*outcomes):
    """Faux httpx.post : un code d'erreur (int) ou un contenu texte (réponse 200) par appel."""
    calls: list[str] = []

    def post(url, headers, json, timeout):
        outcome = outcomes[len(calls)]
        calls.append(json["model"])
        request = httpx.Request("POST", url)
        if isinstance(outcome, int):
            return httpx.Response(outcome, request=request, text="erreur du service")
        return httpx.Response(200, request=request, json={"choices": [{"message": {"content": outcome}}]})

    return post, calls


@pytest.fixture()
def llm_config(monkeypatch):
    monkeypatch.setattr(llm, "LLM_API_KEY", "cle-de-test")
    monkeypatch.setattr(llm, "LLM_MODEL", "principal")
    monkeypatch.setattr(llm, "LLM_FALLBACK_MODEL", "secours")
    monkeypatch.setattr(llm.time, "sleep", lambda seconds: None)  # pas d'attente réelle


def test_service_surcharge_puis_reponse_au_troisieme_essai(monkeypatch, llm_config):
    post, calls = fake_post(503, 503, "ok")
    monkeypatch.setattr(llm.httpx, "post", post)

    assert llm._call_llm([]) == "ok"
    assert calls == ["principal"] * 3


def test_modele_introuvable_bascule_sur_le_modele_de_secours(monkeypatch, llm_config):
    post, calls = fake_post(404, "ok")
    monkeypatch.setattr(llm.httpx, "post", post)

    assert llm._call_llm([]) == "ok"
    assert calls == ["principal", "secours"]


def test_cle_refusee_arrete_tout_sans_reessayer(monkeypatch, llm_config):
    post, calls = fake_post(401)
    monkeypatch.setattr(llm.httpx, "post", post)

    with pytest.raises(llm.LLMError, match="401"):
        llm._call_llm([])
    assert calls == ["principal"]


def test_panne_totale_leve_llm_error_apres_les_essais_des_deux_modeles(monkeypatch, llm_config):
    post, calls = fake_post(503, 503, 503, 503, 503, 503)
    monkeypatch.setattr(llm.httpx, "post", post)

    with pytest.raises(llm.LLMError, match="503"):
        llm._call_llm([])
    assert calls == ["principal"] * 3 + ["secours"] * 3


# --- complément de la banque ---------------------------------------------------------------------


class FakeGenerator:
    """Faux LLM : fournit exactement les questions demandées et compte ses appels."""

    def __init__(self):
        self.calls: list[list[tuple]] = []

    def __call__(self, course_title, jobs):
        self.calls.append(jobs)
        return {
            skill_id: [
                QuestionDraft.model_validate(
                    good(f"Question LLM {name} difficulté {difficulty} numéro {i} ?", difficulty)
                )
                for difficulty, count in wanted.items()
                for i in range(count)
            ]
            for skill_id, name, wanted in jobs
        }


@pytest.fixture()
def web_course(seeded_db):
    """Un cours SANS aucune question en banque (comme les futurs cours web / IA)."""
    domain = seeded_db.scalar(select(Domain).where(Domain.code == "web-dev"))
    course = Course(domain_id=domain.id, code="html-test", title="HTML de base")
    course.skills = [Skill(code=f"s{i}", name=f"Compétence {i}") for i in range(1, 5)]
    seeded_db.add(course)
    seeded_db.commit()
    return course


def bank_size(db, course) -> int:
    return db.scalar(
        select(func.count(BankQuestion.id)).where(BankQuestion.skill_id.in_([s.id for s in course.skills]))
    )


def test_cours_vide_la_banque_est_remplie_a_la_taille_cible(seeded_db, web_course):
    generator = FakeGenerator()
    added = top_up_bank(seeded_db, web_course, generator)

    assert added == 4 * sum(BANK_TARGET_PER_DIFFICULTY.values())  # 4 compétences × 8
    assert missing_questions(seeded_db, web_course) == []
    questions = seeded_db.scalars(select(BankQuestion).where(BankQuestion.source == QuestionSource.LLM)).all()
    assert all(q.review_status == ReviewStatus.APPROVED for q in questions)


def test_cours_deja_complet_aucun_appel_au_llm(seeded_db, web_course):
    generator = FakeGenerator()
    top_up_bank(seeded_db, web_course, generator)
    top_up_bank(seeded_db, web_course, generator)  # 2e démarrage : la banque suffit
    assert len(generator.calls) == 1


def test_banque_suffisante_rien_n_est_demande_au_llm(seeded_db):
    """Python a 2 / 3 / 2 questions par compétence : le LLM n'intervient pas sur un cours relu."""
    course = seeded_db.scalar(select(Course).where(Course.code == "python-basics"))
    assert missing_questions(seeded_db, course) == []


def test_seul_le_manque_est_demande_au_llm(seeded_db):
    """Si une compétence perd des questions, on ne redemande que celles qui manquent."""
    course = seeded_db.scalar(select(Course).where(Course.code == "python-basics"))
    skill = course.skills[0]
    seeded_db.execute(
        BankQuestion.__table__.update()
        .where(BankQuestion.skill_id == skill.id, BankQuestion.difficulty == 3)
        .values(review_status=ReviewStatus.RETIRED)
    )
    seeded_db.commit()

    jobs = missing_questions(seeded_db, course)
    assert jobs == [(skill.id, skill.name, {3: 2})]


def test_llm_en_panne_rien_n_est_ajoute_et_pas_d_erreur(seeded_db, web_course):
    assert top_up_bank(seeded_db, web_course, lambda title, jobs: {}) == 0
    assert bank_size(seeded_db, web_course) == 0


# --- intégration : démarrage d'un test -----------------------------------------------------------


def test_premier_etudiant_sur_un_cours_vide_declenche_la_generation(seeded_db, make_user, web_course):
    user, _ = make_user()
    generator = FakeGenerator()

    test, created = placement_service.start_or_resume(seeded_db, user.id, web_course.id, generate=generator)

    assert created and test.total_questions == 16
    assert test.generation_source == GenerationSource.LLM
    assert all(q.correct_answer in q.options for q in test.questions)
    assert all(q.bank_question_id is not None for q in test.questions)  # les explications sont conservées


def test_deuxieme_etudiant_reutilise_la_banque_sans_appel(seeded_db, make_user, web_course):
    first, _ = make_user("a@example.com")
    second, _ = make_user("b@example.com")
    generator = FakeGenerator()

    placement_service.start_or_resume(seeded_db, first.id, web_course.id, generate=generator)
    placement_service.start_or_resume(seeded_db, second.id, web_course.id, generate=generator)

    assert len(generator.calls) == 1


def test_cours_vide_et_llm_en_panne_503(client, make_user, web_course):
    _, headers = make_user()
    response = client.post("/placement-tests", json={"course_id": web_course.id}, headers=headers)
    assert response.status_code == 503


def test_cours_de_python_sans_cle_llm_fonctionne_avec_la_banque(client, make_user, seeded_db):
    course = seeded_db.scalar(select(Course).where(Course.code == "python-basics"))
    _, headers = make_user()

    response = client.post("/placement-tests", json={"course_id": course.id}, headers=headers)
    assert response.status_code == 201
    assert response.json()["total_questions"] == 16
