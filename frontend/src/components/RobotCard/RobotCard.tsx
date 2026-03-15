import type { Robot } from '../../types/robot';
import { BatteryBar } from '../common/BatteryBar';
import { StatusBadge } from '../common/StatusBadge';

interface Props {
  robot: Robot;
  onSelect?: (robotId: string) => void;
}

export function RobotCard({ robot, onSelect }: Props) {
  return (
    <button
      type="button"
      onClick={() => onSelect?.(robot.robot_id)}
      className="w-full cursor-pointer rounded-xl border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:border-blue-200 hover:shadow-md"
    >
      <div className="mb-3 flex items-center justify-between">
        <div>
          <p className="font-semibold text-slate-800">{robot.robot_id}</p>
          <p className="text-xs text-slate-400">{robot.position.room}</p>
        </div>
        <StatusBadge status={robot.status} />
      </div>

      <div className="space-y-2">
        <div>
          <p className="mb-1 text-xs text-slate-500">バッテリー</p>
          <BatteryBar level={robot.battery_level} />
        </div>

        <div className="flex justify-between text-xs text-slate-500">
          <span>
            速度: <strong className="text-slate-700">{robot.speed.toFixed(1)} m/s</strong>
          </span>
          <span>
            FW: <strong className="text-slate-700">{robot.firmware_version}</strong>
          </span>
        </div>

        {robot.last_seen && (
          <p className="text-xs text-slate-400">
            最終更新: {new Date(robot.last_seen).toLocaleTimeString('ja-JP')}
          </p>
        )}
      </div>
    </button>
  );
}
