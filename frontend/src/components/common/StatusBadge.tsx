import type { RobotStatus } from '../../types/robot';

const CONFIG: Record<RobotStatus, { label: string; className: string }> = {
  IDLE: { label: '待機中', className: 'bg-slate-100 text-slate-700' },
  CLEANING: { label: '掃除中', className: 'bg-blue-100 text-blue-700' },
  CHARGING: { label: '充電中', className: 'bg-green-100 text-green-700' },
  RETURNING_TO_DOCK: { label: 'ドックへ', className: 'bg-yellow-100 text-yellow-700' },
  LOW_BATTERY: { label: '低バッテリー', className: 'bg-orange-100 text-orange-700' },
  UPDATING: { label: 'OTA更新中', className: 'bg-purple-100 text-purple-700' },
  ERROR: { label: 'エラー', className: 'bg-red-100 text-red-700' },
};

export function StatusBadge({ status }: { status: RobotStatus }) {
  const { label, className } = CONFIG[status] ?? {
    label: status,
    className: 'bg-slate-100 text-slate-600',
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${className}`}
    >
      {label}
    </span>
  );
}
