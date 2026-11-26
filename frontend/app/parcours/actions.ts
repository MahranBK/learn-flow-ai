"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { apiRequest } from "@/lib/api-server";
import type { LearningPath, StepStatus } from "@/lib/learning-path-types";

/** Construit (ou reconstruit) le parcours depuis les derniers tests terminés. */
export async function rebuildPathAction(): Promise<void> {
  const result = await apiRequest<LearningPath>("/learning-path/rebuild", { method: "POST" });
  if (!result.ok) {
    if (result.status === 409) redirect("/parcours?notice=no_test"); // aucun test terminé
    throw new Error(result.message);
  }
  revalidatePath("/parcours");
}

/** Change le statut d'une étape (US9). */
export async function setStepStatusAction(stepId: number, status: StepStatus): Promise<void> {
  const result = await apiRequest<LearningPath>(`/learning-path/steps/${stepId}`, {
    method: "PATCH",
    body: { status },
  });
  if (!result.ok) throw new Error(result.message);
  revalidatePath("/parcours");
}