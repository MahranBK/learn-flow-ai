"use client";

import Link from "next/link";

// Affichée quand l'API est injoignable ou renvoie une erreur inattendue pendant le test.
// ⚠️ Dans cette version de Next.js, la fonction de nouvelle tentative s'appelle `retry` (et non `reset`).
export default function TestError({ retry }: { error: unknown; retry: () => void }) {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-12">
      <div
        role="alert"
        className="rounded-2xl bg-white p-8 shadow-sm ring-1 ring-black/5 dark:bg-zinc-900 dark:ring-white/10"
      >
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">Un problème est survenu</h1>
        <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
          Le test de positionnement est momentanément indisponible. Vos réponses déjà enregistrées ne sont pas
          perdues.
        </p>
        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={() => retry()}
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700 dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-200"
          >
            Réessayer
          </button>
          <Link
            href="/dashboard"
            className="rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
          >
            Tableau de bord
          </Link>
        </div>
      </div>
    </main>
  );
}
