"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { apiRequest } from "@/lib/api-server";
import { MAX_INTERESTS, type Domain } from "@/lib/catalog-types";

export type InterestsState = { message?: string };

/** Enregistre les domaines choisis (ils remplacent les précédents), puis ouvre « Mes cours ». */
export async function saveInterests(_prev: InterestsState, formData: FormData): Promise<InterestsState> {
  // ⚠️ Une Server Action peut être appelée directement par POST : on revalide l'entrée.
  const ids = [...new Set(formData.getAll("domain_id").map(Number))];
  if (ids.length === 0) return { message: "Choisissez au moins un domaine." };
  if (ids.length > MAX_INTERESTS || ids.some((id) => !Number.isInteger(id) || id <= 0)) {
    return { message: "Sélection invalide." };
  }

  const result = await apiRequest<Domain[]>("/me/interests", { method: "PUT", body: { domain_ids: ids } });
  if (!result.ok) return { message: result.message };

  revalidatePath("/dashboard");
  redirect("/dashboard"); // ⚠️ jamais dans un try/catch
}
