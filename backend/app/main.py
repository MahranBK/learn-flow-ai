from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import init_db

from app.routers import auth, courses, domains, placement, learning_path, skill_detail

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # crée les tables + rôles par défaut au démarrage
    yield

app = FastAPI(title="Learn Flow AI API", version="0.1.0", lifespan=lifespan)

#to allow next.js (frontend) to communicate with fastAPI (backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(domains.router)
app.include_router(courses.router)
app.include_router(placement.router)
app.include_router(learning_path.router)
app.include_router(skill_detail.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "project": "Learn Flow AI"}