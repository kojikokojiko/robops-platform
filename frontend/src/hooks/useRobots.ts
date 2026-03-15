import { useMutation, useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import type { RobotCommand } from '../types/robot';

export function useRobots() {
  return useQuery({
    queryKey: ['robots'],
    queryFn: api.robots.list,
    // refetchInterval は無効化 — WebSocket のみで更新
  });
}

export function useRobot(robotId: string) {
  return useQuery({
    queryKey: ['robots', robotId],
    queryFn: () => api.robots.get(robotId),
    enabled: !!robotId,
  });
}

export function useSendCommand(robotId: string) {
  return useMutation({
    mutationFn: (cmd: RobotCommand) => api.robots.sendCommand(robotId, cmd),
    // 更新は WebSocket (robot_update) 経由で届くため REST 再取得は不要
  });
}
