import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useLayoutEffect, useRef } from 'react';
import type { Robot, TelemetryHistory, TelemetryPoint, WsMessage } from '../types/robot';

const TELEMETRY_APPEND_INTERVAL = 10_000; // 10秒ごとに1点追記（描画負荷対策）

export function useWebSocket() {
  const qc = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const connectRef = useRef<() => void>(() => {});
  // ロボットごとの最終テレメトリ追記時刻
  const lastTelemetryAppend = useRef<Map<string, number>>(new Map());

  const handleMessage = useCallback(
    (msg: WsMessage) => {
      if (msg.type === 'initial_state') {
        qc.setQueryData(['robots'], msg.robots);
      } else if (msg.type === 'robot_update') {
        qc.setQueryData<Robot[]>(['robots'], (prev) => {
          if (!prev) return [msg.robot];
          const idx = prev.findIndex((r) => r.robot_id === msg.robot.robot_id);
          if (idx === -1) return [...prev, msg.robot];
          const next = [...prev];
          next[idx] = msg.robot;
          return next;
        });
        qc.setQueryData(['robots', msg.robot.robot_id], msg.robot);

        // テレメトリグラフをリアルタイム更新（10秒に1点追記）
        const robotId = msg.robot.robot_id;
        const now = Date.now();
        const last = lastTelemetryAppend.current.get(robotId) ?? 0;
        if (now - last >= TELEMETRY_APPEND_INTERVAL) {
          lastTelemetryAppend.current.set(robotId, now);
          const newPoint: TelemetryPoint = {
            timestamp: msg.robot.last_seen,
            battery_level: msg.robot.battery_level,
            speed: msg.robot.speed,
            status: msg.robot.status,
          };
          const cutoff = new Date(now - 60 * 60 * 1000).toISOString();
          qc.setQueriesData<TelemetryHistory>(
            { queryKey: ['telemetry', robotId] },
            (prev) => {
              if (!prev) return prev;
              const trimmed = prev.points.filter((p) => p.timestamp >= cutoff);
              return { ...prev, points: [...trimmed, newPoint] };
            },
          );
        }
      }
    },
    [qc],
  );

  const connect = useCallback(() => {
    // ローカル: ws://localhost:8000/ws
    // 本番: VITE_WS_URL (wss://xxx.execute-api.xxx.amazonaws.com/dev)
    const url = import.meta.env.VITE_WS_URL ?? `ws://${window.location.host}/ws`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[WS] connected to', url);
      ws.send(JSON.stringify({ action: 'subscribe_robot' }));
    };

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data) as WsMessage;
        console.log('[WS] message received:', msg.type, msg);
        handleMessage(msg);
      } catch {
        console.warn('[WS] failed to parse message:', e.data);
      }
    };

    ws.onclose = (e) => {
      console.log('[WS] disconnected (code:', e.code, 'reason:', e.reason, '), reconnecting in 3s...');
      reconnectTimer.current = setTimeout(() => connectRef.current(), 3000);
    };

    ws.onerror = (e) => {
      console.error('[WS] error:', e);
      ws.close();
    };
  }, [handleMessage]);

  // Keep ref in sync with latest connect callback
  useLayoutEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);
}
