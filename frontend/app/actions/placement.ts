"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { apiRequest } from "@/lib/api-server";
import type { PlacementTest } from "@/lib/placement-types";

// ⚠️ Une Server Action peut être appelée directement par POST : on revalide donc toutes les entrées.
// L'authentification et les droits sont, eux, vérifiés par l'API (JWT + propriétaire du test).

export type StartTestState = { message?: string };

/** Démarre un test sur un cours (ou reprend celui en cours), puis ouvre la page du test. */
export async function startTest(_prev: StartTestState, formData: FormData): Promise<StartTestState> {
  const courseId = Number(formData.get("course_id"));
  if (!Number.isInteger(courseId) || courseId <= 0) return { message: "Cours invalide." };

  const result = await apiRequest<PlacementTest>("/placement-tests", {
    method: "POST",
    body: { course_id: courseId },
  });
  if (!result.ok) return { message: result.message };

  revalidatePath("/dashboard");
  redirect(`/test/${result.data.id}`); // ⚠️ jamais dans un try/catch
}

/** Sauvegarde une réponse au fil de l'eau (permet de reprendre le test plus tard). */
export async function saveAnswer(
  testId: number,
  questionId: number,
  answer: string,
): Promise<{ ok: boolean }> {
  if (!Number.isInteger(testId) || !Number.isInteger(questionId) || typeof answer !== "string" || !answer) {
    return { ok: false };
  }
  const result = await apiRequest<null>(`/placement-tests/${testId}/answers/${questionId}`, {
    method: "PUT",
    body: { answer },
  });
  return { ok: result.ok };
}

export type SubmittedAnswer = { question_id: number; answer: string | null };

/** Soumet le test : la correction et le score sont calculés par l'API, jamais par le navigateur. */
export async function submitTest(
  testId: number,
  answers: SubmittedAnswer[],
): Promise<{ message: string }> {
  if (!Number.isInteger(testId) || !Array.isArray(answers)) return { message: "Soumission invalide." };

  const result = await apiRequest<unknown>(`/placement-tests/${testId}/submit`, {
    method: "POST",
    body: { answers },
  });
  // Déjà terminé (double clic, deuxième onglet) : le résultat existe, on y va.
  if (!result.ok && result.status === 409) redirect(`/test/${testId}/result`);
  if (!result.ok) return { message: result.message };

  revalidatePath("/dashboard");
  redirect(`/test/${testId}/result`);
}
