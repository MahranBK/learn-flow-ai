// Types du catalogue (contrat de l'API FastAPI : /domains, /me/interests, /courses).
// Aucun import serveur : utilisable par les composants client.

import type { Course, Skill } from "./placement-types";

export type Domain = {
  id: number;
  code: string;
  name: string;
  description: string | null;
  /** Clé d'icône : voir components/domain-icon.tsx. */
  icon: string;
};

/** Cours du catalogue, avec son domaine et ses compétences. */
export type CatalogCourse = Course & {
  domain_id: number;
  domain: Domain;
  skills: Skill[];
};

/** Mêmes bornes que l'API (PUT /me/interests : 1 à 10 domaines). */
export const MAX_INTERESTS = 10;
