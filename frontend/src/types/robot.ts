export type RobotStatus =
  | 'IDLE'
  | 'CLEANING'
  | 'CHARGING'
  | 'RETURNING_TO_DOCK'
  | 'LOW_BATTERY'
  | 'UPDATING'
  | 'ERROR';

export interface Position {
  x: number;
  y: number;
  room: string;
}

export interface Robot {
  robot_id: string;
  name: string;
  status: RobotStatus;
  battery_level: number;
  position: Position;
  speed: number;
  firmware_version: string;
  last_seen: string;
  error_code?: string | null;
}

export interface TelemetryPoint {
  timestamp: string;
  battery_level: number;
  speed: number;
  status: string;
}

export interface TelemetryHistory {
  robot_id: string;
  points: TelemetryPoint[];
}

export interface RobotCommand {
  command: string;
  params?: Record<string, unknown>;
}

export interface Schedule {
  schedule_id: string;
  robot_id: string;
  room_id: string;
  cron_expression: string;
  description: string;
  enabled: boolean;
}

export interface ScheduleCreate {
  robot_id: string;
  room_id: string;
  cron_expression: string;
  description?: string;
}

export interface OtaJob {
  job_id: string;
  robot_id: string;
  status: string;
  firmware_version: string;
  new_speed: number;
  progress: number;
  started_at: string;
  completed_at: string;
}

export interface OtaJobCreate {
  robot_ids: string[];
  new_speed: number;
  version: string;
  description?: string;
}

// ─── WebSocket ─────────────────────────────────────────

export type WsMessage =
  | { type: 'initial_state'; robots: Robot[] }
  | { type: 'robot_update'; robot: Robot }
  | { type: 'alert'; robot_id: string; message: string };
