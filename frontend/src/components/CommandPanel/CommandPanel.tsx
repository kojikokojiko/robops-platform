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
      </div>
    </div>
  );
}
