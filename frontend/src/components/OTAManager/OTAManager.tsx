import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { api } from '../../api/client';
import type { OtaJobCreate, Robot } from '../../types/robot';

const STATUS_COLOR: Record<string, string> = {
  QUEUED: 'bg-slate-100 text-slate-600',
  IN_PROGRESS: 'bg-blue-100 text-blue-700',
  SUCCEEDED: 'bg-green-100 text-green-700',
  FAILED: 'bg-red-100 text-red-700',
  CANCELED: 'bg-slate-100 text-slate-500',
};
const STATUS_LABEL: Record<string, string> = {
  QUEUED: '待機中',
  IN_PROGRESS: '更新中',
  SUCCEEDED: '完了',
  FAILED: '失敗',
  CANCELED: 'キャンセル',
};

interface Props {
  robots: Robot[];
}

export function OTAManager({ robots }: Props) {
  const qc = useQueryClient();
  const { data: jobs = [] } = useQuery({
    queryKey: ['ota-jobs'],
    queryFn: api.ota.listJobs,
    refetchInterval: 3000,
  });
  const createMutation = useMutation({
    mutationFn: api.ota.createJob,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ota-jobs'] });
      setOpen(false);
    },
  });

  const [open, setOpen] = useState(false);
  const [filterRobot, setFilterRobot] = useState<string | null>(null);
  const [form, setForm] = useState<OtaJobCreate>({
    robot_ids: robots.map((r) => r.robot_id),
    new_speed: 0.8,
    version: '1.1.0',
    description: '',
  });
  const toggleRobot = (id: string) => {
    setForm((f) => ({
      ...f,
      robot_ids: f.robot_ids.includes(id)
        ? f.robot_ids.filter((r) => r !== id)
        : [...f.robot_ids, id],
    }));
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-800">OTA アップデート</h2>
          <p className="text-sm text-slate-500">走行速度の変更をファームウェア更新としてデモ</p>
        </div>
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="rounded-lg bg-purple-500 px-4 py-2 text-sm font-medium text-white hover:bg-purple-600"
        >
          OTA 実行
        </button>
      </div>

      {/* ロボット別ファームウェアバージョン */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
        {robots.map((r) => (
          <div
            key={r.robot_id}
            className="rounded-xl border border-slate-200 bg-white p-3 text-center"
          >
            <p className="text-xs font-medium text-slate-500">{r.robot_id}</p>
            <p className="mt-1 text-lg font-bold text-slate-800">{r.firmware_version}</p>
            <p className="text-xs text-slate-400">FW</p>
          </div>
        ))}
      </div>

      {/* ジョブ履歴 */}
      <div className="rounded-xl border border-slate-200 bg-white">
        <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 px-4 py-3">
          <h3 className="text-sm font-semibold text-slate-700 mr-2">ジョブ履歴</h3>
          <button
            type="button"
            onClick={() => setFilterRobot(null)}
            className={`rounded-full px-3 py-0.5 text-xs font-medium transition ${
              filterRobot === null
                ? 'bg-slate-700 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            すべて
          </button>
          {robots.map((r) => (
            <button
              key={r.robot_id}
              type="button"
              onClick={() => setFilterRobot(filterRobot === r.robot_id ? null : r.robot_id)}
              className={`rounded-full px-3 py-0.5 text-xs font-medium transition ${
                filterRobot === r.robot_id
                  ? 'bg-slate-700 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {r.robot_id}
            </button>
          ))}
        </div>
        {jobs.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-400">ジョブがありません</p>
        ) : (
          <div className="divide-y divide-slate-50">
            {[...jobs]
              .filter((job) => filterRobot === null || job.robot_id === filterRobot)
              .sort((a, b) => {
                const dateDiff = (b.started_at ?? '').localeCompare(a.started_at ?? '');
                if (dateDiff !== 0) return dateDiff;
                return a.robot_id.localeCompare(b.robot_id);
              })
              .map((job) => (
                <div
                  key={`${job.job_id}-${job.robot_id}`}
                  className="flex items-center justify-between px-4 py-3"
                >
                  <div>
                    <p className="text-sm font-medium text-slate-800">
                      {job.robot_id} &nbsp;
                      <span className="font-normal text-slate-500">→ v{job.firmware_version}</span>
                    </p>
                    <p className="text-xs text-slate-400">
                      速度: {job.new_speed} m/s &nbsp;·&nbsp; {job.job_id}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {job.status === 'IN_PROGRESS' && (
                      <div className="h-1.5 w-20 rounded-full bg-slate-200">
                        <div
                          className="h-1.5 rounded-full bg-blue-500 transition-all"
                          style={{ width: `${job.progress}%` }}
                        />
                      </div>
                    )}
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLOR[job.status] ?? 'bg-slate-100 text-slate-600'}`}
                    >
                      {STATUS_LABEL[job.status] ?? job.status}
                    </span>
                  </div>
                </div>
              ))}
          </div>
        )}
      </div>

      {/* OTA 実行モーダル */}
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <h3 className="mb-1 text-lg font-semibold text-slate-800">OTA アップデート実行</h3>
            <p className="mb-4 text-sm text-slate-500">
              速度変更をファームウェア更新としてロボットに配信します
            </p>
            <div className="space-y-3">
              <div className="block">
                <span className="text-sm text-slate-600">対象ロボット</span>
                <div className="mt-1 flex flex-wrap gap-2">
                  {robots.map((r) => (
                    <button
                      type="button"
                      key={r.robot_id}
                      onClick={() => toggleRobot(r.robot_id)}
                      className={`rounded-lg px-3 py-1.5 text-xs font-medium transition
                        ${
                          form.robot_ids.includes(r.robot_id)
                            ? 'bg-purple-500 text-white'
                            : 'border border-slate-200 text-slate-600 hover:bg-slate-50'
                        }`}
                    >
                      {r.robot_id}
                    </button>
                  ))}
                </div>
              </div>
              <label className="block">
                <span className="text-sm text-slate-600">
                  新しい最大速度 (m/s): <strong>{form.new_speed}</strong>
                </span>
                <input
                  type="range"
                  min={0.1}
                  max={2.0}
                  step={0.1}
                  value={form.new_speed}
                  onChange={(e) => setForm({ ...form, new_speed: parseFloat(e.target.value) })}
                  className="mt-1 w-full accent-purple-500"
                />
                <div className="flex justify-between text-xs text-slate-400">
                  <span>0.1</span>
                  <span>2.0</span>
                </div>
              </label>
              <label className="block">
                <span className="text-sm text-slate-600">バージョン</span>
                <input
                  value={form.version}
                  onChange={(e) => setForm({ ...form, version: e.target.value })}
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-mono"
                />
              </label>
            </div>
            <div className="mt-5 flex gap-2">
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="flex-1 rounded-lg border border-slate-200 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50"
              >
                キャンセル
              </button>
              <button
                type="button"
                onClick={() => createMutation.mutate(form)}
                disabled={createMutation.isPending || form.robot_ids.length === 0}
                className="flex-1 rounded-lg bg-purple-500 py-2 text-sm font-medium text-white hover:bg-purple-600 disabled:opacity-50"
              >
                {createMutation.isPending ? '配信中...' : `${form.robot_ids.length}台に配信`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
