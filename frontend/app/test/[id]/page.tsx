import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";
import { Suspense } from "react";
import { getTest } from "@/lib/placement";
import TestRunner from "./test-runner";

export const metadata: Metadata = {
  title: "Passage du test | Learn Flow AI",
};

export default function TestPage(props: PageProps<"/test/[id]">) {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-12">
      {/* params est une donnée de requête : on la lit dans un composant sous <Suspense> */}
      <Suspense fallback={<p className="text-zinc-500">Chargement du test…</p>}>
        <TestLoader params={props.params} />
      </Suspense>
    </main>
  );
}

async function TestLoader({ params }: { params: PageProps<"/test/[id]">["params"] }) {
  const { id } = await params;
  const testId = Number(id);
  if (!Number.isInteger(testId) || testId <= 0) notFound();

  const test = await getTest(testId);
  if (test.status === "completed") redirect(`/test/${testId}/result`); // un test terminé ne se repasse pas

  return (
    <>
      <p className="text-sm text-zinc-500">{test.course.title}</p>
      <h1 className="mb-6 text-2xl font-semibold text-zinc-900 dark:text-zinc-50">Test de positionnement</h1>
      <TestRunner testId={test.id} questions={test.questions} savedAnswers={test.answers} />
    </>
  );
}
