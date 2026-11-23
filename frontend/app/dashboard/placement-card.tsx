import Link from "next/link";
import { getCourses, getHistory, progressForCourse } from "@/lib/placement";
import { formatScore, LEVEL_LABELS } from "@/lib/placement-types";
import StartTestForm from "@/app/test/start-test-form";

const PRIMARY_LINK =
  "inline-block rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700 dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-200";

/**
 * Carte « Test de positionnement » du tableau de bord (étudiants uniquement) :
 * - jamais passé → invitation à passer le test ;
 * - en cours → reprise ;
 * - terminé → niveau et accès au résultat détaillé (page séparée).
 */
export default async function PlacementCard() {
  const [courses, history] = await Promise.all([getCourses(), getHistory()]);
  if (courses.length === 0) return null;

  return (
    <section
      aria-labelledby="placement-title"
      className="rounded-2xl bg-white p-8 shadow-sm ring-1 ring-black/5 dark:bg-zinc-900 dark:ring-white/10"
    >
      <h2 id="placement-title" className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
        Test de positionnement
      </h2>

      <ul className="mt-4 space-y-6">
        {courses.map((course) => {
          const progress = progressForCourse(history, course.id);
          return (
            <li key={course.id}>
              <p className="font-medium text-zinc-900 dark:text-zinc-100">{course.title}</p>

              {progress.state === "not_started" && (
                <div className="mt-2 space-y-3">
                  <p className="text-sm text-zinc-600 dark:text-zinc-400">
                    Évaluez votre niveau de départ : le résultat servira à adapter votre parcours.
                  </p>
                  <StartTestForm courseId={course.id} label="Passer le test" />
                </div>
              )}

              {progress.state === "in_progress" && (
                <div className="mt-2 space-y-3">
                  <p className="text-sm text-zinc-600 dark:text-zinc-400">Vous avez un test en cours.</p>
                  <Link href={`/test/${progress.testId}`} className={PRIMARY_LINK}>
                    Reprendre le test
                  </Link>
                </div>
              )}

              {progress.state === "completed" && (
                <div className="mt-2 space-y-3">
                  <p className="text-sm text-zinc-600 dark:text-zinc-400">
                    Votre niveau :{" "}
                    <strong className="text-zinc-900 dark:text-zinc-50">{LEVEL_LABELS[progress.level]}</strong>{" "}
                    ({formatScore(progress.score)} %)
                  </p>
                  <div className="flex flex-wrap items-center gap-4">
                    <Link href={`/test/${progress.testId}/result`} className={PRIMARY_LINK}>
                      Voir mon résultat
                    </Link>
                    <Link href="/test" className="text-sm text-zinc-500 underline hover:text-zinc-700">
                      Repasser le test
                    </Link>
                  </div>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
