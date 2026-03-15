import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useTelemetry } from '../../hooks/useTelemetry';

interface Props {
  robotId: string;
  minutes?: number;
}

export function TelemetryChart({ robotId, minutes = 60 }: Props) {
  const { data, isLoading } = useTelemetry(robotId, minutes);

  if (isLoading) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-slate-400">
        読み込み中...
      </div>
    );
  }

  // 1分ごとに平均値を集約（0.3秒テレメトリだと60分で12,000点になりRechartsが描画失敗するため）
  const points = (() => {
    const raw = data?.points ?? [];
    const buckets = new Map<string, { battery: number; speed: number; count: number }>();
    for (const p of raw) {
      const key = new Date(p.timestamp).toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
      const b = buckets.get(key);
      if (b) {
        b.battery += p.battery_level;
        b.speed += p.speed;
        b.count++;
      } else {
        buckets.set(key, { battery: p.battery_level, speed: p.speed, count: 1 });
      }
    }
    return Array.from(buckets.entries()).map(([time, { battery, speed, count }]) => ({
      time,
      battery: parseFloat((battery / count).toFixed(1)),
      speed: parseFloat((speed / count).toFixed(2)),
    }));
  })();

  if (points.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-slate-400">データなし</div>
    );
  }

  console.log('[TelemetryChart] points:', points.length, points.slice(0, 3));

  return (
    <div className="space-y-6">
      {/* バッテリー */}
      <div>
        <h3 className="mb-2 text-sm font-medium text-slate-600">バッテリー残量 (%)</h3>
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={points} margin={{ top: 8, right: 16, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="time" tick={{ fontSize: 11 }} tickLine={false} />
            <YAxis
              domain={[
                (min: number) => Math.max(0, Math.floor(min - 5)),
                (max: number) => Math.min(100, Math.ceil(max + 5)),
              ]}
              tick={{ fontSize: 11 }}
              tickLine={false}
            />
            <Tooltip formatter={(v) => [`${v}%`, 'バッテリー']} />
            <Line
              type="monotone"
              dataKey="battery"
              stroke="#22c55e"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* 速度 */}
      <div>
        <h3 className="mb-2 text-sm font-medium text-slate-600">走行速度 (m/s)</h3>
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={points} margin={{ top: 8, right: 16, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="time" tick={{ fontSize: 11 }} tickLine={false} />
            <YAxis
              domain={[
                (min: number) => Math.max(0, Math.floor(min * 10 - 1) / 10),
                (max: number) => Math.ceil((max + 0.2) * 10) / 10,
              ]}
              tick={{ fontSize: 11 }}
              tickLine={false}
            />
            <Tooltip formatter={(v) => [`${v} m/s`, '速度']} />
            <Line
              type="monotone"
              dataKey="speed"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
