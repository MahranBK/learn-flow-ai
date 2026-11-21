"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { SESSION_COOKIE } from "@/lib/session";

import { API_URL } from "@/lib/api";

type Field = "full_name" | "email" | "password" | "confirm_password";

export type RegisterState = {
  success?: boolean;
  message?: string;
  errors?: Partial<Record<Field, string>>;
  values?: { full_name: string; email: string };
};

export async function register(
  _prevState: RegisterState,
  formData: FormData,
): Promise<RegisterState> {
  const full_name = String(formData.get("full_name") ?? "").trim();
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");
  const confirm_password = String(formData.get("confirm_password") ?? "");
  const values = { full_name, email }; // pour ne pas vider le formulaire en cas d'erreur

  // 1. Validation (mêmes règles que l'API)
  const errors: RegisterState["errors"] = {};
  if (full_name.length < 2) {
    errors.full_name = "Le nom doit contenir au moins 2 caractères.";
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    errors.email = "Adresse email invalide.";
  }
  if (password.length < 8) {
    errors.password = "Le mot de passe doit contenir au moins 8 caractères.";
  } else if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) {
    errors.password = "Le mot de passe doit contenir au moins une lettre et un chiffre.";
  }
  if (password !== confirm_password) {
    errors.confirm_password = "Les mots de passe ne correspondent pas.";
  }
  if (Object.keys(errors).length > 0) {
    return { errors, values };
  }

  // 2. Appel à l'API FastAPI
  let res: Response;
  try {
    res = await fetch(`${API_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ full_name, email, password }),
      cache: "no-store",
    });
  } catch {
    return { message: "Impossible de joindre le serveur. Réessayez plus tard.", values };
  }

  const data = await res.json().catch(() => null);

  // 3. Traitement de la réponse
  if (res.status === 201) {
    return { success: true, message: data?.message ?? "Inscription réussie !" };
  }
  if (res.status === 409) {
    return { errors: { email: data?.detail ?? "Cet email est déjà utilisé." }, values };
  }
  if (res.status === 422 && Array.isArray(data?.detail)) {
    const apiErrors: RegisterState["errors"] = {};
    for (const err of data.detail) {
      const field = err.loc?.[err.loc.length - 1];
      if (field === "full_name" || field === "email" || field === "password") {
        apiErrors[field] = String(err.msg).replace(/^Value error, /, "");
      }
    }
    return { errors: apiErrors, values };
  }
  return { message: "Une erreur est survenue. Réessayez.", values };
}

export type LoginState = {
  message?: string;
  errors?: { email?: string; password?: string };
  values?: { email: string };
};

export async function login(_prevState: LoginState, formData: FormData): Promise<LoginState> {
  const email = String(formData.get("email") ?? "").trim();
  const password = String(formData.get("password") ?? "");
  const values = { email };

  // 1. Validation
  const errors: LoginState["errors"] = {};
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errors.email = "Adresse email invalide.";
  if (!password) errors.password = "Veuillez saisir votre mot de passe.";
  if (Object.keys(errors).length > 0) return { errors, values };

  // 2. Appel à l'API
  let res: Response;
  try {
    res = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
      cache: "no-store",
    });
  } catch {
    return { message: "Impossible de joindre le serveur. Réessayez plus tard.", values };
  }

  const data = await res.json().catch(() => null);

  // 3. Erreurs (401 mauvais identifiants, 403 compte désactivé)
  if (!res.ok) {
    const detail = typeof data?.detail === "string" ? data.detail : "Connexion impossible.";
    return { message: detail, values };
  }

  // 4. Succès : on stocke le JWT dans un cookie httpOnly
  (await cookies()).set(SESSION_COOKIE, data.access_token, {
    httpOnly: true, // inaccessible au JavaScript du navigateur (protection XSS)
    secure: process.env.NODE_ENV === "production", // HTTPS uniquement en production
    sameSite: "lax", // protection CSRF
    path: "/",
    maxAge: data.expires_in, // le cookie expire en même temps que le JWT
  });

  redirect("/dashboard"); // ⚠️ jamais dans un try/catch : redirect() fonctionne en lançant une exception
}

export async function logout() {
  (await cookies()).delete(SESSION_COOKIE);
  redirect("/login");
}