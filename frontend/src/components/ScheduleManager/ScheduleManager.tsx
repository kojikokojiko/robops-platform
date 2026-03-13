import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client'
import type { Robot, ScheduleCreate } from '../../types/robot'

const ROOMS: Record<string, string> = {
  living_room: 'リビング', kitchen: 'キッチン',
  bedroom_1: '寝室1', bedroom_2: '寝室2',
}

interface Props { robots: Robot[] }

export function ScheduleManager({ robots }: Props) {
  const qc = useQueryClient()
  const { data: schedules = [] } = useQuery({ queryKey: ['schedules'], queryFn: api.schedules.list })
  const createMutation = useMutation({
    mutationFn: api.schedules.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['schedules'] }); setOpen(false) },
  })
  const deleteMutation = useMutation({
    mutationFn: api.schedules.delete,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['schedules'] }),
  })

  const [open, setOpen] = useState(false)
  const [form, setForm] = useState<ScheduleCreate>({
    robot_id: robots[0]?.robot_id ?? '',
    room_id: 'living_room',
    cron_expression: 'cron(0 8 * * ? *)',
    description: '',
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-800">掃除スケジュール</h2>
        <button
          onClick={() => setOpen(true)}
          className="rounded-lg bg-blue-500 px-4 py-2 text-sm font-medium text-white hover:bg-blue-600"
        >
          + 追加
        </button>
      </div>

      {/* スケジュール一覧 */}
      {schedules.length === 0 ? (
        <p className="rounded-xl border border-dashed border-slate-200 py-10 text-center text-sm text-slate-400">
          スケジュールがありません
        </p>
      ) : (
        <div className="space-y-2">
          {schedules.map((s) => (
            <div key={s.schedule_id} className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4">
              <div>
                <p className="font-medium text-slate-800">{s.robot_id}</p>
                <p className="text-sm text-slate-500">
                  {ROOMS[s.room_id] ?? s.room_id} &nbsp;·&nbsp; <code className="text-xs">{s.cron_expression}</code>
                </p>
                {s.description && <p className="text-xs text-slate-400">{s.description}</p>}
              </div>
              <button
                onClick={() => deleteMutation.mutate(s.schedule_id)}
                className="rounded-lg px-3 py-1.5 text-xs font-medium text-red-500 hover:bg-red-50"
              >
                削除
              </button>
            </div>
          ))}
        </div>
      )}

      {/* 作成モーダル */}
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <h3 className="mb-4 text-lg font-semibold text-slate-800">スケジュール作成</h3>
            <div className="space-y-3">
              <label className="block">
                <span className="text-sm text-slate-600">ロボット</span>
                <select
                  value={form.robot_id}
                  onChange={(e) => setForm({ ...form, robot_id: e.target.value })}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                >
                  {robots.map((r) => <option key={r.robot_id} value={r.robot_id}>{r.robot_id}</option>)}
                </select>
              </label>
              <label className="block">
                <span className="text-sm text-slate-600">部屋</span>
                <select
                  value={form.room_id}
                  onChange={(e) => setForm({ ...form, room_id: e.target.value })}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                >
                  {Object.entries(ROOMS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </label>
              <label className="block">
                <span className="text-sm text-slate-600">Cron式 (EventBridge形式)</span>
                <input
                  value={form.cron_expression}
                  onChange={(e) => setForm({ ...form, cron_expression: e.target.value })}
                  placeholder="cron(0 8 * * ? *)"
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-mono"
                />
                <p className="mt-1 text-xs text-slate-400">例: 毎日8時 → cron(0 8 * * ? *)</p>
              </label>
              <label className="block">
                <span className="text-sm text-slate-600">メモ (任意)</span>
                <input
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                />
              </label>
            </div>
            <div className="mt-5 flex gap-2">
              <button
                onClick={() => setOpen(false)}
                className="flex-1 rounded-lg border border-slate-200 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50"
              >
                キャンセル
              </button>
              <button
                onClick={() => createMutation.mutate(form)}
                disabled={createMutation.isPending}
                className="flex-1 rounded-lg bg-blue-500 py-2 text-sm font-medium text-white hover:bg-blue-600 disabled:opacity-50"
              >
                {createMutation.isPending ? '作成中...' : '作成'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
