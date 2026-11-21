import { cookies } from "next/headers";
import { API_URL } from "./api";

export const SESSION_COOKIE = "access_token";

export type SessionUser = {
  id: number;
  full_name: string;
  email: string;
  role: "student" | "admin";
  created_at: string;
};

/** Lit le JWT dans le cookie httpOnly (côté serveur uniquement). */
export async function getToken(): Promise<string | undefined> {
  return (await cookies()).get(SESSION_COOKIE)?.value;
}

/** Retourne l'utilisateur connecté, ou null si pas de session / session expirée. */
export async function getCurrentUser(): Promise<SessionUser | null> {
  const token = await getToken();
  if (!token) return null;

  try {
    const res = await fetch(`${API_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return (await res.json()) as SessionUser;
  } catch {
    return null;
  }
}