import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { redirect } from "next/navigation";
import { logout } from "@/app/actions/auth";
import { getMyInterests } from "@/lib/catalog";
import { getCurrentUser } from "@/lib/session";
import MyCourses, { CoursesSkeleton } from "./my-courses";

export const metadata: Metadata = {
  title: "Tableau de bord | Learn Flow AI",
};

export default function DashboardPage() {
  return (
    <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-10 sm:py-12">
      <Suspense fallback={<CoursesSkeleton />}>
        <Dashboard />
      </Suspense>
    </main>
  );
}

async function Dashboard() {
  const user = await getCurrentUser();
  if (!user) redirect("/login?expired=1"); // session refusée par l'API → le proxy supprime le cookie

  const isStudent = user.role === "student";
  // Un étudiant qui n'a pas encore choisi de domaine passe d'abord par l'écran d'accueil.
  if (isStudent && (await getMyInterests()).length === 0) redirect("/onboarding");

  const firstName = user.full_name.split(" ")[0];

  return (
    <div className="space-y-10">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <span
            aria-hidden="true"
            className="flex size-12 items-center justify-center rounded-full bg-indigo-600 text-lg font-semibold text-white"
          >
            {firstName.charAt(0).toUpperCase()}
          </span>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
              Bonjour {firstName} 👋
            </h1>
            <p className="text-sm text-zinc-500">
              {user.email} · {isStudent ? "Étudiant" : "Administrateur"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {isStudent && (
            <Link
              href="/onboarding"
              className="rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
            >
              Modifier mes domaines
            </Link>
          )}
          <form action={logout}>
            <button
              type="submit"
              className="rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
            >
              Se déconnecter
            </button>
          </form>
        </div>
      </header>

      {/* Les cours et tests de positionnement ne concernent que les étudiants */}
      {isStudent && <MyCourses />}
    </div>
  );
}
