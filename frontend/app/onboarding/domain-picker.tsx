"use client";

import Link from "next/link";
import { useActionState, useState } from "react";
import { saveInterests, type InterestsState } from "@/app/actions/interests";
import DomainIcon from "@/components/domain-icon";
import { MAX_INTERESTS, type Domain } from "@/lib/catalog-types";

const initialState: InterestsState = {};

type Props = {
  domains: Domain[];
  selectedIds: number[];
  /** Lien « Annuler » (affiché seulement quand l'étudiant modifie un choix existant). */
  cancelHref: string | null;
};

/** Grille de cartes à cocher : un domaine = une case (accessible au clavier et au lecteur d'écran). */
export default function DomainPicker({ domains, selectedIds, cancelHref }: Props) {
  const [state, formAction, pending] = useActionState(saveInterests, initialState);
  const [selected, setSelected] = useState<Set<number>>(() => new Set(selectedIds));

  function toggle(id: number) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else if (next.size < MAX_INTERESTS) next.add(id);
      return next;
    });
  }

  return (
    <form action={formAction} className="mt-8">
      <fieldset>
        <legend className="sr-only">Domaines d’intérêt</legend>
        <ul className="grid gap-4 sm:grid-cols-2">
          {domains.map((domain) => (
            <li key={domain.id}>
              <label className="group flex h-full cursor-pointer items-start gap-4 rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm transition hover:border-zinc-300 hover:shadow-md has-checked:border-indigo-500 has-checked:bg-indigo-50/60 has-checked:ring-1 has-checked:ring-indigo-500 has-focus-visible:ring-2 has-focus-visible:ring-indigo-500 dark:border-white/10 dark:bg-zinc-900 dark:hover:border-white/20 dark:has-checked:border-indigo-400 dark:has-checked:bg-indigo-500/10 dark:has-checked:ring-indigo-400">
                <input
                  type="checkbox"
                  name="domain_id"
                  value={domain.id}
                  checked={selected.has(domain.id)}
                  onChange={() => toggle(domain.id)}
                  className="sr-only"
                />
                <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-zinc-100 text-zinc-600 transition group-has-checked:bg-indigo-600 group-has-checked:text-white dark:bg-zinc-800 dark:text-zinc-300">
                  <DomainIcon name={domain.icon} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block font-semibold text-zinc-900 dark:text-zinc-50">{domain.name}</span>
                  {domain.description && (
                    <span className="mt-1 block text-sm text-zinc-600 dark:text-zinc-400">{domain.description}</span>
                  )}
                </span>
                <span
                  aria-hidden="true"
                  className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full border border-zinc-300 text-transparent transition group-has-checked:border-indigo-600 group-has-checked:bg-indigo-600 group-has-checked:text-white dark:border-zinc-600"
                >
                  <svg viewBox="0 0 20 20" fill="currentColor" className="size-3.5">
                    <path d="M16.7 5.3a1 1 0 0 1 0 1.4l-7.5 7.5a1 1 0 0 1-1.4 0L3.3 9.7a1 1 0 1 1 1.4-1.4l3.8 3.8 6.8-6.8a1 1 0 0 1 1.4 0z" />
                  </svg>
                </span>
              </label>
            </li>
          ))}
        </ul>
      </fieldset>

      {state.message && (
        <p role="alert" className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-200">
          {state.message}
        </p>
      )}

      <div className="mt-8 flex flex-wrap items-center gap-4">
        <button
          type="submit"
          disabled={pending || selected.size === 0}
          className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {pending ? "Enregistrement…" : "Voir mes cours"}
        </button>
        {cancelHref && (
          <Link href={cancelHref} className="text-sm text-zinc-500 hover:underline">
            Annuler
          </Link>
        )}
        <p aria-live="polite" className="text-sm text-zinc-500">
          {selected.size === 0
            ? "Sélectionnez au moins un domaine."
            : `${selected.size} domaine${selected.size > 1 ? "s" : ""} sélectionné${selected.size > 1 ? "s" : ""}`}
        </p>
      </div>
    </form>
  );
}
