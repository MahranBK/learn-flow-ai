import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { getCourses, getHistory, progressForCourse } from "@/lib/placement";
import { formatScore, LEVEL_LABELS } from "@/lib/placement-types";
import StartTestForm from "./start-test-form";

export const metadata: Metadata = {
  title: "Test de positionnement | Learn Flow AI",
};

export default function TestPage() {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-12">
      <Link href="/dashboard" className="text-sm text-zinc-500 hover:underline">
        ← Tableau de bord
      </Link>
      <h1 className="mt-4 text-2xl font-semibold text-zinc-900 dark:text-zinc-50">Test de positionnement</h1>
      <p className="mt-1 mb-8 text-sm text-zinc-500">
        Choisissez un cours pour évaluer votre niveau de départ. Ce n’est pas une note : le résultat sert à
        adapter votre parcours. Vos réponses sont sauvegardées au fur et à mesure, vous pouvez reprendre plus tard.
      </p>

      <Suspense fallback={<p className="text-zinc-500">Chargement des cours…</p>}>
        <CourseList />
      </Suspense>
    </main>
  );
}

async function CourseList() {
  const [courses, history] = await Promise.all([getCourses(), getHistory()]);

  if (courses.length === 0) {
    return <p className="text-zinc-500">Aucun cours n’est disponible pour le moment.</p>;
  }

  return (
    <ul className="space-y-4">
      {courses.map((course) => {
        const progress = progressForCourse(history, course.id);
        return (
          <li
            key={course.id}
            className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-black/5 dark:bg-zinc-900 dark:ring-white/10"
          >
            <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">{course.title}</h2>
            {course.description && <p className="mt-1 text-sm text-zinc-500">{course.description}</p>}

            <div className="mt-4">
              {progress.state === "not_started" && <StartTestForm courseId={course.id} label="Commencer le test" />}

              {progress.state === "in_progress" && (
                <div className="space-y-2">
                  <p className="text-sm text-zinc-600 dark:text-zinc-400">Vous avez un test en cours.</p>
                  <Link
                    href={`/test/${progress.testId}`}
                    className="inline-block rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700 dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-200"
                  >
                    Reprendre le test
                  </Link>
                </div>
              )}

              {progress.state === "completed" && (
                <div className="space-y-3">
                  <p className="text-sm text-zinc-600 dark:text-zinc-400">
                    Votre niveau :{" "}
                    <strong className="text-zinc-900 dark:text-zinc-50">{LEVEL_LABELS[progress.level]}</strong>{" "}
                    ({formatScore(progress.score)} %)
                  </p>
                  <div className="flex flex-wrap items-start gap-3">
                    <Link
                      href={`/test/${progress.testId}/result`}
                      className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700 dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-200"
                    >
                      Voir mon résultat
                    </Link>
                    <StartTestForm courseId={course.id} label="Repasser le test" variant="secondary" />
                  </div>
                </div>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
