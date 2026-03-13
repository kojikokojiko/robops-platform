import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useTelemetry } from '../../hooks/useTelemetry'

interface Props {
  robotId: string
  minutes?: number
}

export function TelemetryChart({ robotId, minutes = 60 }: Props) {
  const { data, isLoading } = useTelemetry(robotId, minutes)

  if (isLoading) {
    return <div className="flex h-48 items-center justify-center text-sm text-slate-400">読み込み中...</div>
  }

  const points = (data?.points ?? []).map((p) => ({
    time: new Date(p.timestamp).toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' }),
    battery: parseFloat(p.battery_level.toFixed(1)),
    speed: parseFloat(p.speed.toFixed(2)),
  }))

  if (points.length === 0) {
    return <div className="flex h-48 items-center justify-center text-sm text-slate-400">データなし</div>
  }

  return (
    <div className="space-y-6">
      {/* バッテリー */}
      <div>
        <h3 className="mb-2 text-sm font-medium text-slate-600">バッテリー残量 (%)</h3>
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={points} margin={{ top: 4, right: 16, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="time" tick={{ fontSize: 11 }} tickLine={false} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} tickLine={false} />
            <Tooltip formatter={(v) => [`${v}%`, 'バッテリー']} />
            <Line
              type="monotone"
              dataKey="battery"
              stroke="#22c55e"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* 速度 */}
      <div>
        <h3 className="mb-2 text-sm font-medium text-slate-600">走行速度 (m/s)</h3>
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={points} margin={{ top: 4, right: 16, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="time" tick={{ fontSize: 11 }} tickLine={false} />
            <YAxis domain={[0, 2]} tick={{ fontSize: 11 }} tickLine={false} />
            <Tooltip formatter={(v) => [`${v} m/s`, '速度']} />
            <Line
              type="monotone"
              dataKey="speed"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
