import { FleetMap } from '../components/FleetMap/FleetMap';
import { RobotCard } from '../components/RobotCard/RobotCard';
import { useRobots } from '../hooks/useRobots';
import { useWebSocket } from '../hooks/useWebSocket';
import type { RobotStatus } from '../types/robot';

const STATUS_ORDER: RobotStatus[] = [
  'LOW_BATTERY',
  'ERROR',
  'CLEANING',
  'RETURNING_TO_DOCK',
  'UPDATING',
  'CHARGING',
  'IDLE',
];

export function Dashboard() {
  useWebSocket();
  const { data: robots = [], isLoading } = useRobots();

  const alerts = robots.filter(
    (r) => r.status === 'LOW_BATTERY' || r.status === 'ERROR' || r.battery_level < 20,
  );

  const sorted = [...robots].sort(
    (a, b) => STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status),
  );

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* アラートバナー */}
      {alerts.length > 0 && (
        <div className="rounded-xl border border-orange-200 bg-orange-50 px-4 py-3">
          <p className="text-sm font-medium text-orange-700">
            ⚠️ {alerts.length}台のロボットに注意が必要です:{' '}
            {alerts.map((r) => r.robot_id).join(', ')}
          </p>
        </div>
      )}

      {/* サマリー */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: '総台数', value: robots.length, color: 'text-slate-800' },
          {
            label: '掃除中',
            value: robots.filter((r) => r.status === 'CLEANING').length,
            color: 'text-blue-600',
          },
          {
            label: '充電中',
            value: robots.filter((r) => r.status === 'CHARGING').length,
            color: 'text-green-600',
          },
          { label: '要注意', value: alerts.length, color: 'text-orange-600' },
        ].map((s) => (
          <div
            key={s.label}
            className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm text-center"
          >
            <p className={`text-3xl font-bold ${s.color}`}>{s.value}</p>
            <p className="mt-1 text-xs text-slate-500">{s.label}</p>
          </div>
        ))}
      </div>

      {/* フロアマップ */}
      {robots.length > 0 && <FleetMap robots={robots} />}

      {/* ロボットカード一覧 */}
      <div>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
          ロボット一覧
        </h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          {sorted.map((robot) => (
            <RobotCard key={robot.robot_id} robot={robot} />
          ))}
        </div>
      </div>
    </div>
  );
}
