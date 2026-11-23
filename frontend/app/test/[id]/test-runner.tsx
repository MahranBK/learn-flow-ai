"use client";

import { useState, useTransition } from "react";
import { saveAnswer, submitTest } from "@/app/actions/placement";
import { splitQuestion, type Question, type SavedAnswer } from "@/lib/placement-types";

type Props = {
  testId: number;
  questions: Question[];
  savedAnswers: SavedAnswer[]; // réponses déjà enregistrées (reprise d'un test interrompu)
};

export default function TestRunner({ testId, questions, savedAnswers }: Props) {
  const [answers, setAnswers] = useState<Record<number, string>>(() =>
    Object.fromEntries(savedAnswers.map((a) => [a.question_id, a.answer])),
  );
  // On reprend à la première question sans réponse
  const [index, setIndex] = useState(() => {
    const firstUnanswered = questions.findIndex((q) => !savedAnswers.some((a) => a.question_id === q.id));
    return firstUnanswered === -1 ? 0 : firstUnanswered;
  });
  const [unsynced, setUnsynced] = useState<ReadonlySet<number>>(new Set());
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, startSubmit] = useTransition();

  const question = questions[index];
  const total = questions.length;
  const answeredCount = questions.filter((q) => answers[q.id] !== undefined).length;
  const unansweredCount = total - answeredCount;
  const isLast = index === total - 1;
  const { prompt, code } = splitQuestion(question.question);

  function markSynced(questionId: number, ok: boolean) {
    setUnsynced((previous) => {
      const next = new Set(previous);
      if (ok) next.delete(questionId);
      else next.add(questionId);
      return next;
    });
  }

  function select(option: string) {
    setAnswers((previous) => ({ ...previous, [question.id]: option }));
    setConfirming(false);
    // Sauvegarde au fil de l'eau. En cas d'échec, la réponse reste en mémoire et sera renvoyée à la fin.
    saveAnswer(testId, question.id, option)
      .then((result) => markSynced(question.id, result.ok))
      .catch(() => markSynced(question.id, false));
  }

  function finish() {
    if (unansweredCount > 0 && !confirming) {
      setConfirming(true); // on demande confirmation avant de laisser des questions sans réponse
      return;
    }
    setError(null);
    startSubmit(async () => {
      const result = await submitTest(
        testId,
        questions.map((q) => ({ question_id: q.id, answer: answers[q.id] ?? null })),
      );
      // En cas de succès, l'action redirige vers la page de résultat : on n'arrive ici qu'en cas d'erreur.
      setError(result.message);
    });
  }

  return (
    <div className="space-y-6">
      {/* Progression */}
      <div>
        <div className="mb-2 flex items-center justify-between text-sm text-zinc-600 dark:text-zinc-400">
          <span>
            Question {index + 1} sur {total}
          </span>
          <span>
            {answeredCount} / {total} répondues
          </span>
        </div>
        <div
          role="progressbar"
          aria-label="Progression du test"
          aria-valuemin={0}
          aria-valuemax={total}
          aria-valuenow={answeredCount}
          className="h-2 overflow-hidden rounded-full bg-zinc-200 dark:bg-zinc-800"
        >
          <div
            className="h-full rounded-full bg-zinc-900 transition-all dark:bg-white"
            style={{ width: `${(answeredCount / total) * 100}%` }}
          />
        </div>
      </div>

      {/* Question */}
      <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-black/5 dark:bg-zinc-900 dark:ring-white/10">
        <p className="mb-3 inline-block rounded-full bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300">
          {question.skill.name}
        </p>
        <p className="text-lg font-medium text-zinc-900 dark:text-zinc-50">{prompt}</p>
        {code && (
          <pre className="mt-3 overflow-x-auto rounded-lg bg-zinc-100 p-4 font-mono text-sm whitespace-pre text-zinc-800 dark:bg-zinc-800 dark:text-zinc-100">
            {code}
          </pre>
        )}

        <fieldset className="mt-5 space-y-2" disabled={isSubmitting}>
          <legend className="sr-only">Choisissez une réponse</legend>
          {question.options.map((option, optionIndex) => {
            const checked = answers[question.id] === option;
            const inputId = `q${question.id}-o${optionIndex}`;
            return (
              <label
                key={option}
                htmlFor={inputId}
                className={`flex cursor-pointer items-start gap-3 rounded-lg border px-4 py-3 text-sm transition ${
                  checked
                    ? "border-zinc-900 bg-zinc-50 dark:border-white dark:bg-zinc-800"
                    : "border-zinc-200 hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
                }`}
              >
                <input
                  id={inputId}
                  type="radio"
                  name={`question-${question.id}`}
                  value={option}
                  checked={checked}
                  onChange={() => select(option)}
                  className="mt-0.5"
                />
                <span className="text-zinc-900 dark:text-zinc-100">{option}</span>
              </label>
            );
          })}
        </fieldset>

        {unsynced.size > 0 && (
          <p role="status" className="mt-4 text-sm text-amber-700 dark:text-amber-400">
            Une réponse n’a pas pu être sauvegardée pour l’instant. Elle est conservée et sera envoyée à la fin du test.
          </p>
        )}
      </section>

      {/* Navigation entre les questions */}
      <nav aria-label="Aller à une question" className="flex flex-wrap gap-2">
        {questions.map((q, i) => {
          const answered = answers[q.id] !== undefined;
          return (
            <button
              key={q.id}
              type="button"
              onClick={() => setIndex(i)}
              disabled={isSubmitting}
              aria-current={i === index ? "step" : undefined}
              aria-label={`Question ${i + 1}${answered ? ", répondue" : ", sans réponse"}`}
              className={`h-9 w-9 rounded-lg text-sm font-medium transition disabled:opacity-60 ${
                i === index ? "ring-2 ring-zinc-900 ring-offset-2 dark:ring-white dark:ring-offset-black" : ""
              } ${
                answered
                  ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
                  : "border border-zinc-300 text-zinc-600 dark:border-zinc-700 dark:text-zinc-300"
              }`}
            >
              {i + 1}
            </button>
          );
        })}
      </nav>

      {/* Confirmation et erreurs */}
      {confirming && (
        <p role="alert" className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-200">
          {unansweredCount > 1
            ? `Il reste ${unansweredCount} questions sans réponse. Elles compteront comme fausses.`
            : "Il reste 1 question sans réponse. Elle comptera comme fausse."}{" "}
          Voulez-vous terminer quand même ?
        </p>
      )}
      {error && (
        <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-200">
          {error}
        </p>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={() => setIndex((i) => i - 1)}
          disabled={index === 0 || isSubmitting}
          className="rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-40 dark:border-zinc-700 dark:hover:bg-zinc-800"
        >
          Précédent
        </button>

        <div className="flex gap-3">
          {!isLast && (
            <button
              type="button"
              onClick={() => setIndex((i) => i + 1)}
              disabled={isSubmitting}
              className="rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium hover:bg-zinc-100 disabled:opacity-40 dark:border-zinc-700 dark:hover:bg-zinc-800"
            >
              Suivant
            </button>
          )}
          <button
            type="button"
            onClick={finish}
            disabled={isSubmitting}
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-200"
          >
            {isSubmitting
              ? "Correction en cours…"
              : confirming
                ? "Terminer quand même"
                : "Terminer le test"}
          </button>
        </div>
      </div>
    </div>
  );
}
