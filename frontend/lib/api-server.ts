import { redirect } from "next/navigation";
import { API_URL } from "./api";
import { getToken } from "./session";

export type ApiResult<T> =
  | { ok: true; status: number; data: T }
  | { ok: false; status: number; message: string };

const NETWORK_ERROR = "Impossible de joindre le serveur. Réessayez plus tard.";

/** Extrait un message lisible d'une réponse d'erreur FastAPI ({ detail: string | [...] }). */
function errorMessage(data: unknown): string {
  const detail = (data as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  return "Une erreur est survenue. Réessayez.";
}

/**
 * Appelle l'API avec le JWT du cookie httpOnly (côté serveur uniquement).
 * - pas de jeton ou 401 → redirection vers /login?expired=1 (le proxy supprime alors le cookie) ;
 * - 403 (rôle non autorisé) → redirection vers /dashboard ;
 * - autre erreur → { ok: false, status, message } avec le message de l'API (en français).
 * ⚠️ redirect() lance une exception : ne jamais appeler cette fonction dans un try/catch.
 */
export async function apiRequest<T>(
  path: string,
  options: { method?: "GET" | "POST" | "PUT"; body?: unknown } = {},
): Promise<ApiResult<T>> {
  const token = await getToken();
  if (!token) redirect("/login?expired=1");

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method: options.method ?? "GET",
      headers: {
        Authorization: `Bearer ${token}`,
        ...(options.body !== undefined && { "Content-Type": "application/json" }),
      },
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      cache: "no-store",
    });
  } catch {
    return { ok: false, status: 0, message: NETWORK_ERROR };
  }

  if (res.status === 401) redirect("/login?expired=1");
  if (res.status === 403) redirect("/dashboard"); // rôle non autorisé (ex. un admin sur une page étudiant)

  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) return { ok: false, status: res.status, message: errorMessage(data) };
  return { ok: true, status: res.status, data: data as T };
}
