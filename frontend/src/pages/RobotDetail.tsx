import { useNavigate, useParams } from 'react-router-dom';
import { CommandPanel } from '../components/CommandPanel/CommandPanel';
import { BatteryBar } from '../components/common/BatteryBar';
import { StatusBadge } from '../components/common/StatusBadge';
import { TelemetryChart } from '../components/TelemetryChart/TelemetryChart';
import { useRobot } from '../hooks/useRobots';

const ROOM_LABELS: Record<string, string> = {
  living_room: 'リビング',
  kitchen: 'キッチン',
  bedroom_1: '寝室1',
  bedroom_2: '寝室2',
  charging_dock: '充電ドック',
};

export function RobotDetail() {
  const { robotId = '' } = useParams();
  const navigate = useNavigate();
  const { data: robot, isLoading } = useRobot(robotId);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
      </div>
    );
  }

  if (!robot) {
    return (
      <div className="py-16 text-center text-slate-500">
        <p>ロボットが見つかりません</p>
        <button
          type="button"
          onClick={() => navigate('/')}
          className="mt-3 text-sm text-blue-500 hover:underline"
        >
          ← ダッシュボードへ
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ヘッダー */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => navigate('/')}
          className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100"
          aria-label="戻る"
        >
          ←
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-800">{robot.robot_id}</h1>
            <StatusBadge status={robot.status} />
          </div>
          <p className="text-sm text-slate-500">
            {ROOM_LABELS[robot.position.room] ?? robot.position.room} &nbsp;·&nbsp; FW{' '}
            {robot.firmware_version}
          </p>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        {/* 左: デジタルツイン・コマンド */}
        <div className="space-y-4 lg:col-span-1">
          {/* デジタルツイン */}
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="mb-4 font-semibold text-slate-700">デジタルツイン</h3>
            <div className="space-y-3">
              <div>
                <p className="mb-1 text-xs text-slate-500">バッテリー</p>
                <BatteryBar level={robot.battery_level} />
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="rounded-lg bg-slate-50 p-3">
                  <p className="text-xs text-slate-500">速度</p>
                  <p className="mt-0.5 text-xl font-bold text-slate-800">
                    {robot.speed.toFixed(1)}
                    <span className="text-sm font-normal"> m/s</span>
                  </p>
                </div>
                <div className="rounded-lg bg-slate-50 p-3">
                  <p className="text-xs text-slate-500">位置 (X, Y)</p>
                  <p className="mt-0.5 text-sm font-bold text-slate-800">
                    ({robot.position.x.toFixed(1)}, {robot.position.y.toFixed(1)})
                  </p>
                </div>
                <div className="col-span-2 rounded-lg bg-slate-50 p-3">
                  <p className="text-xs text-slate-500">部屋</p>
                  <p className="mt-0.5 font-bold text-slate-800">
                    {ROOM_LABELS[robot.position.room] ?? robot.position.room}
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

          {/* コマンドパネル */}
          <CommandPanel robot={robot} />
        </div>

        {/* 右: テレメトリグラフ */}
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="font-semibold text-slate-700">テレメトリ履歴</h3>
          </div>
          <TelemetryChart robotId={robot.robot_id} minutes={60} />
        </div>
      </div>
    </div>
  );
}
