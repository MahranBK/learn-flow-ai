import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { getResult } from "@/lib/placement";
import {
  formatScore,
  LEVEL_DESCRIPTIONS,
  LEVEL_LABELS,
  MASTERY_LABELS,
  splitQuestion,
  type MasteryLevel,
  type PlacementLevel,
  type QuestionReview,
} from "@/lib/placement-types";

export const metadata: Metadata = {
  title: "Résultat du test | Learn Flow AI",
};

const CARD = "rounded-2xl bg-white p-6 shadow-sm ring-1 ring-black/5 dark:bg-zinc-900 dark:ring-white/10";

const LEVEL_BADGE: Record<PlacementLevel, string> = {
  beginner: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
  intermediate: "bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-200",
  advanced: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
};

const MASTERY_STYLE: Record<MasteryLevel, { bar: string; text: string }> = {
  mastered: { bar: "bg-emerald-500", text: "text-emerald-700 dark:text-emerald-400" },
  partial: { bar: "bg-amber-500", text: "text-amber-700 dark:text-amber-400" },
  gap: { bar: "bg-rose-500", text: "text-rose-700 dark:text-rose-400" },
  insufficient_data: { bar: "bg-zinc-400", text: "text-zinc-500" },
};

export default function ResultPage(props: PageProps<"/test/[id]/result">) {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-12">
      <Link href="/dashboard" className="text-sm text-zinc-500 hover:underline">
        ← Tableau de bord
      </Link>
      {/* params est une donnée de requête : on la lit dans un composant sous <Suspense> */}
      <Suspense fallback={<p className="mt-6 text-zinc-500">Chargement du résultat…</p>}>
        <Result params={props.params} />
      </Suspense>
    </main>
  );
}

async function Result({ params }: { params: PageProps<"/test/[id]/result">["params"] }) {
  const { id } = await params;
  const testId = Number(id);
  if (!Number.isInteger(testId) || testId <= 0) notFound();

  const result = await getResult(testId);
  const completedOn = new Intl.DateTimeFormat("fr-FR", { dateStyle: "long", timeZone: "Africa/Tunis" }).format(
    new Date(result.completed_at),
  );

  const { correct_count: ok, total_questions: total, unanswered_count: blank } = result;
  const summary = [
    `${ok} bonne${ok > 1 ? "s" : ""} réponse${ok > 1 ? "s" : ""} sur ${total}.`,
    blank > 0 && `${blank} question${blank > 1 ? "s sont restées" : " est restée"} sans réponse.`,
    "Les questions plus difficiles rapportent plus de points.",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="mt-4 space-y-6">
      <header>
        <p className="text-sm text-zinc-500">
          {result.course.title} · passé le {completedOn}
        </p>
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">Résultat de votre test</h1>
      </header>

      {!result.reliable && (
        <p role="status" className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-200">
          Résultat à confirmer : plus de la moitié des questions sont restées sans réponse.
        </p>
      )}

      <section className={CARD} aria-labelledby="level-title">
        <h2 id="level-title" className="sr-only">
          Niveau et score global
        </h2>
        <div className="flex flex-wrap items-center gap-4">
          <p className="text-5xl font-semibold text-zinc-900 dark:text-zinc-50">{formatScore(result.score)} %</p>
          <span className={`rounded-full px-3 py-1 text-sm font-medium ${LEVEL_BADGE[result.level]}`}>
            Niveau {LEVEL_LABELS[result.level].toLowerCase()}
          </span>
        </div>
        <p className="mt-3 text-sm text-zinc-600 dark:text-zinc-400">{LEVEL_DESCRIPTIONS[result.level]}</p>
        <p className="mt-3 text-sm text-zinc-500">{summary}</p>
      </section>

      <section className={CARD} aria-labelledby="skills-title">
        <h2 id="skills-title" className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
          Vos compétences
        </h2>
        <ul className="mt-4 space-y-5">
          {result.skills.map((item) => {
            const style = MASTERY_STYLE[item.mastery];
            return (
              <li key={item.skill.id}>
                <div className="mb-1 flex items-baseline justify-between gap-3 text-sm">
                  <span className="font-medium text-zinc-900 dark:text-zinc-100">{item.skill.name}</span>
                  <span className={`font-medium ${style.text}`}>
                    {MASTERY_LABELS[item.mastery]} · {formatScore(item.score)} %
                  </span>
                </div>
                <div
                  role="progressbar"
                  aria-label={`Score en ${item.skill.name}`}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={item.score}
                  className="h-2 overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-800"
                >
                  <div className={`h-full rounded-full ${style.bar}`} style={{ width: `${item.score}%` }} />
                </div>
                <p className="mt-1 text-xs text-zinc-500">
                  {item.n_correct} / {item.n_questions} bonnes réponses
                </p>
              </li>
            );
          })}
        </ul>
      </section>

      <section className={CARD} aria-labelledby="review-title">
        <h2 id="review-title" className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
          Correction détaillée
        </h2>
        <ol className="mt-4 space-y-2">
          {result.review.map((item, i) => (
            <ReviewItem key={i} number={i + 1} item={item} />
          ))}
        </ol>
      </section>

      <div>
        <Link
          href="/dashboard"
          className="inline-block rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700 dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-200"
        >
          Retour au tableau de bord
        </Link>
      </div>
    </div>
  );
}

function ReviewItem({ number, item }: { number: number; item: QuestionReview }) {
  const { prompt, code } = splitQuestion(item.question);
  return (
    <li>
      <details className="rounded-lg border border-zinc-200 px-4 py-3 dark:border-zinc-700">
        <summary className="cursor-pointer text-sm font-medium text-zinc-900 dark:text-zinc-100">
          <span className={item.is_correct ? "text-emerald-600" : "text-rose-600"} aria-hidden="true">
            {item.is_correct ? "✓" : "✗"}
          </span>{" "}
          <span className="sr-only">{item.is_correct ? "Bonne réponse. " : "Mauvaise réponse. "}</span>
          {number}. {prompt}
        </summary>

        {code && (
          <pre className="mt-3 overflow-x-auto rounded-lg bg-zinc-100 p-3 font-mono text-sm whitespace-pre text-zinc-800 dark:bg-zinc-800 dark:text-zinc-100">
            {code}
          </pre>
        )}

        <ul className="mt-3 space-y-1 text-sm">
          {item.options.map((option) => {
            const isCorrect = option === item.correct_answer;
            const isYours = option === item.your_answer;
            return (
              <li
                key={option}
                className={
                  isCorrect
                    ? "font-medium text-emerald-700 dark:text-emerald-400"
                    : isYours
                      ? "font-medium text-rose-700 dark:text-rose-400"
                      : "text-zinc-600 dark:text-zinc-400"
                }
              >
                {option}
                {isCorrect && " — bonne réponse"}
                {isYours && !isCorrect && " — votre réponse"}
              </li>
            );
          })}
        </ul>
        {item.your_answer === null && <p className="mt-2 text-sm text-zinc-500">Vous n’avez pas répondu à cette question.</p>}
        {item.explanation && (
          <p className="mt-3 rounded-lg bg-zinc-50 p-3 text-sm text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
            {item.explanation}
          </p>
        )}
      </details>
    </li>
  );
}
