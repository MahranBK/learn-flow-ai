import os

# Doit être défini AVANT tout import de `app` : les tests n'utilisent jamais la vraie base.
os.environ["DATABASE_URL"] = "sqlite:///./test.db"