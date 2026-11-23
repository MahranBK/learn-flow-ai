import Link from "next/link";

// Page 404 en français (aussi affichée pour un test qui n'appartient pas à l'utilisateur connecté).
export default function NotFound() {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-12">
      <div className="rounded-2xl bg-white p-8 shadow-sm ring-1 ring-black/5 dark:bg-zinc-900 dark:ring-white/10">
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">Page introuvable</h1>
        <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
          Cette page n’existe pas, ou vous n’y avez pas accès.
        </p>
        <Link
          href="/dashboard"
          className="mt-6 inline-block rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700 dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-200"
        >
          Retour au tableau de bord
        </Link>
      </div>
    </main>
  );
}
