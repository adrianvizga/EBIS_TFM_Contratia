
interface UsageBadgeProps {
  used: number;
  limit: number | null;
  label: string;
  compact?: boolean;
}

export default function UsageBadge({ used, limit, label, compact = false }: UsageBadgeProps) {
  if (limit === null) return null;

  const remaining = Math.max(0, limit - used);
  const pct = limit > 0 ? (used / limit) * 100 : 0;

  let colorClasses: string;
  let barColor: string;
  if (pct >= 100) {
    colorClasses = 'text-red-600 dark:text-red-400';
    barColor = 'bg-red-500';
  } else if (pct >= 75) {
    colorClasses = 'text-amber-600 dark:text-amber-400';
    barColor = 'bg-amber-500';
  } else {
    colorClasses = 'text-primary-600 dark:text-primary-400';
    barColor = 'bg-primary-500';
  }

  if (compact) {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
          pct >= 100
            ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
            : pct >= 75
            ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300'
            : 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
        }`}
        title={`${label}: ${used}/${limit} usados`}
      >
        {remaining}/{limit}
      </span>
    );
  }

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-dark-600 dark:text-dark-400">{label}</span>
        <span className={`text-xs font-bold ${colorClasses}`}>
          {used}/{limit}
        </span>
      </div>
      <div className="w-full bg-dark-200 dark:bg-dark-700 rounded-full h-1.5 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${Math.min(100, pct)}%` }}
        />
      </div>
    </div>
  );
}
