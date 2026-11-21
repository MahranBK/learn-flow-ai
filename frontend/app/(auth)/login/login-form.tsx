"use client";

import { useActionState } from "react";
import { login, type LoginState } from "@/app/actions/auth";

const initialState: LoginState = {};

export default function LoginForm() {
  const [state, formAction, pending] = useActionState(login, initialState);

  return (
    <form action={formAction} noValidate className="space-y-4">
      {state.message && (
        <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-200">
          {state.message}
        </p>
      )}

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
        autoComplete="current-password"
        error={state.errors?.password}
      />

      <button
        type="submit"
        disabled={pending}
        className="w-full rounded-lg bg-zinc-900 px-4 py-2.5 font-medium text-white transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-200"
      >
        {pending ? "Connexion en cours…" : "Se connecter"}
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
  error?: string;
};

function InputField({ label, name, type, autoComplete, defaultValue, error }: InputFieldProps) {
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
        aria-describedby={error ? `${name}-error` : undefined}
        className={`w-full rounded-lg border bg-white px-3 py-2 text-zinc-900 outline-none focus:ring-2 dark:bg-zinc-800 dark:text-zinc-100 ${
          error ? "border-red-500 focus:ring-red-200" : "border-zinc-300 focus:ring-zinc-200 dark:border-zinc-700"
        }`}
      />
      {error && (
        <p id={`${name}-error`} className="text-sm text-red-600 dark:text-red-400">{error}</p>
      )}
    </div>
  );
}