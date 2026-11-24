import { NextResponse, type NextRequest } from "next/server";

// Même nom de cookie que dans lib/session.ts
const SESSION_COOKIE = "access_token";

// Pages réservées aux utilisateurs connectés (ajouter ici les futures pages : /test, /parcours, ...)
const PROTECTED_ROUTES = ["/dashboard", "/onboarding", "/test", "/admin"];
// Pages réservées aux admins
const ADMIN_ROUTES = ["/admin"];
// Pages inutiles si on est déjà connecté
const AUTH_ROUTES = ["/login", "/register"];

type JwtPayload = { sub?: string; role?: string; exp?: number };

/** Lit le contenu du JWT (sans vérifier la signature : c'est le rôle du backend). */
function decodeJwtPayload(token: string): JwtPayload | null {
  try {
    const part = token.split(".")[1];
    if (!part) return null;
    const base64 = part.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, "=");
    return JSON.parse(atob(padded));
  } catch {
    return null;
  }
}

function matches(pathname: string, routes: string[]) {
  return routes.some((route) => pathname === route || pathname.startsWith(`${route}/`));
}

export function proxy(request: NextRequest) {
  const { pathname, searchParams } = request.nextUrl;
  const token = request.cookies.get(SESSION_COOKIE)?.value;
  const payload = token ? decodeJwtPayload(token) : null;
  const isLoggedIn = !!payload?.exp && payload.exp * 1000 > Date.now();

  // 1. Page protégée sans session valide → /login (+ suppression du cookie expiré)
  if (matches(pathname, PROTECTED_ROUTES) && !isLoggedIn) {
    const response = NextResponse.redirect(new URL("/login", request.url));
    if (token) response.cookies.delete(SESSION_COOKIE);
    return response;
  }

  // 2. Page admin avec un rôle non admin → /dashboard
  if (matches(pathname, ADMIN_ROUTES) && payload?.role !== "admin") {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  if (matches(pathname, AUTH_ROUTES)) {
    // 3. Session refusée par l'API (?expired=1) → on supprime le cookie et on affiche /login
    if (searchParams.has("expired")) {
      const response = NextResponse.next();
      response.cookies.delete(SESSION_COOKIE);
      return response;
    }
    // 4. Déjà connecté → pas besoin de /login ou /register
    if (isLoggedIn) {
      return NextResponse.redirect(new URL("/dashboard", request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  // Toutes les pages sauf les fichiers statiques et internes de Next.js
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};