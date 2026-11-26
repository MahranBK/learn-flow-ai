import { notFound } from "next/navigation";
import { apiRequest } from "./api-server";
import type { SkillDetail } from "./skill-detail-types";

export type SkillDetailState =
  | { kind: "ready"; detail: SkillDetail }
  | { kind: "no_test"; message: string }; // aucun test terminé pour le cours de cette compétence

/**
 * Détail d'une compétence (dernier test terminé).
 * 404 → page introuvable ; 409 → état vide ; autre erreur → app/competences/error.tsx.
 */
export async function getSkillDetail(skillId: number): Promise<SkillDetailState> {
  const result = await apiRequest<SkillDetail>(`/skills/${skillId}/detail`);
  if (result.ok) return { kind: "ready", detail: result.data };
  if (result.status === 404) notFound();
  if (result.status === 409) return { kind: "no_test", message: result.message };
  throw new Error(result.message);
}