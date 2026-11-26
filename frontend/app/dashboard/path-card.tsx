import Link from "next/link";

// Carte d'accès au parcours personnalisé (US8/US9). Volontairement statique : aucun appel API,
// donc elle ne peut pas casser le dashboard (la page /parcours gère elle-même tous les états).
export default function PathCard() {
  return (
    <section
      aria-labelledby="path-card-title"
      className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-black/5 dark:bg-zinc-900 dark:ring-white/10"
    >
      <h2 id="path-card-title" className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
        Mon parcours
      </h2>
      <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
        Les compétences à travailler, tous cours confondus, dans l’ordre conseillé. Suivez votre avancement étape par
        étape.
      </p>
      <Link
        href="/parcours"
        className="mt-4 inline-block rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-500"
      >
        Voir mon parcours
      </Link>
    </section>
  );
}