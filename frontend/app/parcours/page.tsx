import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { getLearningPath } from "@/lib/learning-path";
import {
  MASTERY_CHIP,
  STEP_STATUS_LABELS,
  type LearningPath,
  type PathStep,
  type StepStatus,
} from "@/lib/learning-path-types";
import { formatScore, MASTERY_LABELS } from "@/lib/placement-types";
import { rebuildPathAction, setStepStatusAction } from "./actions";

export const metadata: Metadata = {
  title: "Mon parcours | Learn Flow AI",
};

const CARD = "rounded-2xl bg-white p-6 shadow-sm ring-1 ring-black/5 dark:bg-zinc-900 dark:ring-white/10";
const PRIMARY_BUTTON =
  "inline-block rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-500";
const SECONDARY_BUTTON =
  "inline-block rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800";

const STATUS_CHIP: Record<StepStatus, string> = {
  todo: "bg-zinc-100 text-zinc-700 ring-zinc-500/20 dark:bg-zinc-800 dark:text-zinc-300 dark:ring-zinc-400/20",
  in_progress:
    "bg-indigo-50 text-indigo-800 ring-indigo-600/20 dark:bg-indigo-500/10 dark:text-indigo-300 dark:ring-indigo-400/20",
  done: "bg-emerald-50 text-emerald-800 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-300 dark:ring-emerald-400/20",
};

export default function LearningPathPage(props: PageProps<"/parcours">) {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-12">
      <Link href="/dashboard" className="text-sm text-zinc-500 hover:underline">
        ← Tableau de bord
      </Link>
      {/* Données de requête (cookie, searchParams) : lues dans un composant sous <Suspense> */}
      <Suspense fallback={<p className="mt-6 text-zinc-500">Chargement de votre parcours…</p>}>
        <PathView searchParams={props.searchParams} />
      </Suspense>
    </main>
  );
}

async function PathView({ searchParams }: { searchParams: PageProps<"/parcours">["searchParams"] }) {
  const { notice } = await searchParams;
  const state = await getLearningPath();

  const noTestNotice =
    notice === "no_test" ? (
      <p role="status" className="mt-6 rounded-lg bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-200">
        Aucun test terminé pour l’instant : passez d’abord un test de positionnement depuis le tableau de bord.
      </p>
    ) : null;

  if (state.kind === "error") {
    return (
      <div role="alert" className={`mt-6 ${CARD}`}>
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">Un problème est survenu</h1>
        <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">{state.message}</p>
      </div>
    );
  }

  if (state.kind === "none") {
    return (
      <>
        {noTestNotice}
        <div className={`mt-6 ${CARD}`}>
          <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">Mon parcours</h1>
          <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
            Votre parcours d’apprentissage est construit à partir des résultats de vos tests de positionnement, tous
            cours confondus. Il n’a pas encore été créé.
          </p>
          <form action={rebuildPathAction} className="mt-6">
            <button type="submit" className={PRIMARY_BUTTON}>
              Construire mon parcours
            </button>
          </form>
        </div>
      </>
    );
  }

  return (
    <>
      {noTestNotice}
      <PathContent path={state.path} />
    </>
  );
}

