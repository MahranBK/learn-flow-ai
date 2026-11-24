import { LEVEL_LABELS, type PlacementLevel } from "@/lib/placement-types";

const STYLES: Record<PlacementLevel, string> = {
  beginner: "bg-amber-50 text-amber-800 ring-amber-600/20 dark:bg-amber-500/10 dark:text-amber-300 dark:ring-amber-400/20",
  intermediate: "bg-sky-50 text-sky-800 ring-sky-600/20 dark:bg-sky-500/10 dark:text-sky-300 dark:ring-sky-400/20",
  advanced: "bg-emerald-50 text-emerald-800 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-300 dark:ring-emerald-400/20",
};

/** Pastille du niveau déterminé par le test de positionnement. */
export default function LevelBadge({ level }: { level: PlacementLevel }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${STYLES[level]}`}>
      {LEVEL_LABELS[level]}
    </span>
  );
}
