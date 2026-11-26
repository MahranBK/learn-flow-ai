import type { Course, MasteryLevel, Skill } from "./placement-types";
import type { StepStatus } from "./learning-path-types";

export type MissedQuestion = {
  position: number;
  difficulty: number; // 1 à 3
  question: string;
  options: string[];
  user_answer: string | null; // null = laissée sans réponse
  correct_answer: string;
};

export type SkillDetail = {
  skill: Skill;
  course: Course;
  test_id: number;
  completed_at: string;
  mastery: MasteryLevel;
  score: number | null; // null = non évaluée
  n_questions: number;
  n_correct: number;
  n_unanswered: number;
  missed_questions: MissedQuestion[];
  step: { id: number; position: number; status: StepStatus } | null; // étape du parcours actif
};

export const DIFFICULTY_LABELS: Record<number, string> = {
  1: "Facile",
  2: "Moyenne",
  3: "Difficile",
};

/** Couleur de la barre de score par niveau de maîtrise. */
export const MASTERY_BAR: Record<MasteryLevel, string> = {
  mastered: "bg-emerald-500",
  partial: "bg-amber-500",
  gap: "bg-rose-500",
  insufficient_data: "bg-zinc-400",
};