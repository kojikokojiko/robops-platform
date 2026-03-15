import { useState } from 'react';
import { CommandPanel } from '../components/CommandPanel/CommandPanel';
import { BatteryBar } from '../components/common/BatteryBar';
import { StatusBadge } from '../components/common/StatusBadge';
import { FleetMap } from '../components/FleetMap/FleetMap';
import { RobotCard } from '../components/RobotCard/RobotCard';
import { TelemetryChart } from '../components/TelemetryChart/TelemetryChart';
import { useRobot, useRobots } from '../hooks/useRobots';
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

const ROOM_LABELS: Record<string, string> = {
  living_room: 'リビング',
  kitchen: 'キッチン',
  bedroom_1: '寝室1',
  bedroom_2: '寝室2',
  charging_dock: '充電ドック',
};

// ─── 詳細パネル ───────────────────────────────────────────
function RobotDetailPanel({ robotId, onClose }: { robotId: string; onClose: () => void }) {
  const { data: robot, isLoading } = useRobot(robotId);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-3 border-b border-slate-200 px-5 py-4 shrink-0">
        {robot && (
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h2 className="font-bold text-slate-800 truncate">{robot.robot_id}</h2>
              <StatusBadge status={robot.status} />
            </div>
            <p className="text-xs text-slate-500">
              {ROOM_LABELS[robot.position.room] ?? robot.position.room}
              &nbsp;·&nbsp;FW {robot.firmware_version}
            </p>
          </div>
        )}
        <button
          type="button"
          onClick={onClose}
          className="ml-auto rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 shrink-0"
          aria-label="閉じる"
        >
          ✕
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {isLoading && (
          <div className="flex h-32 items-center justify-center">
            <div className="h-6 w-6 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
          </div>
        )}
        {robot && (
          <>
            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <h3 className="mb-3 text-sm font-semibold text-slate-700">デジタルツイン</h3>
              <div className="space-y-3">
                <div>
                  <p className="mb-1 text-xs text-slate-500">バッテリー</p>
                  <BatteryBar level={robot.battery_level} />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="rounded-lg bg-slate-50 p-2">
                    <p className="text-xs text-slate-500">速度</p>
                    <p className="mt-0.5 text-lg font-bold text-slate-800">
                      {robot.speed.toFixed(1)}
                      <span className="text-xs font-normal"> m/s</span>
                    </p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-2">
                    <p className="text-xs text-slate-500">位置 (X, Y)</p>
                    <p className="mt-0.5 text-sm font-bold text-slate-800">
                      ({robot.position.x.toFixed(1)}, {robot.position.y.toFixed(1)})
                    </p>
                  </div>
                </div>
                {robot.last_seen && (
                  <p className="text-xs text-slate-400">
                    最終更新: {new Date(robot.last_seen).toLocaleString('ja-JP')}
                  </p>
                )}
              </div>
            </div>

            <CommandPanel robot={robot} />

            <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
              <h3 className="mb-3 text-sm font-semibold text-slate-700">テレメトリ履歴</h3>
              <TelemetryChart robotId={robot.robot_id} minutes={60} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ─── ダッシュボード ───────────────────────────────────────
export function Dashboard() {
  useWebSocket();
  const { data: robots = [], isLoading } = useRobots();
  const [selectedRobotId, setSelectedRobotId] = useState<string | null>(null);

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
    <div className="flex gap-5 items-start">
      {/* メインコンテンツ */}
      <div className="flex-1 min-w-0 space-y-6">
        {alerts.length > 0 && (
          <div className="rounded-xl border border-orange-200 bg-orange-50 px-4 py-3">
            <p className="text-sm font-medium text-orange-700">
              ⚠️ {alerts.length}台のロボットに注意が必要です:{' '}
              {alerts.map((r) => r.robot_id).join(', ')}
            </p>
          </div>
        )}

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

        {robots.length > 0 && <FleetMap robots={robots} onSelect={setSelectedRobotId} />}

        <div>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
            ロボット一覧
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
            {sorted.map((robot) => (
              <RobotCard key={robot.robot_id} robot={robot} onSelect={setSelectedRobotId} />
            ))}
          </div>
        </div>
      </div>

      {/* 詳細パネル (右側固定) */}
      {selectedRobotId && (
        <aside
          className="w-96 shrink-0 sticky top-4 rounded-xl border border-slate-200 bg-white shadow-lg overflow-hidden"
          style={{ height: 'calc(100vh - 5rem)' }}
        >
          <RobotDetailPanel robotId={selectedRobotId} onClose={() => setSelectedRobotId(null)} />
        </aside>
      )}
    </div>
  );
}
