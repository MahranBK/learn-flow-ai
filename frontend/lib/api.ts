// URL de l'API FastAPI utilisée côté serveur Next.js (Server Actions).
// Dans Docker : http://backend:8000 — en local sans Docker : http://localhost:8000
export const API_URL =
  process.env.API_INTERNAL_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000";