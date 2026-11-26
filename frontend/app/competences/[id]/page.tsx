import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { MASTERY_CHIP, STEP_STATUS_LABELS } from "@/lib/learning-path-types";
import { formatScore, MASTERY_LABELS, splitQuestion } from "@/lib/placement-types";
import { getSkillDetail } from "@/lib/skill-detail";
import {
  DIFFICULTY_LABELS,
  MASTERY_BAR,
  type MissedQuestion,
  type SkillDetail,
} from "@/lib/skill-detail-types";

export const metadata: Metadata = {
  title: "Détail d’une compétence | Learn Flow AI",
};

const CARD = "rounded-2xl bg-white p-6 shadow-sm ring-1 ring-black/5 dark:bg-zinc-900 dark:ring-white/10";
const PRIMARY_BUTTON =
  "inline-block rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-500";
const SECONDARY_BUTTON =
  "inline-block rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800";

export default function SkillDetailPage(props: PageProps<"/competences/[id]">) {
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-12">
      <Link href="/parcours" className="text-sm text-zinc-500 hover:underline">
        ← Mon parcours
      </Link>
      {/* params est une donnée de requête : lu dans un composant sous <Suspense> */}
      <Suspense fallback={<p className="mt-6 text-zinc-500">Chargement de la compétence…</p>}>
        <DetailView params={props.params} />
      </Suspense>
    </main>
  );
}

async function DetailView({ params }: { params: PageProps<"/competences/[id]">["params"] }) {
  const { id } = await params;
  const skillId = Number(id);
  if (!Number.isInteger(skillId) || skillId <= 0) notFound();

  const state = await getSkillDetail(skillId);

  if (state.kind === "no_test") {
    return (
      <div className={`mt-6 ${CARD}`}>
        <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">Détail d’une compétence</h1>
        <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">{state.message}</p>
        <Link href="/dashboard" className={`mt-6 ${PRIMARY_BUTTON}`}>
          Aller au tableau de bord
        </Link>
      </div>
    );
  }

  return <DetailContent detail={state.detail} />;
}

function DetailContent({ detail }: { detail: SkillDetail }) {
  const completedOn = new Intl.DateTimeFormat("fr-FR", { dateStyle: "long", timeZone: "Africa/Tunis" }).format(
    new Date(detail.completed_at),
  );
  const score = detail.score;

  return (
    <div className="mt-4 space-y-6">
      <header>
        <p className="text-sm text-zinc-500">
          {detail.course.title} · d’après votre test du {completedOn}
        </p>
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">{detail.skill.name}</h1>
      </header>

      <section className={CARD} aria-labelledby="level-title">
        <h2 id="level-title" className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
          Mon niveau
        </h2>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <span
            className={`rounded-full px-3 py-1 text-sm font-medium ring-1 ring-inset ${MASTERY_CHIP[detail.mastery]}`}
          >
            {MASTERY_LABELS[detail.mastery]}
          </span>
          <span className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">
            {score !== null ? `${formatScore(score)} %` : "—"}
          </span>
        </div>
        <div
          role="progressbar"
          aria-label={`Score en ${detail.skill.name}`}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={score ?? 0}
          className="mt-3 h-2 overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-800"
        >
          <div className={`h-full rounded-full ${MASTERY_BAR[detail.mastery]}`} style={{ width: `${score ?? 0}%` }} />
        </div>
        <p className="mt-3 text-sm text-zinc-600 dark:text-zinc-400">
          {detail.n_questions > 0
            ? `${detail.n_correct} bonne${detail.n_correct > 1 ? "s" : ""} réponse${detail.n_correct > 1 ? "s" : ""} sur ${detail.n_questions} question${detail.n_questions > 1 ? "s" : ""}`
            : "Aucune question du test ne portait sur cette compétence."}
          {detail.n_unanswered > 0 && ` · ${detail.n_unanswered} sans réponse`}
        </p>
        {detail.mastery === "insufficient_data" && (
          <p
            role="status"
            className="mt-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-200"
          >
            Trop peu de questions pour conclure : ce niveau reste à confirmer.
          </p>
        )}
      </section>

      <section className={CARD} aria-labelledby="step-title">
        <h2 id="step-title" className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
          Dans mon parcours
        </h2>
        {detail.step ? (
          <>
            <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
              Cette compétence est l’étape {detail.step.position} de votre parcours. Statut :{" "}
              <strong className="font-medium text-zinc-900 dark:text-zinc-100">
                {STEP_STATUS_LABELS[detail.step.status]}
              </strong>
              .
            </p>
            <Link href="/parcours" className={`mt-4 ${SECONDARY_BUTTON}`}>
              Retour à mon parcours
            </Link>
          </>
        ) : (
          <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
            {detail.mastery === "mastered"
              ? "Compétence maîtrisée : elle n’a pas besoin d’étape dans votre parcours."
              : "Cette compétence n’est pas dans votre parcours. Reconstruisez-le pour l’y ajouter."}
          </p>
        )}
      </section>

      <section className={CARD} aria-labelledby="missed-title">
        <h2 id="missed-title" className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
          Lacunes associées
        </h2>
        {detail.missed_questions.length === 0 ? (
          <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
            Aucune question ratée sur cette compétence. Bravo !
          </p>
        ) : (
          <>
            <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
              {detail.missed_questions.length} question{detail.missed_questions.length > 1 ? "s" : ""} à revoir.
            </p>
            <ul className="mt-4 space-y-4">
              {detail.missed_questions.map((q) => (
                <MissedQuestionItem key={q.position} question={q} />
              ))}
            </ul>
          </>
        )}
      </section>

      <div className="flex flex-wrap gap-3">
        <Link href={`/test/${detail.test_id}/result`} className={PRIMARY_BUTTON}>
          Voir la correction complète du test
        </Link>
        <Link href="/parcours" className={SECONDARY_BUTTON}>
          Mon parcours
        </Link>
      </div>
    </div>
  );
}

function MissedQuestionItem({ question }: { question: MissedQuestion }) {
  const { prompt, code } = splitQuestion(question.question);
  return (
    <li className="rounded-xl border border-zinc-200 p-4 dark:border-zinc-800">
      <p className="text-xs text-zinc-500">
        Question {question.position} · {DIFFICULTY_LABELS[question.difficulty] ?? "—"}
      </p>
      <p className="mt-1 text-sm font-medium text-zinc-900 dark:text-zinc-100">{prompt}</p>
      {code && (
        <pre className="mt-2 overflow-x-auto rounded-lg bg-zinc-100 p-3 text-xs text-zinc-800 dark:bg-zinc-800 dark:text-zinc-100">
          <code>{code}</code>
        </pre>
      )}
      <dl className="mt-3 space-y-1 text-sm">
        <div className="flex gap-2">
          <dt className="shrink-0 text-zinc-500">Votre réponse :</dt>
          <dd className="text-rose-700 dark:text-rose-400">{question.user_answer ?? "Sans réponse"}</dd>
        </div>
        <div className="flex gap-2">
          <dt className="shrink-0 text-zinc-500">Bonne réponse :</dt>
          <dd className="font-medium text-emerald-700 dark:text-emerald-400">{question.correct_answer}</dd>
        </div>
      </dl>
    </li>
  );
}