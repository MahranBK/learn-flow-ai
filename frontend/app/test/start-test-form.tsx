"use client";

import { useActionState } from "react";
import { startTest, type StartTestState } from "@/app/actions/placement";

const initialState: StartTestState = {};

const STYLES = {
  primary:
    "bg-indigo-600 text-white shadow-sm hover:bg-indigo-500",
  secondary:
    "border border-zinc-300 hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800",
} as const;

type Props = { courseId: number; label: string; variant?: keyof typeof STYLES };

/** Bouton qui démarre (ou reprend) un test sur un cours et affiche l'éventuelle erreur de l'API. */
export default function StartTestForm({ courseId, label, variant = "primary" }: Props) {
  const [state, formAction, pending] = useActionState(startTest, initialState);

  return (
    <form action={formAction} className="space-y-2">
      <input type="hidden" name="course_id" value={courseId} />
      <button
        type="submit"
        disabled={pending}
        className={`rounded-lg px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-60 ${STYLES[variant]}`}
      >
        {pending ? "Préparation du test…" : label}
      </button>
      {state.message && (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {state.message}
        </p>
      )}
    </form>
  );
}
