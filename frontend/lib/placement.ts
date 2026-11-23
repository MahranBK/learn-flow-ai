import { notFound, redirect } from "next/navigation";
import { apiRequest, type ApiResult } from "./api-server";
import type { Course, HistoryItem, PlacementResult, PlacementTest } from "./placement-types";

/** Renvoie les données, ou lève une erreur affichée par app/test/error.tsx. */
function unwrap<T>(result: ApiResult<T>): T {
  if (!result.ok) throw new Error(result.message);
  return result.data;
}

export async function getCourses(): Promise<Course[]> {
  return unwrap(await apiRequest<Course[]>("/courses"));
}

/** Historique des tests de l'étudiant connecté (le plus récent en premier). */
export async function getHistory(): Promise<HistoryItem[]> {
  return unwrap(await apiRequest<HistoryItem[]>("/placement-tests"));
}

export async function getTest(id: number): Promise<PlacementTest> {
  const result = await apiRequest<PlacementTest>(`/placement-tests/${id}`);
  if (!result.ok && result.status === 404) notFound();
  return unwrap(result);
}

/** Résultat d'un test terminé. Si le test n'est pas terminé (409), on renvoie vers le test. */
export async function getResult(id: number): Promise<PlacementResult> {
  const result = await apiRequest<PlacementResult>(`/placement-tests/${id}/result`);
  if (!result.ok && result.status === 404) notFound();
  if (!result.ok && result.status === 409) redirect(`/test/${id}`);
  return unwrap(result);
}

/** État du test d'un étudiant pour un cours, déduit de l'historique. */
export type CourseProgress =
  | { state: "not_started" }
  | { state: "in_progress"; testId: number }
  | { state: "completed"; testId: number; score: number; level: NonNullable<HistoryItem["level"]> };

export function progressForCourse(history: HistoryItem[], courseId: number): CourseProgress {
  const attempts = history.filter((item) => item.course.id === courseId); // déjà du plus récent au plus ancien
  const active = attempts.find((item) => item.status === "in_progress");
  if (active) return { state: "in_progress", testId: active.id };

  const done = attempts.find((item) => item.status === "completed" && item.score !== null && item.level);
  if (done) return { state: "completed", testId: done.id, score: done.score!, level: done.level! };

  return { state: "not_started" };
}
