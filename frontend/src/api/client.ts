import type {
  OtaJob,
  OtaJobCreate,
  Robot,
  RobotCommand,
  Schedule,
  ScheduleCreate,
  TelemetryHistory,
} from '../types/robot';

// ローカル: Vite proxy が /api を :8000 に転送
// 本番: VITE_API_URL に API Gateway URL をセット
const BASE = import.meta.env.VITE_API_URL ?? '';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${init?.method ?? 'GET'} ${path} failed (${res.status}): ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ─── Robots ───────────────────────────────────────────

export const api = {
  robots: {
    list: () => request<Robot[]>('/robots'),
    get: (id: string) => request<Robot>(`/robots/${id}`),
    sendCommand: (id: string, cmd: RobotCommand) =>
      request(`/robots/${id}/commands`, { method: 'POST', body: JSON.stringify(cmd) }),
  },

  // ─── Telemetry ──────────────────────────────────────

  telemetry: {
    get: (id: string, minutes = 60) =>
      request<TelemetryHistory>(`/robots/${id}/telemetry?minutes=${minutes}`),
  },

  // ─── Schedules ──────────────────────────────────────

  schedules: {
    list: () => request<Schedule[]>('/schedules'),
    create: (body: ScheduleCreate) =>
      request<Schedule>('/schedules', { method: 'POST', body: JSON.stringify(body) }),
    delete: (id: string) => request<void>(`/schedules/${id}`, { method: 'DELETE' }),
  },

  // ─── OTA ────────────────────────────────────────────

  ota: {
    listJobs: () => request<OtaJob[]>('/ota/jobs'),
    createJob: (body: OtaJobCreate) =>
      request<OtaJob[]>('/ota/jobs', { method: 'POST', body: JSON.stringify(body) }),
    getJob: (id: string) => request<OtaJob[]>(`/ota/jobs/${id}`),
  },
};
