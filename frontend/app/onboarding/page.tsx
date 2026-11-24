import type { Metadata } from "next";
import { Suspense } from "react";
import { redirect } from "next/navigation";
import { getDomains, getMyInterests } from "@/lib/catalog";
import { getCurrentUser } from "@/lib/session";
import DomainPicker from "./domain-picker";

export const metadata: Metadata = {
  title: "Vos centres d'intérêt | Learn Flow AI",
};

export default function OnboardingPage() {
  return (
    <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-12 sm:py-16">
      <Suspense fallback={<PickerSkeleton />}>
        <Picker />
      </Suspense>
    </main>
  );
}

async function Picker() {
  const user = await getCurrentUser();
  if (!user) redirect("/login?expired=1");
  if (user.role !== "student") redirect("/dashboard"); // seuls les étudiants choisissent des domaines

  const [domains, interests] = await Promise.all([getDomains(), getMyInterests()]);
  const isFirstVisit = interests.length === 0;

  return (
    <>
      <header className="max-w-2xl">
        <p className="text-sm font-medium text-indigo-600 dark:text-indigo-400">
          {isFirstVisit ? `Bienvenue ${user.full_name.split(" ")[0]} 👋` : "Vos centres d'intérêt"}
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-zinc-900 sm:text-4xl dark:text-zinc-50">
          Qu’aimeriez-vous apprendre ?
        </h1>
        <p className="mt-3 text-zinc-600 dark:text-zinc-400">
          Choisissez un ou plusieurs domaines. Nous vous proposerons les cours correspondants, avec un test
          de positionnement pour chacun afin d’identifier votre niveau de départ.
        </p>
      </header>

      <DomainPicker domains={domains} selectedIds={interests.map((d) => d.id)} cancelHref={isFirstVisit ? null : "/dashboard"} />
    </>
  );
}

function PickerSkeleton() {
  return (
    <div aria-busy="true" className="animate-pulse space-y-8">
      <div className="space-y-3">
        <div className="h-4 w-32 rounded bg-zinc-200 dark:bg-zinc-800" />
        <div className="h-9 w-2/3 rounded bg-zinc-200 dark:bg-zinc-800" />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-32 rounded-2xl bg-zinc-200 dark:bg-zinc-800" />
        ))}
      </div>
    </div>
  );
}
