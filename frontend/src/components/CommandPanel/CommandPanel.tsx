import { useState } from 'react';
import { useSendCommand } from '../../hooks/useRobots';
import type { Robot } from '../../types/robot';

const ROOMS = ['living_room', 'kitchen', 'bedroom_1', 'bedroom_2'];
const ROOM_LABELS: Record<string, string> = {
  living_room: 'リビング',
  kitchen: 'キッチン',
  bedroom_1: '寝室1',
  bedroom_2: '寝室2',
};

interface Props {
  robot: Robot;
}

export function CommandPanel({ robot }: Props) {
  const [selectedRoom, setSelectedRoom] = useState('living_room');
  const [speed, setSpeed] = useState(robot.speed || 0.5);
  const { mutate: sendCommand, isPending } = useSendCommand(robot.robot_id);

  const canClean = robot.status === 'IDLE' && robot.battery_level > 20;
  const canStop = robot.status === 'CLEANING';
  const canReturn = !['CHARGING', 'RETURNING_TO_DOCK'].includes(robot.status);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="mb-4 font-semibold text-slate-700">コマンドパネル</h3>

      <div className="space-y-4">
        {/* 掃除開始 */}
        <div className="flex items-center gap-2">
          <select
            value={selectedRoom}
            onChange={(e) => setSelectedRoom(e.target.value)}
            className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
            disabled={!canClean || isPending}
          >
            {ROOMS.map((r) => (
              <option key={r} value={r}>
                {ROOM_LABELS[r]}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() =>
              sendCommand({ command: 'START_CLEANING', params: { room_id: selectedRoom } })
            }
            disabled={!canClean || isPending}
            className="rounded-lg bg-blue-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-40"
          >
            掃除開始
          </button>
        </div>

        {/* 掃除停止 */}
        <button
          type="button"
          onClick={() => sendCommand({ command: 'STOP_CLEANING' })}
          disabled={!canStop || isPending}
          className="w-full rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
        >
          掃除停止
        </button>

        {/* 充電ドックへ戻す */}
        <button
          type="button"
          onClick={() => sendCommand({ command: 'RETURN_TO_DOCK' })}
          disabled={!canReturn || isPending}
          className={`w-full rounded-lg px-4 py-2 text-sm font-medium transition
            ${
              robot.battery_level < 20
                ? 'bg-orange-500 text-white hover:bg-orange-600'
                : 'border border-slate-200 text-slate-700 hover:bg-slate-50'
            }
            disabled:cursor-not-allowed disabled:opacity-40`}
        >
          {robot.battery_level < 20 ? '⚡ 充電ドックへ戻す' : '充電ドックへ戻す'}
        </button>

        {/* 速度設定 */}
        <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
          <label htmlFor="speed-range" className="mb-2 block text-xs font-medium text-slate-600">
            速度設定: <strong>{speed.toFixed(1)} m/s</strong>
          </label>
          <input
            id="speed-range"
            type="range"
            min={0.1}
            max={2.0}
            step={0.1}
            value={speed}
            onChange={(e) => setSpeed(parseFloat(e.target.value))}
            className="w-full accent-blue-500"
            disabled={isPending}
          />
          <div className="mt-1 flex justify-between text-xs text-slate-400">
            <span>0.1</span>
            <span>2.0 m/s</span>
          </div>
          <button
            type="button"
            onClick={() => sendCommand({ command: 'SET_SPEED', params: { speed } })}
            disabled={isPending}
            className="mt-2 w-full rounded-lg bg-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-300 disabled:opacity-40"
          >
            速度を適用
          </button>
        </div>
      </div>
    </div>
  );
}
