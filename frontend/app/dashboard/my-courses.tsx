import Link from "next/link";
import DomainIcon from "@/components/domain-icon";
import LevelBadge from "@/components/level-badge";
import StartTestForm from "@/app/test/start-test-form";
import { getMyCourses, groupByDomain } from "@/lib/catalog";
import type { CatalogCourse } from "@/lib/catalog-types";
import { getHistory, progressForCourse, type CourseProgress } from "@/lib/placement";
import { formatScore } from "@/lib/placement-types";

/**
 * « Mes cours » : les cours des domaines choisis par l'étudiant, regroupés par domaine.
 * Chaque cours montre l'état de son test de positionnement (à passer / en cours / terminé).
 */
export default async function MyCourses() {
  const [courses, history] = await Promise.all([getMyCourses(), getHistory()]);

  if (courses.length === 0) {
    return (
      <p className="rounded-2xl border border-dashed border-zinc-300 p-8 text-center text-zinc-500 dark:border-zinc-700">
        Aucun cours n’est encore disponible pour vos domaines.
      </p>
    );
  }

  const groups = groupByDomain(courses);

  return (
    <div className="space-y-10">
      {groups.map(({ domain, courses }) => (
        <section key={domain.id} aria-labelledby={`domain-${domain.id}`}>
          <div className="mb-4 flex items-center gap-3">
            <span className="flex size-9 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-300">
              <DomainIcon name={domain.icon} className="size-5" />
            </span>
            <h2 id={`domain-${domain.id}`} className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
              {domain.name}
            </h2>
          </div>

          <ul className="grid gap-4 md:grid-cols-2">
            {courses.map((course) => (
              <CourseCard key={course.id} course={course} progress={progressForCourse(history, course.id)} />
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

function CourseCard({ course, progress }: { course: CatalogCourse; progress: CourseProgress }) {
  return (
    <li className="flex flex-col rounded-2xl bg-white p-6 shadow-sm ring-1 ring-black/5 transition hover:shadow-md dark:bg-zinc-900 dark:ring-white/10">
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-semibold text-zinc-900 dark:text-zinc-50">{course.title}</h3>
        {progress.state === "completed" && <LevelBadge level={progress.level} />}
        {progress.state === "in_progress" && (
          <span className="shrink-0 rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-700 ring-1 ring-inset ring-indigo-600/20 dark:bg-indigo-500/10 dark:text-indigo-300 dark:ring-indigo-400/20">
            En cours
          </span>
        )}
      </div>

      {course.description && <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">{course.description}</p>}

      <ul aria-label="Compétences évaluées" className="mt-4 flex flex-wrap gap-1.5">
        {course.skills.map((skill) => (
          <li
            key={skill.id}
            className="rounded-md bg-zinc-100 px-2 py-0.5 text-xs text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300"
          >
            {skill.name}
          </li>
        ))}
      </ul>

      <div className="mt-auto pt-5">
        <CourseAction course={course} progress={progress} />
      </div>
    </li>
  );
}

function CourseAction({ course, progress }: { course: CatalogCourse; progress: CourseProgress }) {
  switch (progress.state) {
    case "not_started":
      return (
        <div className="space-y-2">
          <p className="text-xs text-zinc-500">Test de positionnement · environ 16 questions</p>
          <StartTestForm courseId={course.id} label="Passer le test" />
        </div>
      );
    case "in_progress":
      return (
        <Link
          href={`/test/${progress.testId}`}
          className="inline-block rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-500"
        >
          Reprendre le test
        </Link>
      );
    case "completed":
      return (
        <div className="space-y-3">
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Score : <strong className="text-zinc-900 dark:text-zinc-50">{formatScore(progress.score)} %</strong>
          </p>
          <div className="flex flex-wrap items-center gap-4">
            <Link
              href={`/test/${progress.testId}/result`}
              className="inline-block rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-500"
            >
              Voir mon résultat
            </Link>
            <Link href="/test" className="text-sm text-zinc-500 underline hover:text-zinc-700 dark:hover:text-zinc-300">
              Repasser le test
            </Link>
          </div>
        </div>
      );
  }
}

export function CoursesSkeleton() {
  return (
    <div aria-busy="true" className="animate-pulse space-y-8">
      <div className="flex items-center gap-4">
        <div className="size-12 rounded-full bg-zinc-200 dark:bg-zinc-800" />
        <div className="h-7 w-56 rounded bg-zinc-200 dark:bg-zinc-800" />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-48 rounded-2xl bg-zinc-200 dark:bg-zinc-800" />
        ))}
      </div>
    </div>
  );
}
