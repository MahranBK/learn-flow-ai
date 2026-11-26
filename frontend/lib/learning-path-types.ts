import type { Course, MasteryLevel, Skill } from "./placement-types";

export type StepStatus = "todo" | "in_progress" | "done";

export type PathStep = {
  id: number;
  position: number;
  course: Course;
  skill: Skill;
  mastery_at_creation: MasteryLevel;
  score_at_creation: number | null; // null = compétence non évaluée
  objective: string;
  status: StepStatus;
  completed_at: string | null;
};

export type PathProgress = {
  total: number;
  done: number;
  in_progress: number;
  todo: number;
  percent: number; // 0-100 ; 100 si le parcours est vide
};

export type LearningPath = {
  id: number;
  created_at: string;
  progress: PathProgress;
  steps: PathStep[];
};

export const STEP_STATUS_LABELS: Record<StepStatus, string> = {
  todo: "À faire",
  in_progress: "En cours",
  done: "Terminée",
};

/** Classes Tailwind de la puce de niveau (mêmes couleurs que la page de résultat). */
export const MASTERY_CHIP: Record<MasteryLevel, string> = {
  mastered:
    "bg-emerald-50 text-emerald-800 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-300 dark:ring-emerald-400/20",
  partial:
    "bg-amber-50 text-amber-800 ring-amber-600/20 dark:bg-amber-500/10 dark:text-amber-300 dark:ring-amber-400/20",
  gap: "bg-rose-50 text-rose-800 ring-rose-600/20 dark:bg-rose-500/10 dark:text-rose-300 dark:ring-rose-400/20",
  insufficient_data:
    "bg-zinc-100 text-zinc-700 ring-zinc-500/20 dark:bg-zinc-800 dark:text-zinc-300 dark:ring-zinc-400/20",
};