function PathContent({ path }: { path: LearningPath }) {
  const { progress, steps } = path;
  const createdOn = new Intl.DateTimeFormat("fr-FR", { dateStyle: "long", timeZone: "Africa/Tunis" }).format(
    new Date(path.created_at),
  );

  return (
    <div className="mt-4 space-y-6">
      <header>
        <p className="text-sm text-zinc-500">Construit le {createdOn} à partir de vos derniers tests</p>
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">Mon parcours</h1>
      </header>

      <section className={CARD} aria-labelledby="progress-title">
        <h2 id="progress-title" className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
          Ma progression
        </h2>
        <div className="mt-3 flex items-baseline justify-between text-sm">
          <span className="text-zinc-600 dark:text-zinc-400">
            {progress.done} / {progress.total} étape{progress.total > 1 ? "s" : ""} terminée
            {progress.done > 1 ? "s" : ""}
          </span>
          <span className="font-medium text-zinc-900 dark:text-zinc-100">{progress.percent} %</span>
        </div>
        <div
          role="progressbar"
          aria-label="Progression du parcours"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={progress.percent}
          className="mt-2 h-2 overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-800"
        >
          <div className="h-full rounded-full bg-indigo-500" style={{ width: `${progress.percent}%` }} />
        </div>
        <p className="mt-3 text-xs text-zinc-500">
          {progress.in_progress} en cours · {progress.todo} à faire
        </p>
      </section>

      {steps.length === 0 ? (
        <section className={CARD}>
          <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">Rien à travailler pour l’instant</h2>
          <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
            Vos derniers tests montrent que toutes les compétences évaluées sont maîtrisées. Bravo !
          </p>
        </section>
      ) : (
        <ol className="space-y-4" aria-label="Étapes du parcours">
          {steps.map((step) => (
            <StepCard key={step.id} step={step} />
          ))}
        </ol>
      )}

      <section className={CARD} aria-labelledby="rebuild-title">
        <h2 id="rebuild-title" className="text-base font-semibold text-zinc-900 dark:text-zinc-50">
          Mettre à jour mon parcours
        </h2>
        <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
          Après avoir repassé un test, reconstruisez votre parcours. L’ancien est archivé et votre avancement repart de
          zéro.
        </p>
        <form action={rebuildPathAction} className="mt-4">
          <button type="submit" className={SECONDARY_BUTTON}>
            Reconstruire à partir de mes derniers tests
          </button>
        </form>
      </section>
    </div>
  );
}

function StepCard({ step }: { step: PathStep }) {
  const done = step.status === "done";
  return (
    <li className={`${CARD} ${done ? "opacity-80" : ""}`}>
      <div className="flex items-start gap-4">
        <span
          aria-hidden="true"
          className="flex size-8 shrink-0 items-center justify-center rounded-full bg-zinc-100 text-sm font-semibold text-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
        >
          {done ? "✓" : step.position}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-xs text-zinc-500">
            Étape {step.position} · {step.course.title}
          </p>
          <h3
            className={`text-base font-semibold text-zinc-900 dark:text-zinc-50 ${done ? "line-through decoration-zinc-400" : ""}`}
          >
            {step.skill.name}
          </h3>
          <div className="mt-2 flex flex-wrap gap-2">
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${STATUS_CHIP[step.status]}`}
            >
              {STEP_STATUS_LABELS[step.status]}
            </span>
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${MASTERY_CHIP[step.mastery_at_creation]}`}
            >
              {MASTERY_LABELS[step.mastery_at_creation]}
              {step.score_at_creation !== null && ` · ${formatScore(step.score_at_creation)} %`}
            </span>
          </div>
          <p className="mt-3 text-sm text-zinc-600 dark:text-zinc-400">{step.objective}</p>
          <StepActions step={step} />
        </div>
      </div>
    </li>
  );
}

function StepActions({ step }: { step: PathStep }) {
  const setStatus = (status: StepStatus) => setStepStatusAction.bind(null, step.id, status);
  return (
    <div className="mt-4 flex flex-wrap items-center gap-2">
      {step.status === "todo" && (
        <form action={setStatus("in_progress")}>
          <button type="submit" className={PRIMARY_BUTTON}>
            Commencer
          </button>
        </form>
      )}
      {step.status === "in_progress" && (
        <form action={setStatus("done")}>
          <button type="submit" className={PRIMARY_BUTTON}>
            Marquer comme terminé
          </button>
        </form>
      )}
      {step.status === "done" && (
        <form action={setStatus("todo")}>
          <button type="submit" className={SECONDARY_BUTTON}>
            Rouvrir
          </button>
        </form>
      )}
      <Link href={`/competences/${step.skill.id}`} className={SECONDARY_BUTTON}>
        Voir le détail
      </Link>
    </div>
  );
}