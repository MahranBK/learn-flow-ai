import { apiRequest } from "./api-server";
import type { LearningPath } from "./learning-path-types";

export type LearningPathState =
  | { kind: "ready"; path: LearningPath }
  | { kind: "none" } // 404 : parcours pas encore construit
  | { kind: "error"; message: string };

export async function getLearningPath(): Promise<LearningPathState> {
  const result = await apiRequest<LearningPath>("/learning-path");
  if (result.ok) return { kind: "ready", path: result.data };
  if (result.status === 404) return { kind: "none" };
  return { kind: "error", message: result.message };
}