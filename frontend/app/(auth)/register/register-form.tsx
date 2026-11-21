"use client";

import { useActionState } from "react";
import Link from "next/link";
import { register, type RegisterState } from "@/app/actions/auth";

const initialState: RegisterState = {};

export default function RegisterForm() {
  const [state, formAction, pending] = useActionState(register, initialState);

  // Critère d'acceptation : un message confirme l'inscription
  if (state.success) {
    return (
      <div
        role="status"
        className="rounded-lg bg-green-50 p-4 text-sm text-green-800 dark:bg-green-950 dark:text-green-200"
      >
        <p className="font-medium">{state.message}</p>
        <Link href="/login" className="mt-2 inline-block font-semibold underline">
          Aller à la connexion →
        </Link>
      </div>
    );
  }

  return (
    <form action={formAction} noValidate className="space-y-4">
      {state.message && (
        <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-200">
          {state.message}
        </p>
      )}

      <InputField
        label="Nom complet"
        name="full_name"
        type="text"
        autoComplete="name"
        defaultValue={state.values?.full_name}
        error={state.errors?.full_name}
      />
      <InputField
        label="Email"
        name="email"
        type="email"
        autoComplete="email"
        defaultValue={state.values?.email}
        error={state.errors?.email}
      />
      <InputField
        label="Mot de passe"
        name="password"
        type="password"
        autoComplete="new-password"
        hint="8 caractères minimum, avec au moins une lettre et un chiffre."
        error={state.errors?.password}
      />
      <InputField
        label="Confirmer le mot de passe"
        name="confirm_password"
        type="password"
        autoComplete="new-password"
        error={state.errors?.confirm_password}
      />

      <button
        type="submit"
        disabled={pending}
        className="w-full rounded-lg bg-zinc-900 px-4 py-2.5 font-medium text-white transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-200"
      >
        {pending ? "Inscription en cours…" : "S'inscrire"}
      </button>
    </form>
  );
}

type InputFieldProps = {
  label: string;
  name: string;
  type: string;
  autoComplete?: string;
  defaultValue?: string;
  hint?: string;
  error?: string;
};

function InputField({ label, name, type, autoComplete, defaultValue, hint, error }: InputFieldProps) {
  const describedBy = error ? `${name}-error` : hint ? `${name}-hint` : undefined;
  return (
    <div className="space-y-1">
      <label htmlFor={name} className="block text-sm font-medium text-zinc-700 dark:text-zinc-300">
        {label}
      </label>
      <input
        id={name}
        name={name}
        type={type}
        autoComplete={autoComplete}
        defaultValue={defaultValue}
        aria-invalid={!!error}
        aria-describedby={describedBy}
        className={`w-full rounded-lg border bg-white px-3 py-2 text-zinc-900 outline-none focus:ring-2 dark:bg-zinc-800 dark:text-zinc-100 ${
          error
            ? "border-red-500 focus:ring-red-200"
            : "border-zinc-300 focus:ring-zinc-200 dark:border-zinc-700"
        }`}
      />
      {error ? (
        <p id={`${name}-error`} className="text-sm text-red-600 dark:text-red-400">{error}</p>
      ) : hint ? (
        <p id={`${name}-hint`} className="text-xs text-zinc-500">{hint}</p>
      ) : null}
    </div>
  );
}