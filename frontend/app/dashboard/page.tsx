import type { Metadata } from "next";
import { Suspense } from "react";
import { redirect } from "next/navigation";
import { logout } from "@/app/actions/auth";
import { getCurrentUser } from "@/lib/session";

export const metadata: Metadata = {
  title: "Tableau de bord | Learn Flow AI",
};

export default function DashboardPage() {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-12">
      <Suspense fallback={<p className="text-zinc-500">Chargement…</p>}>
        <UserPanel />
      </Suspense>
    </main>
  );
}

async function UserPanel() {
  const user = await getCurrentUser();
  if (!user) redirect("/login?expired=1"); // session refusée par l'API → le proxy supprime le cookie
  
  return (
    <div className="rounded-2xl bg-white p-8 shadow-sm ring-1 ring-black/5 dark:bg-zinc-900 dark:ring-white/10">
      <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
        Bonjour {user.full_name} 👋
      </h1>
      <dl className="mt-4 space-y-1 text-sm text-zinc-600 dark:text-zinc-400">
        <div><dt className="inline font-medium">Email : </dt><dd className="inline">{user.email}</dd></div>
        <div><dt className="inline font-medium">Rôle : </dt><dd className="inline">{user.role === "admin" ? "Administrateur" : "Étudiant"}</dd></div>
      </dl>

      <form action={logout} className="mt-6">
        <button
          type="submit"
          className="rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
        >
          Se déconnecter
        </button>
      </form>
    </div>
  );
}