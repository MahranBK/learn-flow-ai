"""
Catalogue : domaines → cours → compétences.

Pour ajouter un domaine, un cours ou une compétence : ajouter une entrée ici puis redémarrer le
backend (le chargement est idempotent). Les cours web-dev et ai n'ont pas encore de cours : ils
seront ajoutés avec la génération des questions par LLM.
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
        "courses": [],
    },
    {
        "code": "ai",
        "name": "Intelligence artificielle",
        "description": "Comprendre et construire des systèmes d'apprentissage automatique.",
        "icon": "brain",
        "courses": [],
    },
]
