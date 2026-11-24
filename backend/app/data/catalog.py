"""
Catalogue : domaines → cours → compétences.

Pour ajouter un domaine, un cours ou une compétence : ajouter une entrée ici puis redémarrer le
backend (le chargement est idempotent). Chaque compétence doit avoir ses questions dans
data/question_bank.json (au minimum 2 faciles, 3 moyennes, 2 difficiles) : le LLM complète ensuite.
"""

CATALOG: list[dict] = [
    {
        "code": "programming",
        "name": "Programmation",
        "description": "Les fondamentaux pour apprendre à programmer.",
        "icon": "code",
        "courses": [
            {
                "code": "python-basics",
                "title": "Bases de Python",
                "description": "Test de positionnement sur les fondamentaux de la programmation en Python.",
                "skills": [
                    {"code": "variables-types", "name": "Variables et types de données"},
                    {"code": "conditions", "name": "Structures conditionnelles"},
                    {"code": "loops", "name": "Boucles"},
                    {"code": "functions", "name": "Fonctions"},
                ],
            },
        ],
    },
    {
        "code": "data",
        "name": "Données et bases de données",
        "description": "Interroger, analyser et structurer des données.",
        "icon": "database",
        "courses": [
            {
                "code": "sql-basics",
                "title": "Bases de SQL",
                "description": "Test de positionnement sur les requêtes SQL fondamentales.",
                "skills": [
                    {"code": "select", "name": "Requêtes SELECT"},
                    {"code": "filtering", "name": "Filtrage et tri"},
                    {"code": "joins", "name": "Jointures"},
                    {"code": "aggregation", "name": "Agrégation et regroupement"},
                ],
            },
        ],
    },
    {
        "code": "web-dev",
        "name": "Développement web",
        "description": "Créer des sites et des applications web, du front-end au back-end.",
        "icon": "globe",
        "courses": [
            {
                "code": "html-css-basics",
                "title": "HTML et CSS",
                "description": "Test de positionnement sur la structure et le style d'une page web.",
                "skills": [
                    {"code": "html-structure", "name": "Structure HTML"},
                    {"code": "css-selectors", "name": "Sélecteurs et propriétés CSS"},
                    {"code": "box-model-layout", "name": "Modèle de boîte et mise en page"},
                    {"code": "responsive", "name": "Responsive design et accessibilité"},
                ],
            },
            {
                "code": "javascript-basics",
                "title": "Bases de JavaScript",
                "description": "Test de positionnement sur les fondamentaux de JavaScript et du DOM.",
                "skills": [
                    {"code": "js-variables", "name": "Variables et types"},
                    {"code": "js-functions", "name": "Fonctions"},
                    {"code": "js-arrays-objects", "name": "Tableaux et objets"},
                    {"code": "js-dom-events", "name": "DOM et événements"},
                ],
            },
        ],
    },
    {
        "code": "ai",
        "name": "Intelligence artificielle",
        "description": "Comprendre et construire des systèmes d'apprentissage automatique.",
        "icon": "brain",
        "courses": [
            {
                "code": "ml-basics",
                "title": "Fondamentaux du Machine Learning",
                "description": "Test de positionnement sur les notions de base de l'apprentissage automatique.",
                "skills": [
                    {"code": "ml-concepts", "name": "Concepts de base de l'IA et du ML"},
                    {"code": "data-preparation", "name": "Préparation des données"},
                    {"code": "model-evaluation", "name": "Évaluation des modèles"},
                    {"code": "overfitting", "name": "Surapprentissage et généralisation"},
                ],
            },
        ],
    },
]
