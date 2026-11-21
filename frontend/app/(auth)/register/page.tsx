import type { Metadata } from "next";
import Link from "next/link";
import RegisterForm from "./register-form";

export const metadata: Metadata = {
  title: "Inscription | Learn Flow AI",
};

export default function RegisterPage() {
  return (
    <>
      <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">Créer un compte</h1>
      <p className="mb-6 mt-1 text-sm text-zinc-500">
        Rejoignez Learn Flow AI et commencez votre parcours personnalisé.
      </p>

      <RegisterForm />

      <p className="mt-6 text-center text-sm text-zinc-500">
        Déjà un compte ?{" "}
        <Link href="/login" className="font-medium text-zinc-900 underline dark:text-zinc-100">
          Se connecter
        </Link>
      </p>
    </>
  );
}