import { apiRequest, type ApiResult } from "./api-server";
import type { CatalogCourse, Domain } from "./catalog-types";

/** Renvoie les données, ou lève une erreur affichée par la page d'erreur la plus proche. */
function unwrap<T>(result: ApiResult<T>): T {
  if (!result.ok) throw new Error(result.message);
  return result.data;
}

/** Tous les domaines proposés. */
export async function getDomains(): Promise<Domain[]> {
  return unwrap(await apiRequest<Domain[]>("/domains"));
}

/** Domaines choisis par l'étudiant connecté (liste vide tant qu'il n'a rien choisi). */
export async function getMyInterests(): Promise<Domain[]> {
  return unwrap(await apiRequest<Domain[]>("/me/interests"));
}

/** Cours des domaines choisis par l'étudiant, triés par domaine puis par titre. */
export async function getMyCourses(): Promise<CatalogCourse[]> {
  return unwrap(await apiRequest<CatalogCourse[]>("/courses?mine=true"));
}

/** Regroupe les cours par domaine en conservant l'ordre renvoyé par l'API. */
export function groupByDomain(courses: CatalogCourse[]): { domain: Domain; courses: CatalogCourse[] }[] {
  const groups = new Map<number, { domain: Domain; courses: CatalogCourse[] }>();
  for (const course of courses) {
    const group = groups.get(course.domain.id) ?? { domain: course.domain, courses: [] };
    group.courses.push(course);
    groups.set(course.domain.id, group);
  }
  return [...groups.values()];
}
