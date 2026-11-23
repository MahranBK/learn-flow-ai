// Types et libellés du test de positionnement (contrat de l'API FastAPI : /placement-tests).
// Ce fichier ne dépend d'aucun module serveur : il peut être importé par les composants client.

export type Course = {
  id: number;
  code: string;
  title: string;
  description: string | null;
};

export type Skill = { id: number; code: string; name: string };

export type TestStatus = "pending" | "in_progress" | "completed";
export type PlacementLevel = "beginner" | "intermediate" | "advanced";
export type MasteryLevel = "gap" | "partial" | "mastered" | "insufficient_data";

/** Question vue par l'étudiant : jamais de bonne réponse avant la soumission. */
export type Question = {
  id: number;
  position: number;
  skill: Skill;
  question: string;
  options: string[];
};

export type SavedAnswer = { question_id: number; answer: string };

export type PlacementTest = {
  id: number;
  status: TestStatus;
  course: Course;
  total_questions: number;
  started_at: string;
  questions: Question[];
  answers: SavedAnswer[];
};

export type HistoryItem = {
  id: number;
  course: Course;
  attempt_number: number;
  status: TestStatus;
  score: number | null;
  level: PlacementLevel | null;
  started_at: string;
  completed_at: string | null;
};

export type SkillResult = {
  skill: Skill;
  score: number;
  n_questions: number;
  n_correct: number;
  n_unanswered: number;
  mastery: MasteryLevel;
};

export type QuestionReview = {
  question: string;
  options: string[];
  your_answer: string | null;
  correct_answer: string;
  is_correct: boolean;
  explanation: string | null;
};

export type PlacementResult = {
  id: number;
  course: Course;
  score: number;
  level: PlacementLevel;
  reliable: boolean;
  correct_count: number;
  total_questions: number;
  unanswered_count: number;
  completed_at: string;
  skills: SkillResult[];
  review: QuestionReview[];
};

export const LEVEL_LABELS: Record<PlacementLevel, string> = {
  beginner: "Débutant",
  intermediate: "Intermédiaire",
  advanced: "Avancé",
};

export const LEVEL_DESCRIPTIONS: Record<PlacementLevel, string> = {
  beginner: "Vous découvrez le sujet : votre parcours commencera par consolider les bases.",
  intermediate: "Vous maîtrisez une partie des notions : certaines compétences restent à renforcer.",
  advanced: "Vous avez une bonne maîtrise du sujet : votre parcours pourra viser des exercices plus exigeants.",
};

export const MASTERY_LABELS: Record<MasteryLevel, string> = {
  mastered: "Maîtrisée",
  partial: "En progrès",
  gap: "À renforcer",
  insufficient_data: "Données insuffisantes",
};

/** 93.75 → « 93,8 » ; 100 → « 100 » (format français). */
export function formatScore(score: number): string {
  return score.toLocaleString("fr-FR", { maximumFractionDigits: 1 });
}

/**
 * Sépare l'énoncé du code : dans la banque, la 1re ligne est la question et les suivantes
 * sont du code (à afficher en police fixe, indentation conservée).
 */
export function splitQuestion(text: string): { prompt: string; code: string | null } {
  const [prompt, ...codeLines] = text.split("\n");
  return { prompt, code: codeLines.length > 0 ? codeLines.join("\n") : null };
}
