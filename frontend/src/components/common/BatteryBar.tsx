interface Props {
  level: number; // 0-100
  showLabel?: boolean;
}

export function BatteryBar({ level, showLabel = true }: Props) {
  const color = level > 50 ? 'bg-green-500' : level > 20 ? 'bg-yellow-500' : 'bg-red-500';

  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-full rounded-full bg-slate-200">
        <div
          className={`h-2 rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${Math.max(0, Math.min(100, level))}%` }}
        />
      </div>
      {showLabel && (
        <span className="w-10 shrink-0 text-right text-xs font-medium text-slate-600">
          {level.toFixed(0)}%
        </span>
      )}
    </div>
  );
}
