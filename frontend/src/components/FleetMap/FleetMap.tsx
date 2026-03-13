import { useNavigate } from 'react-router-dom';
import type { Robot, RobotStatus } from '../../types/robot';

// フロアマップ定義 (emulator/robot/robot_state.py の ROOMS と一致させる)
const ROOMS = [
  { id: 'living_room', label: 'リビング', x: 1, y: 0, w: 5, h: 4 },
  { id: 'kitchen', label: 'キッチン', x: 6, y: 0, w: 4, h: 4 },
  { id: 'bedroom_1', label: '寝室1', x: 0, y: 4, w: 5, h: 4 },
  { id: 'bedroom_2', label: '寝室2', x: 5, y: 4, w: 5, h: 4 },
  { id: 'charging_dock', label: '充電', x: 0, y: 0, w: 1, h: 1 },
];

// フロアは 10m × 8m → SVG 500px × 400px (1m = 50px)
const SCALE = 50;
const W = 10 * SCALE;
const H = 8 * SCALE;

const STATUS_COLOR: Record<RobotStatus, string> = {
  IDLE: '#94a3b8',
  CLEANING: '#3b82f6',
  CHARGING: '#22c55e',
  RETURNING_TO_DOCK: '#f59e0b',
  LOW_BATTERY: '#f97316',
  UPDATING: '#a855f7',
  ERROR: '#ef4444',
};

interface Props {
  robots: Robot[];
}

export function FleetMap({ robots }: Props) {
  const navigate = useNavigate();

  return (
    <div className="overflow-auto rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="mb-3 text-sm font-semibold text-slate-500 uppercase tracking-wide">
        フロアマップ
      </h2>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full max-w-2xl"
        style={{ aspectRatio: `${W}/${H}` }}
        aria-label="フロアマップ"
        role="img"
      >
        <title>フロアマップ</title>
        {/* 背景 */}
        <rect x={0} y={0} width={W} height={H} fill="#f8fafc" />

        {/* 部屋 */}
        {ROOMS.map((room) => (
          <g key={room.id}>
            <rect
              x={room.x * SCALE}
              y={room.y * SCALE}
              width={room.w * SCALE}
              height={room.h * SCALE}
              fill={room.id === 'charging_dock' ? '#dcfce7' : '#e2e8f0'}
              stroke="#cbd5e1"
              strokeWidth={1.5}
              rx={4}
            />
            <text
              x={(room.x + room.w / 2) * SCALE}
              y={(room.y + room.h / 2) * SCALE}
              textAnchor="middle"
              dominantBaseline="middle"
              fill="#64748b"
              fontSize={room.id === 'charging_dock' ? 8 : 12}
              fontWeight={500}
            >
              {room.label}
            </text>
          </g>
        ))}

        {/* ロボット */}
        {robots.map((robot) => {
          const cx = robot.position.x * SCALE;
          const cy = robot.position.y * SCALE;
          const color = STATUS_COLOR[robot.status] ?? '#94a3b8';
          const label = robot.robot_id.replace('robot-', '');

          return (
            <a
              key={robot.robot_id}
              href={`/robots/${robot.robot_id}`}
              onClick={(e) => {
                e.preventDefault();
                navigate(`/robots/${robot.robot_id}`);
              }}
              aria-label={robot.robot_id}
              className="cursor-pointer"
            >
              {/* 掃除中はパルスリング */}
              {robot.status === 'CLEANING' && (
                <circle cx={cx} cy={cy} r={14} fill={color} opacity={0.2}>
                  <animate attributeName="r" values="12;20;12" dur="2s" repeatCount="indefinite" />
                  <animate
                    attributeName="opacity"
                    values="0.3;0;0.3"
                    dur="2s"
                    repeatCount="indefinite"
                  />
                </circle>
              )}
              <circle cx={cx} cy={cy} r={12} fill={color} stroke="white" strokeWidth={2} />
              <text
                x={cx}
                y={cy}
                textAnchor="middle"
                dominantBaseline="middle"
                fill="white"
                fontSize={9}
                fontWeight={700}
              >
                {label}
              </text>
              {/* 低バッテリーアイコン */}
              {(robot.status === 'LOW_BATTERY' || robot.battery_level < 20) && (
                <text x={cx + 10} y={cy - 10} fontSize={10}>
                  ⚡
                </text>
              )}
            </a>
          );
        })}
      </svg>

      {/* 凡例 */}
      <div className="mt-3 flex flex-wrap gap-3">
        {Object.entries(STATUS_COLOR).map(([status, color]) => (
          <div key={status} className="flex items-center gap-1 text-xs text-slate-500">
            <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: color }} />
            {STATUS_LABELS[status as RobotStatus]}
          </div>
        ))}
      </div>
    </div>
  );
}

const STATUS_LABELS: Record<RobotStatus, string> = {
  IDLE: '待機中',
  CLEANING: '掃除中',
  CHARGING: '充電中',
  RETURNING_TO_DOCK: 'ドックへ',
  LOW_BATTERY: '低バッテリー',
  UPDATING: 'OTA更新中',
  ERROR: 'エラー',
};
