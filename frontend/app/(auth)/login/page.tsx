import type { Metadata } from "next";
import Link from "next/link";
import LoginForm from "./login-form";

export const metadata: Metadata = {
  title: "Connexion | Learn Flow AI",
};

export default function LoginPage() {
  return (
    <>
      <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">Se connecter</h1>
      <p className="mb-6 mt-1 text-sm text-zinc-500">Content de vous revoir sur Learn Flow AI.</p>

      <LoginForm />

      <p className="mt-6 text-center text-sm text-zinc-500">
        Pas encore de compte ?{" "}
        <Link href="/register" className="font-medium text-zinc-900 underline dark:text-zinc-100">
          S'inscrire
        </Link>
      </p>
    </>
  );
}